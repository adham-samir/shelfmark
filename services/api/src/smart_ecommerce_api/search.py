"""SF-03 image and voice search adapters sharing the catalog authority."""

from __future__ import annotations

from io import BytesIO
import json
from pathlib import Path
from typing import Annotated, Protocol
from uuid import UUID

import numpy as np
from openai import OpenAI
from PIL import Image, UnidentifiedImageError
import psycopg
from psycopg.types.json import Json
from pydantic import Field
import torch
from torch.nn.functional import cosine_similarity, normalize

from . import db
from .catalog import CatalogService
from .errors import DependencyUnavailable, InvalidInput, PayloadTooLarge, UnsupportedMedia
from .models import Product, StrictModel


IMAGE_MEDIA_TYPES = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
}
AUDIO_MEDIA_TYPES = {
    "audio/flac",
    "audio/m4a",
    "audio/mp4",
    "audio/mpeg",
    "audio/mpga",
    "audio/ogg",
    "audio/wav",
    "audio/webm",
    "audio/x-m4a",
    "audio/x-wav",
}


def normalise_media_type(value: str) -> str:
    """Reduce an upload's media type to the bare type.

    Browsers append the codec to what they record — ``audio/webm;codecs=opus``
    in Chrome, ``audio/ogg; codecs=opus`` in Firefox, ``audio/mp4;codecs=...``
    in Safari — so an exact comparison against the allow-list rejected every
    real recording before it reached the provider.
    """

    return value.split(";", 1)[0].strip().lower()


class RankedProduct(StrictModel):
    product: Product
    score: Annotated[float, Field(ge=-1, le=1)]


class ImageSearchResponse(StrictModel):
    items: list[RankedProduct]
    model_version: str


class VoiceSearchResponse(StrictModel):
    transcript: str
    items: list[Product]
    total: Annotated[int, Field(ge=0)]
    model: str


class Transcriber(Protocol):
    @property
    def model(self) -> str: ...

    def transcribe(
        self,
        *,
        filename: str,
        content_type: str,
        content: bytes,
        language: str,
    ) -> str: ...


