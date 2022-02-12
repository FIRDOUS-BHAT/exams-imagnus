import sqlalchemy
from sqlalchemy_utils import EmailType


metadata = sqlalchemy.MetaData()

users = sqlalchemy.Table(
    "users",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("fullname", sqlalchemy.String),
    sqlalchemy.Column("mobile", sqlalchemy.String, unique=True),
    sqlalchemy.Column("email", EmailType, unique=True),
    sqlalchemy.Column("password", sqlalchemy.String),
    sqlalchemy.Column("status", sqlalchemy.String),
    sqlalchemy.Column("created_at", sqlalchemy.String),
)
