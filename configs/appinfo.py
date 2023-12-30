from pydantic_settings import BaseSettings, SettingsConfigDict


class Setting(BaseSettings):
    app_url: str
    app_name: str
    app_version: str
    app_framework: str
    app_date: str
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
    

    class Config:
        # env_file = ".env"
        # extra = "ignore"
        # config_class = SettingsConfigDict
        env_prefix = ""  # Optional: use a prefix like 'MYAPP_' for all environment variables
        case_sensitive = True 
