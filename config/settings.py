"""
Configuration settings for the enhanced RAG system.
"""
import os
from typing import Optional, List, Any
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API Keys
    google_api_key: str = ""
    groq_api_key: str = ""
    pinecone_api_key: str = ""
    langsmith_api_key: str = ""
    redis_url: str = "redis://localhost:6379"

    
    # Database
    database_url: str = "sqlite:///./rag_system.db"
    
    # Vector Store
    pinecone_environment: str = "us-west1-gcp"
    pinecone_index_name: str = "youtube-rag"
    embedding_model: str = "models/text-embedding-004"  # Gemini embedding model
    embedding_dimension: int = 768  # Gemini text-embedding-004 dimension
    # Optional vector store selector (pinecone, faiss, chroma)
    vector_store_type: Optional[str] = None
    
    # LLM Settings (Groq)
    llm_model: str = "llama-3.3-70b-versatile"
    llm_temperature: float = 0.2
    max_tokens: int = 1000
    llm_model_type: str = "groq"
    
    # Retrieval Settings
    top_k: int = 6
    similarity_threshold: float = 0.7
    mmr_diversity_threshold: float = 0.3
    
    # Translation
    default_language: str = "en"
    # Accept raw env var as comma-separated string to avoid JSON parsing by dotenv provider
    supported_languages_raw: Optional[Any] = Field(
        default=None, alias="SUPPORTED_LANGUAGES"
    )
    supported_languages: List[str] = Field(
        default_factory=lambda: [
            "en", "es", "fr", "de", "it", "pt", "ru", "zh", "ja", "ko", "ar", "ur"
        ]
    )
    
    # Evaluation
    enable_ragas: bool = True
    enable_langsmith: bool = True
    
    # Chrome Extension
    extension_id: str = "youtube-rag-extension"
    backend_url: str = "http://localhost:8000"
    
    # Performance
    max_concurrent_requests: int = 10
    cache_ttl: int = 3600  # 1 hour

    # Security & Server
    secret_key: Optional[str] = None
    allowed_origins_raw: Optional[str] = Field(default=None, alias="ALLOWED_ORIGINS")  # comma-separated
    # Give this field a dummy alias so Pydantic Settings does NOT bind ALLOWED_ORIGINS here
    allowed_origins: List[str] = Field(default_factory=lambda: ["*"], alias="IGNORED_ALLOWED_ORIGINS")
    log_level: str = "INFO"
    enable_metrics: bool = True
    debug: bool = False
    reload_on_change: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = False

    def model_post_init(self, __context):  # type: ignore[override]
        """Populate supported_languages from supported_languages_raw if provided."""
        if self.supported_languages_raw:
            try:
                # Accept either CSV string or JSON list
                if isinstance(self.supported_languages_raw, list):
                    self.supported_languages = [str(lang).strip() for lang in self.supported_languages_raw if str(lang).strip()]
                elif isinstance(self.supported_languages_raw, str):
                    raw = self.supported_languages_raw.strip()
                    # If it's JSON-like but delivered as string, try to parse
                    if raw.startswith("[") and raw.endswith("]"):
                        import json
                        arr = json.loads(raw)
                        self.supported_languages = [str(lang).strip() for lang in arr if str(lang).strip()]
                    else:
                        self.supported_languages = [
                            lang.strip() for lang in raw.split(",") if lang.strip()
                        ]
            except Exception:
                # Keep defaults on parse failure
                pass
        # Parse allowed origins if provided
        if self.allowed_origins_raw:
            self.allowed_origins = [
                o.strip() for o in self.allowed_origins_raw.split(",") if o.strip()
            ]


settings = Settings()
