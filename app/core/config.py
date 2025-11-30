# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    SECRET_KEY: str = "change-me"
    ACCESS_TOKEN_EXPIRE_MIN: int = 1440
    DATABASE_URL: str = "postgresql+asyncpg://postgres:12345@127.0.0.1:5432/trends"

    MEDIA_DIR: str = "./media"
    ALLOWED_ORIGINS: str = "*"
    REDIS_URL: str | None = None

    # ⚙️ HLS local (para video tipo TikTok/Instagram sin pagar CDN)
    HLS_DIR: str = "./media/hls"
    HLS_SEG_SECONDS: int = 2              # duración de cada segmento .ts
    HLS_USE_LADDER: bool = True           # True: 240/360/480p (ABR). False: 1 calidad
    HLS_FAST_TRANSCODE: bool = True       # preset "veryfast" para que sea rápido

    # 👇 Compatibilidad Tenor / GIFs (aunque ahora uses servicio local)
    TENOR_API_KEY: str = "LIVDSRZULELA"
    TENOR_CLIENT_KEY: str = "trends-app"
    TENOR_BASE_URL: str = "https://tenor.googleapis.com/v2"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def allow_origins_list(self) -> List[str]:
        if self.ALLOWED_ORIGINS == "*":
            return ["*"]
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]


settings = Settings()
