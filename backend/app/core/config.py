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
    anthropic_api_key: str = ""

    # ==========================================
    # STORAGE VM (SSH) -- optionnels : absents, capacity.py renvoie une
    # erreur explicite au moment de l'appel plutôt que de faire planter
    # tout le backend au démarrage pour qui n'a pas encore la VM configurée.
    # ==========================================
    storage_vm_host: str | None = None
    storage_vm_port: int = 22
    storage_vm_user: str | None = None
    storage_vm_ssh_key_path: str | None = None

    # ==========================================
    # DATA HUB -- documents ajoutés par les ingénieurs
    # ==========================================
    upload_dir: str = "uploads"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()