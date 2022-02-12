from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from starlette.config import Config

config = Config(".env")
POSTGRES_USER = config("DB_USERNAME", cast=str)
POSTGRES_PASSWORD = config("DB_PASSWORD", cast=str)
POSTGRES_SERVER = config("DB_HOST", cast=str, default="db")
POSTGRES_PORT = config("DB_PORT", cast=str, default="5432")
POSTGRES_DB = config("DB_DATABASE", cast=str)

# SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"
SQLALCHEMY_DATABASE_URL = "postgresql://" + POSTGRES_USER + ":" + POSTGRES_PASSWORD + "@postgresserver/" + POSTGRES_DB

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
)
#connect_args={"check_same_thread": False}
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()