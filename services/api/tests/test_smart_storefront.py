from datetime import UTC, datetime
from decimal import Decimal
from io import BytesIO
import json
from pathlib import Path
from uuid import UUID

from PIL import Image
import pytest
from fastapi.testclient import TestClient

from smart_ecommerce_api.auth import Principal
from smart_ecommerce_api.assistant import (
    AssistantRequest,
    AssistantService,
    FaqKnowledge,
    OpenAITextGenerator,
)
from smart_ecommerce_api.catalog import CatalogService, OperationalProduct
from smart_ecommerce_api.commerce_models import Shipment, ShipmentEvent
from smart_ecommerce_api.errors import (
    DependencyUnavailable,
    InvalidInput,
    PayloadTooLarge,
    ResourceNotFound,
    UnsupportedMedia,
)
from smart_ecommerce_api.search import (
    OpenAITranscriber,
    PyTorchImageRetriever,
    SearchService,
)
from smart_ecommerce_api.main import create_app


ROOT = Path(__file__).parents[1]
NOW = datetime(2026, 10, 27, tzinfo=UTC)
CUSTOMER_ID = UUID("20000000-0000-4000-8000-000000000001")
OTHER_CUSTOMER_ID = UUID("20000000-0000-4000-8000-000000000002")
OWN_ORDER_ID = UUID("70000000-0000-4000-8000-000000000001")
OTHER_ORDER_ID = UUID("70000000-0000-4000-8000-000000000002")
PRODUCT_IDS = [
    UUID(f"10000000-0000-4000-8000-{index:012d}") for index in range(1, 5)
]


class Operational:
    def list_active(self):
        return [
            OperationalProduct(
                product_id=product_id,
                amount=Decimal(str(8000 + index * 1000)),
                currency="EGP",
                price_updated_at=NOW,
                available=10,
                inventory_updated_at=NOW,
            )
            for index, product_id in enumerate(PRODUCT_IDS)
        ]

    def get_active(self, product_id):
        return next(
            (item for item in self.list_active() if item.product_id == product_id),
            None,
        )

    def ping(self):
        return None


class Descriptive:
    records = {
        str(PRODUCT_IDS[0]): {
            "_id": str(PRODUCT_IDS[0]),
            "name": "X1 Synthetic Phone",
            "description": "Blue smartphone fixture",
            "categories": ["phones"],
            "attributes": {"storage": "128 GB", "color": "blue"},
            "images": [],
        },
        str(PRODUCT_IDS[1]): {
            "_id": str(PRODUCT_IDS[1]),
            "name": "Y2 Synthetic Phone",
            "description": "Red smartphone fixture",
            "categories": ["phones"],
            "attributes": {"storage": "256 GB", "color": "red"},
            "images": [],
        },
        str(PRODUCT_IDS[2]): {
            "_id": str(PRODUCT_IDS[2]),
            "name": "H1 Synthetic Headphones",
            "description": "Black wireless headphone fixture",
            "categories": ["headphones"],
            "attributes": {"battery": "30 h", "color": "black"},
            "images": [],
        },
        str(PRODUCT_IDS[3]): {
            "_id": str(PRODUCT_IDS[3]),
            "name": "L1 Synthetic Laptop",
            "description": "Silver portable computer fixture",
            "categories": ["laptops"],
            "attributes": {"storage": "512 GB SSD", "color": "silver"},
            "images": [],
        },
    }

    def get_many(self, product_ids):
        return {str(item): self.records[str(item)] for item in product_ids}

    def get_one(self, product_id):
        return self.records.get(str(product_id))

    def ping(self):
        return None


class FakeCommerce:
    def get_shipment(self, customer_id, order_id):
        if customer_id != CUSTOMER_ID or order_id != OWN_ORDER_ID:
            raise ResourceNotFound("Shipment not found.")
        return Shipment(
            shipment_id=UUID("80000000-0000-4000-8000-000000000001"),
            status="in_transit",
            updated_at=NOW,
            events=[
                ShipmentEvent(
                    status="in_transit",
                    description_ar="الشحنة في الطريق",
                    description_en="Shipment is in transit",
                    occurred_at=NOW,
                )
            ],
        )


