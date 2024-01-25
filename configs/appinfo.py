from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Setting(BaseSettings):
    app_url: str
    app_name: str
    debug: str
    allowed_host: str
    cookie_name: str
    secret_key: str
    algorithm: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    razorpay_key: str
    razorpay_secret: str
    AWS_SERVER_PUBLIC_KEY: str
    AWS_SERVER_SECRET_KEY: str
    AWS_SERVER_REGION: str
    bunny_library_id: str
    bunny_cdn_host: str
    bunny_access_key: str
    admin_login: str
    ws_url: str
    cache_time: int
    slack_webhook_url: str
    app_type: str
    

    class Config:
        if os.path.exists('.env'):
            env_file = '.env'
        extra = "ignore"
        config_class = SettingsConfigDict
