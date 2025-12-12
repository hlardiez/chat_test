"""Configuration settings loaded from environment variables."""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # OpenAI Configuration
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-3.5-turbo", alias="OPEN_AI_MODEL")
    
    # Pinecone Configuration
    pinecone_api_key: str = Field(..., alias="PINECONE_API_KEY")
    pinecone_host: Optional[str] = Field(default=None, alias="PINECONE_HOST")
    pinecone_index_name: str = Field(..., alias="PINECONE_INDEX")
    pinecone_namespace: Optional[str] = Field(default=None, alias="PINECONE_NAMESPACE")
    
    # RagMetrics Configuration
    ragmetrics_api_key: str = Field(..., alias="RAGMETRICS_API_KEY")
    ragmetrics_base_url: str = Field(
        default="https://ragmetrics-staging-docker-c9ana3hgacg3fbbt.centralus-01.azurewebsites.net",
        alias="RAGMETRICS_URL"
    )
    ragmetrics_eval_group_id: str = Field(..., alias="RAGMETRICS_EVAL_GROUP_ID")
    ragmetrics_type: str = Field(default="S", alias="RAGMETRICS_EVAL_TYPE")
    ragmetrics_conversation_id: str = Field(..., alias="RAGMETRICS_CONVERSATION_ID")
    
    # RAG Configuration
    rag_top_k: int = Field(default=5, alias="RAG_TOP_K")
    embedding_model: str = Field(default="text-embedding-3-small", alias="EMBEDDING_MODEL")
    
    # Regeneration Configuration
    reg_score: int = Field(default=3, alias="REG_SCORE")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        # Don't fail if .env file doesn't exist (for Streamlit Cloud)
        env_file_required = False


# Global settings instance - lazy initialization
_settings_instance: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create the global settings instance (lazy initialization)."""
    global _settings_instance
    if _settings_instance is None:
        try:
            _settings_instance = Settings()
        except Exception as e:
            # Provide helpful error message for Streamlit Cloud
            import sys
            error_msg = str(e)
            if "Field required" in error_msg or "validation error" in error_msg.lower():
                raise ValueError(
                    f"Missing required environment variables. "
                    f"Please set all required variables in Streamlit Cloud Secrets. "
                    f"Original error: {error_msg}"
                ) from e
            raise
    return _settings_instance


# For backward compatibility, create a property-like accessor
class _SettingsProxy:
    """Proxy class to access settings lazily."""
    
    def __getattr__(self, name):
        return getattr(get_settings(), name)


settings = _SettingsProxy()