class OpenAITranscriber:
    """OpenAI-compatible speech-to-text adapter.

    ``base_url`` lets an OpenAI-compatible gateway (for example OpenRouter at
    ``https://openrouter.ai/api/v1``) stand in for OpenAI; ``None`` keeps the
    default OpenAI endpoint.
    """

    def __init__(
        self, api_key: str | None, model: str, base_url: str | None = None
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url

    @property
    def model(self) -> str:
        return self._model

    def transcribe(
        self,
        *,
        filename: str,
        content_type: str,
        content: bytes,
        language: str,
    ) -> str:
        if not self._api_key:
            raise DependencyUnavailable(
                "Voice search is unavailable because its API key is not configured."
            )
        try:
            result = OpenAI(
                api_key=self._api_key, base_url=self._base_url
            ).audio.transcriptions.create(
                model=self._model,
                file=(filename, content, content_type),
                language=language,
            )
            transcript = result.text.strip()
        except Exception as error:
            raise DependencyUnavailable("The transcription provider is unavailable.") from error
        if not transcript:
            raise InvalidInput("The recording did not contain recognizable speech.")
        return transcript


def extract_embedding(image: Image.Image) -> torch.Tensor:
    """Extract a deterministic PyTorch color feature for the synthetic baseline."""

    pixels = torch.from_numpy(
        np.asarray(image.convert("RGB").resize((96, 96)), dtype=np.float32).copy()
    ).permute(2, 0, 1) / 255.0
    mean = pixels.mean(dim=(1, 2))
    return normalize(torch.cat((mean, 1.0 - mean)), dim=0)


class PyTorchImageRetriever:
    def __init__(self, artifact_path: str) -> None:
        self._path = Path(artifact_path)
        self._artifact: dict[str, object] | None = None

    def _load(self) -> dict[str, object]:
        if self._artifact is None:
            try:
                artifact = json.loads(self._path.read_text(encoding="utf-8"))
                required = {"version_label", "framework", "prototypes", "metrics"}
                if not required.issubset(artifact) or artifact["framework"] != "pytorch":
                    raise ValueError("invalid image-search artifact")
                for prototype in artifact["prototypes"]:
                    UUID(prototype["product_id"])
                    if len(prototype["rgb"]) != 3:
                        raise ValueError("invalid RGB prototype")
                self._artifact = artifact
            except Exception as error:
                raise DependencyUnavailable(
                    "The image-search artifact is unavailable."
                ) from error
        return self._artifact

    @property
    def version(self) -> str:
        return str(self._load()["version_label"])

    @property
    def metadata(self) -> dict[str, object]:
        return self._load()

    def rank(self, image: Image.Image) -> list[tuple[UUID, float]]:
        query = extract_embedding(image)
        ranked: list[tuple[UUID, float]] = []
        for prototype in self._load()["prototypes"]:
            rgb = tuple(int(value) for value in prototype["rgb"])
            swatch = Image.new("RGB", (8, 8), rgb)
            score = float(cosine_similarity(query, extract_embedding(swatch), dim=0))
            ranked.append((UUID(prototype["product_id"]), round(score, 6)))
        return sorted(ranked, key=lambda item: (-item[1], str(item[0])))


class SearchEvidenceStore:
    def __init__(self, dsn: str, artifact_reference: str) -> None:
        self._dsn = dsn
        self._artifact_reference = artifact_reference

    def register_image_model(self, artifact: dict[str, object]) -> None:
        try:
            with db.connection(self._dsn) as connection:
                model_version_id = UUID(str(artifact["model_version_id"]))
                evaluation_id = UUID(str(artifact["evaluation_id"]))
                connection.execute(
                    """
                    INSERT INTO model_versions(
                        model_version_id, module, version_label,
                        dataset_snapshot_id, artifact_reference, framework
                    ) VALUES (%s, 'image_search', %s, %s, %s, 'pytorch')
                    ON CONFLICT (model_version_id) DO NOTHING
                    """,
                    (
                        model_version_id,
                        artifact["version_label"],
                        artifact["dataset_snapshot_id"],
                        self._artifact_reference,
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO evaluation_runs(
                        evaluation_id, model_version_id, dataset_snapshot_id,
                        split_strategy, metrics, limitations
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (evaluation_id) DO NOTHING
                    """,
                    (
                        evaluation_id,
                        model_version_id,
                        artifact["dataset_snapshot_id"],
                        "three deterministic color perturbations around each of four catalog prototypes",
                        Json(artifact["metrics"]),
                        artifact["limitations"],
                    ),
                )
        except (KeyError, ValueError, psycopg.Error) as error:
            raise DependencyUnavailable(
                "Image-search evaluation evidence could not be stored."
            ) from error


class SearchService:
    def __init__(
        self,
        catalog: CatalogService,
        image_retriever: PyTorchImageRetriever,
        transcriber: Transcriber,
        maximum_upload_bytes: int,
        evidence_store: SearchEvidenceStore | None = None,
    ) -> None:
        self._catalog = catalog
        self._image_retriever = image_retriever
        self._transcriber = transcriber
        self._maximum_upload_bytes = maximum_upload_bytes
        self._evidence_store = evidence_store

    @property
    def maximum_upload_bytes(self) -> int:
        return self._maximum_upload_bytes

    def _validate_size(self, content: bytes) -> None:
        if not content:
            raise InvalidInput("The uploaded file is empty.")
        if len(content) > self._maximum_upload_bytes:
            raise PayloadTooLarge("The uploaded file exceeds the 5 MiB limit.")

    def image_search(
        self,
        *,
        content: bytes,
        content_type: str,
        category: str | None,
        filters: dict[str, str],
        limit: int,
    ) -> ImageSearchResponse:
        self._validate_size(content)
        expected_format = IMAGE_MEDIA_TYPES.get(normalise_media_type(content_type))
        if expected_format is None:
            raise UnsupportedMedia("Upload a JPEG, PNG, or WebP image.")
        try:
            image = Image.open(BytesIO(content))
            image.load()
            if image.format != expected_format or image.width * image.height > 16_000_000:
                raise ValueError("image metadata is not accepted")
        except (UnidentifiedImageError, OSError, ValueError) as error:
            raise InvalidInput("The uploaded image is invalid or mislabeled.") from error
        products = self._catalog.list_products(
            query=None,
            category=category,
            filters=filters,
            limit=100,
            offset=0,
        ).items
        if self._evidence_store is not None:
            self._evidence_store.register_image_model(self._image_retriever.metadata)
        by_id = {product.product_id: product for product in products}
        items = [
            RankedProduct(product=by_id[product_id], score=score)
            for product_id, score in self._image_retriever.rank(image)
            if product_id in by_id
        ][:limit]
        return ImageSearchResponse(
            items=items,
            model_version=self._image_retriever.version,
        )

    def voice_search(
        self,
        *,
        filename: str,
        content_type: str,
        content: bytes,
        language: str,
        category: str | None,
        filters: dict[str, str],
        limit: int,
    ) -> VoiceSearchResponse:
        self._validate_size(content)
        content_type = normalise_media_type(content_type)
        if content_type not in AUDIO_MEDIA_TYPES:
            raise UnsupportedMedia("Upload a supported recorded-audio file.")
        transcript = self._transcriber.transcribe(
            filename=filename,
            content_type=content_type,
            content=content,
            language=language,
        )
        transcript = transcript.strip()
        if not transcript:
            raise InvalidInput("The recording did not contain recognizable speech.")
        page = self._catalog.list_products(
            query=transcript,
            category=category,
            filters=filters,
            limit=limit,
            offset=0,
        )
        return VoiceSearchResponse(
            transcript=transcript,
            items=page.items,
            total=page.total,
            model=self._transcriber.model,
        )