class RecordingGenerator:
    model = "fake-grounded-v1"

    def __init__(self):
        self.calls = []

    def generate(self, *, instructions, input_text):
        self.calls.append((instructions, json.loads(input_text)))
        return "Grounded fixture answer"


class FakeTranscriber:
    model = "fake-transcriber-v1"

    def __init__(self, transcript="wireless headphones"):
        self.transcript = transcript
        self.calls = []

    def transcribe(self, **request):
        self.calls.append(request)
        return self.transcript


class FakeAuthenticator:
    def authenticate(self, token):
        if token != "customer-token":
            raise AssertionError("unexpected test token")
        return Principal(
            principal_id=UUID("30000000-0000-4000-8000-000000000001"),
            account_type="customer",
            customer_id=CUSTOMER_ID,
            scopes=frozenset(),
        )


class UnusedRecommendation:
    def recommend(self, customer_id, limit):
        raise AssertionError("recommendation endpoint is not part of this test")


def catalog():
    return CatalogService(Operational(), Descriptive())


def png(rgb):
    output = BytesIO()
    Image.new("RGB", (64, 64), rgb).save(output, format="PNG")
    return output.getvalue()


def search_service(transcript="wireless headphones", maximum=1024 * 1024):
    return SearchService(
        catalog(),
        PyTorchImageRetriever(str(ROOT / "artifacts/image_search.json")),
        FakeTranscriber(transcript),
        maximum,
    )


def api_client():
    product_catalog = catalog()
    commerce = FakeCommerce()
    assistant = AssistantService(
        product_catalog,
        commerce,
        FaqKnowledge(str(ROOT / "data/assistant_faq.json")),
        RecordingGenerator(),
    )
    search = SearchService(
        product_catalog,
        PyTorchImageRetriever(str(ROOT / "artifacts/image_search.json")),
        FakeTranscriber("find me wireless headphones"),
        1024 * 1024,
    )
    return TestClient(
        create_app(
            product_catalog,
            commerce,
            FakeAuthenticator(),
            UnusedRecommendation(),
            assistant,
            search,
        ),
        raise_server_exceptions=False,
    )


def test_assistant_grounds_catalog_faq_and_owned_shipment() -> None:
    generator = RecordingGenerator()
    service = AssistantService(
        catalog(),
        FakeCommerce(),
        FaqKnowledge(str(ROOT / "data/assistant_faq.json")),
        generator,
    )
    result = service.answer(
        CUSTOMER_ID,
        AssistantRequest(
            message="Where is my shipment?", locale="en", order_id=OWN_ORDER_ID
        ),
    )
    assert result.answer == "Grounded fixture answer"
    assert {source.kind for source in result.sources} == {"faq", "product", "shipment"}
    prompt = generator.calls[0][1]
    assert prompt["context"]["shipment"]["status"] == "in_transit"
    assert prompt["context"]["products"][0]["name"] == "X1 Synthetic Phone"
    assert "only the supplied JSON facts" in generator.calls[0][0]


def test_assistant_does_not_expose_another_customers_shipment() -> None:
    generator = RecordingGenerator()
    service = AssistantService(
        catalog(),
        FakeCommerce(),
        FaqKnowledge(str(ROOT / "data/assistant_faq.json")),
        generator,
    )
    result = service.answer(
        CUSTOMER_ID,
        AssistantRequest(message="Track this", order_id=OTHER_ORDER_ID),
    )
    assert all(source.kind != "shipment" for source in result.sources)
    assert generator.calls[0][1]["context"]["shipment"] == {
        "status": "not_found_or_not_owned"
    }
    assert str(OTHER_CUSTOMER_ID) not in json.dumps(generator.calls[0][1])


