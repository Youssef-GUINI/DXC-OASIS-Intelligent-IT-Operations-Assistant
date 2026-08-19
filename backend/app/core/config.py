# from pydantic_settings import BaseSettings, SettingsConfigDict


# class Settings(BaseSettings):
#     database_url: str
#     jwt_secret_key: str
#     jwt_algorithm: str = "HS256"
#     jwt_expire_minutes: int = 60
#     chroma_host: str = "localhost"
#     chroma_port: int = 8001
#     groq_api_key: str = ""
#     anthropic_api_key: str = ""

#     model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# settings = Settings()


from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ==========================================
    # APPLICATION
    # ==========================================
    app_name: str = "OASIS AI Copilot"
    app_env: str = "development"
    debug: bool = True

    # ==========================================
    # DATABASE
    # ==========================================
    database_url: str

    # ==========================================
    # JWT
    # ==========================================
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # ==========================================
    # CHROMADB
    # ==========================================
    chroma_host: str = "localhost"
    chroma_port: int = 8001

    # ==========================================
    # LLM
    # ==========================================
    groq_api_key: str
    groq_model: str = "openai/gpt-oss-20b"
    groq_tool_model: str = "openai/gpt-oss-20b"
    groq_max_tokens: int = 700
    anthropic_api_key: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
