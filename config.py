from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str = "super-tajny-klucz-domyslny"
    ADMIN_PASSWORD: str = "dnshui321enbui1g3782uje@dasda"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

# import instance
settings = Settings()