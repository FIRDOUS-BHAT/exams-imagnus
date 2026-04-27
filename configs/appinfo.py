from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Setting(BaseSettings):
    app_url: str = ""
    app_name: str = "I-Magnus Exams"
    app_version: str = "1.0.0"
    debug: bool = False
    allowed_host: str = "*"
    cookie_name: str = "imagnus_session"
    secret_key: str
    algorithm: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    razorpay_key: str = ""
    razorpay_secret: str = ""
    AWS_SERVER_PUBLIC_KEY: str = ""
    AWS_SERVER_SECRET_KEY: str = ""
    AWS_SERVER_REGION: str = "ap-south-1"
    bunny_library_id: str = ""
    bunny_cdn_host: str = ""
    bunny_access_key: str = ""
    admin_login: str = "admin_session"
    ws_url: str = ""
    cache_time: int = 3600
    slack_webhook_url: str = ""
    app_type: str = "production"
    sms_api_key: str = ""
    fcm_server_key: str = ""
    vimeo_client_id: str = ""
    vimeo_client_secret: str = ""
    vimeo_access_token: str = ""
    legacy_api_username: str = ""
    legacy_api_password: str = ""
    firebase_api_key: str = ""
    firebase_auth_domain: str = ""
    firebase_project_id: str = ""
    firebase_storage_bucket: str = ""
    firebase_messaging_sender_id: str = ""
    firebase_app_id: str = ""
    firebase_measurement_id: str = ""

    @field_validator("debug", mode="before")
    @classmethod
    def normalize_debug(cls, value):
        if isinstance(value, bool) or value is None:
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on", "debug", "development", "dev", "local"}:
                return True
            if normalized in {"0", "false", "no", "off", "release", "production", "prod", "live"}:
                return False
        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )
