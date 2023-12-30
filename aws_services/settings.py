from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    AWS_SERVER_PUBLIC_KEY: str
    AWS_SERVER_SECRET_KEY: str
    IMAGEKIT_PRIVATE_KEY: str
    IMAGEKIT_PUBLIC_KEY: str

    class Config:
        # env_file = '.env'
        # extra = "ignore"
        # config_class = SettingsConfigDict
        # env_file_encoding = 'utf-8'
        env_prefix = ""  # Optional: use a prefix like 'MYAPP_' for all environment variables
        case_sensitive = True 


settings = Settings(_env_file='.env', _env_file_encoding='utf-8')
