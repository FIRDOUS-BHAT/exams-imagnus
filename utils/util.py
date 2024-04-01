from jose import JWTError, jwt
from configs import appinfo
from configs.connection import database
from passlib.context import CryptContext
from datetime import datetime, timedelta
# import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from auth import model
# from jwt import PyJWTError
from pydantic import ValidationError
import pytz

from functools import lru_cache
import sys

def dd(data):
    print(data)
    sys.exit()

@lru_cache()
def app_setting():
    return appinfo.Setting()


settings = app_setting()

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/student/v2/auth/token/"
)

pwd_context = CryptContext(schemes=["bcrypt"])

tz = pytz.timezone("Asia/Kolkata")

# exception handler for authjwt
# in production, you can tweak performance using orjson response


def findExistedUser(mobile: str):
    query = "select * from students where status='1' and mobile=:mobile"
    return database.fetch_one(query, values={"mobile": mobile})


def findExistedEmail(email: str):
    query = "select * from students where status='1' and email=:email"
    return database.fetch_one(query, values={"email": email})


def get_password_hash(password):
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(*, data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(tz) + expires_delta
    else:
        expire = datetime.now(tz) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.secret_key,
                             algorithms=[settings.algorithm])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = model.TokenData(username=username)
    except (JWTError, ValidationError):
        raise credentials_exception
    return True
    # user = await findExistedUser(token_data.username)
    # if user is None:
    #     raise credentials_exception

    # return model.UserList(**user)


def get_current_active_user(current_user: model.UserList = Depends(get_current_user)):
    if current_user.status == '9':
        raise HTTPException(status_code=208, detail="Inactive user")
    return current_user
