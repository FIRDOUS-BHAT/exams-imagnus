from functools import lru_cache
from typing import Optional

from imagekitio import ImageKit
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    AWS_SERVER_PUBLIC_KEY: str = ""
    AWS_SERVER_SECRET_KEY: str = ""
    IMAGEKIT_PRIVATE_KEY: str = ""
    IMAGEKIT_PUBLIC_KEY: str = ""

    class Config:
        env_file = '.env'
        extra = "ignore"
        config_class = SettingsConfigDict
        env_file_encoding = 'utf-8'


@lru_cache()
def get_settings() -> Settings:
    return Settings(_env_file='.env', _env_file_encoding='utf-8')


def has_s3_credentials(current: Optional[Settings] = None) -> bool:
    current = current or get_settings()
    return bool(current.AWS_SERVER_PUBLIC_KEY and current.AWS_SERVER_SECRET_KEY)


def has_imagekit_credentials(current: Optional[Settings] = None) -> bool:
    current = current or get_settings()
    return bool(current.IMAGEKIT_PRIVATE_KEY and current.IMAGEKIT_PUBLIC_KEY)


@lru_cache()
def get_imagekit_client() -> Optional[ImageKit]:
    current = get_settings()
    if not has_imagekit_credentials(current):
        return None
    return ImageKit(
        private_key=current.IMAGEKIT_PRIVATE_KEY,
        public_key=current.IMAGEKIT_PUBLIC_KEY,
        url_endpoint='https://ik.imagekit.io/imagnus/'
    )


settings = get_settings()
