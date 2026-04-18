import databases
import sqlalchemy
from functools import lru_cache
from typing import Optional
from urllib.parse import quote, urlencode
from configs import dbinfo
from db.table import metadata
from databases import DatabaseURL
from starlette.config import Config
from starlette.datastructures import Secret


@lru_cache()
def db_config():
    return dbinfo.Setting()


def DATABASE_URL(
        connection: str = db_config().db_connection,
        username: str = db_config().db_username,
        password: str = db_config().db_password,
        host: str = db_config().db_host,
        port: str = db_config().db_port,
        database: str = db_config().db_database,
        sslmode: Optional[str] = db_config().db_sslmode,
):
    encoded_username = quote(username, safe="")
    encoded_password = quote(password, safe="")
    encoded_database = quote(database, safe="")
    base_url = f"{connection}://{encoded_username}:{encoded_password}@{host}:{port}/{encoded_database}"

    if sslmode:
        return f"{base_url}?{urlencode({'sslmode': sslmode})}"

    return base_url


database = databases.Database(DATABASE_URL())

# engine = sqlalchemy.create_engine(
#     DATABASE_URL()
# )
#
# metadata.create_all(engine)
