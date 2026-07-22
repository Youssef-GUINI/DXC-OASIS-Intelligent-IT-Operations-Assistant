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
    APP_NAME: str = "OASIS AI Copilot"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # ==========================================
    # DATABASE
    # ==========================================
    DATABASE_URL: str

    # ==========================================
    # JWT
    # ==========================================
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    # ==========================================
    # CHROMADB
    # ==========================================
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001

    # ==========================================
    # LLM
    # ==========================================
    GROQ_API_KEY: str
    ANTHROPIC_API_KEY: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()