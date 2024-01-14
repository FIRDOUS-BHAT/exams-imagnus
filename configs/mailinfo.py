from pydantic_settings import BaseSettings, SettingsConfigDict
import os


class Setting(BaseSettings):
    mail_username: str
    mail_password: str
    mail_from: str
    mail_port: str
    mail_server: str
    mail_from_name: str

    class Config:
        if os.path.exists('.env'):
            env_file = '.env'
        extra = "ignore"
        config_class = SettingsConfigDict
        env_file_encoding = 'utf-8'