def test_openai_adapters_fail_explicitly_without_a_key() -> None:
    with pytest.raises(DependencyUnavailable, match="API key"):
        OpenAITextGenerator(None, "gpt-6-luna").generate(
            instructions="grounded", input_text="question"
        )
    with pytest.raises(DependencyUnavailable, match="API key"):
        OpenAITranscriber(None, "gpt-transcribe").transcribe(
            filename="speech.wav",
            content_type="audio/wav",
            content=b"audio",
            language="en",
        )


def test_image_search_uses_pytorch_ranking_and_combines_filters() -> None:
    service = search_service()
    result = service.image_search(
        content=png((40, 100, 220)),
        content_type="image/png",
        category=None,
        filters={},
        limit=3,
    )
    assert result.items[0].product.product_id == PRODUCT_IDS[0]
    assert result.model_version == "pytorch-color-retrieval-v1"

    filtered = service.image_search(
        content=png((40, 100, 220)),
        content_type="image/png",
        category="phones",
        filters={"storage": "256 GB"},
        limit=3,
    )
    assert [item.product.product_id for item in filtered.items] == [PRODUCT_IDS[1]]


def test_voice_search_uses_transcript_and_catalog_filters() -> None:
    result = search_service("find me wireless headphones").voice_search(
        filename="query.wav",
        content_type="audio/wav",
        content=b"synthetic audio bytes",
        language="en",
        category="headphones",
        filters={"color": "black"},
        limit=20,
    )
    assert result.transcript == "find me wireless headphones"
    assert result.total == 1
    assert result.items[0].product_id == PRODUCT_IDS[2]


def test_dynamic_facets_reflect_search_context() -> None:
    facets = catalog().facets(query="phone", category=None, filters={})
    assert facets.total == 2
    storage = next(facet for facet in facets.facets if facet.key == "storage")
    assert {(item.value, item.count) for item in storage.options} == {
        ("128 GB", 1),
        ("256 GB", 1),
    }


def test_upload_and_empty_recognition_failures_are_structured() -> None:
    service = search_service()
    with pytest.raises(InvalidInput):
        service.image_search(
            content=b"not an image",
            content_type="image/png",
            category=None,
            filters={},
            limit=3,
        )
    with pytest.raises(UnsupportedMedia):
        service.voice_search(
            filename="query.txt",
            content_type="text/plain",
            content=b"hello",
            language="en",
            category=None,
            filters={},
            limit=20,
        )
    with pytest.raises(PayloadTooLarge):
        search_service(maximum=2).image_search(
            content=b"123",
            content_type="image/png",
            category=None,
            filters={},
            limit=3,
        )
    with pytest.raises(InvalidInput, match="recognizable speech"):
        search_service("   ").voice_search(
            filename="query.wav",
            content_type="audio/wav",
            content=b"audio",
            language="en",
            category=None,
            filters={},
            limit=20,
        )


def test_http_routes_expose_assistant_search_filters_and_error_envelopes() -> None:
    api = api_client()
    headers = {"authorization": "Bearer customer-token"}
    assistant = api.post(
        "/v1/assistant/messages",
        json={"message": "Which phone should I choose?", "locale": "en"},
        headers=headers,
    )
    assert assistant.status_code == 200
    assert assistant.json()["model"] == "fake-grounded-v1"
    assert any(source["kind"] == "product" for source in assistant.json()["sources"])

    facets = api.get("/v1/products/facets?q=phone")
    assert facets.status_code == 200
    assert facets.json()["total"] == 2

    image = api.post(
        "/v1/search/image?category=phones&filter=storage%3A128%20GB",
        files={"image": ("phone.png", png((40, 100, 220)), "image/png")},
    )
    assert image.status_code == 200, image.text
    assert image.json()["items"][0]["product"]["product_id"] == str(PRODUCT_IDS[0])

    voice = api.post(
        "/v1/search/voice?locale=en&category=headphones",
        files={"audio": ("query.wav", b"synthetic audio", "audio/wav")},
    )
    assert voice.status_code == 200, voice.text
    assert voice.json()["items"][0]["product_id"] == str(PRODUCT_IDS[2])

    invalid = api.post(
        "/v1/search/image",
        files={"image": ("bad.png", b"not an image", "image/png")},
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "invalid_input"
