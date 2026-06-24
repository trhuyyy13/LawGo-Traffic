from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "LawGo Traffic"
    app_env: str = "local"

    # LLM
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    llm_api_key: str = ""
    embedding_model: str = "multilingual-e5-large"

    # Data
    data_dir: str = "./data"
    lightrag_working_dir: str = "./data/graph/lightrag"

    # Qdrant Cloud
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""

    # Neo4j AuraDB Free
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""

    # Supabase
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_bucket: str = "lawgo-traffic-docs"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Voice
    voice_enabled: bool = False
    stt_model: str = "phowhisper"
    tts_voice: str = "vi-VN-HoaiMyNeural"

    # OCR (set OCR_ENABLED=true to activate; reuses LLM_API_KEY above)
    ocr_enabled: bool = False
    ocr_model: str = "gpt-5.4-mini"


settings = Settings()
