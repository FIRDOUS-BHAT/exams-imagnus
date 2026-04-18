from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os

class Setting(BaseSettings):
    db_connection: str
    db_host: str
    db_port: str = "5432"
    db_database: str
    db_username: str
    db_password: str
    db_sslmode: Optional[str] = None

    class Config:
        if os.path.exists('.env'):
            env_file = '.env'
        extra = "ignore"
        config_class = SettingsConfigDict
        env_file_encoding = 'utf-8'
