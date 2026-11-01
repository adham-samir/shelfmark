"""Environment-backed runtime configuration."""

from dataclasses import dataclass
import os


@dataclass(frozen=True, slots=True)
class Settings:
    postgres_dsn: str
    mongo_uri: str
    mongo_database: str
    recommendation_artifact: str
    image_search_artifact: str
    forecast_artifact: str
    assistant_knowledge: str
    pricing_seasons: str
    fraud_artifact: str
    openai_api_key: str | None
    openai_base_url: str | None
    assistant_model: str
    transcription_model: str
    maximum_upload_bytes: int
    worker_threads: int

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            postgres_dsn=os.getenv(
                "SMART_ECOMMERCE_POSTGRES_DSN",
                "postgresql://smart_ecommerce:smart_ecommerce@postgres:5432/smart_ecommerce",
            ),
            mongo_uri=os.getenv(
                "SMART_ECOMMERCE_MONGO_URI",
                "mongodb://mongo:27017/?directConnection=true",
            ),
            mongo_database=os.getenv("SMART_ECOMMERCE_MONGO_DATABASE", "smart_ecommerce"),
            recommendation_artifact=os.getenv(
                "SMART_ECOMMERCE_RECOMMENDATION_ARTIFACT",
                "services/api/artifacts/recommendation.joblib",
            ),
            image_search_artifact=os.getenv(
                "SMART_ECOMMERCE_IMAGE_SEARCH_ARTIFACT",
                "services/api/artifacts/image_search.json",
            ),
            forecast_artifact=os.getenv(
                "SMART_ECOMMERCE_FORECAST_ARTIFACT",
                "services/api/artifacts/forecast.joblib",
            ),
            assistant_knowledge=os.getenv(
                "SMART_ECOMMERCE_ASSISTANT_KNOWLEDGE",
                "services/api/data/assistant_faq.json",
            ),
            pricing_seasons=os.getenv(
                "SMART_ECOMMERCE_PRICING_SEASONS",
                "services/api/data/pricing_seasons.json",
            ),
            fraud_artifact=os.getenv(
                "SMART_ECOMMERCE_FRAUD_ARTIFACT",
                "services/api/artifacts/fraud.joblib",
            ),
            openai_api_key=os.getenv("OPENAI_API_KEY") or None,
            openai_base_url=os.getenv("SMART_ECOMMERCE_OPENAI_BASE_URL") or None,
            assistant_model=os.getenv(
                "SMART_ECOMMERCE_ASSISTANT_MODEL", "gpt-6-luna"
            ),
            transcription_model=os.getenv(
                "SMART_ECOMMERCE_TRANSCRIPTION_MODEL", "gpt-transcribe"
            ),
            maximum_upload_bytes=int(
                os.getenv("SMART_ECOMMERCE_MAXIMUM_UPLOAD_BYTES", str(5 * 1024 * 1024))
            ),
            worker_threads=int(os.getenv("SMART_ECOMMERCE_WORKER_THREADS", "100")),
        )

