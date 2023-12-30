from pydantic_settings import BaseSettings, SettingsConfigDict


class Setting(BaseSettings):
    db_connection: str
    db_host: str
    db_port: str
    db_database: str
    db_username: str
    db_password: str
    app_url: str
    slack_webhook_url: str

    class Config:
        # env_file = '.env'
        # extra = "ignore"
        # config_class = SettingsConfigDict
        # env_file_encoding = 'utf-8'
        env_prefix = ""  # Optional: use a prefix like 'MYAPP_' for all environment variables
        case_sensitive = True 
