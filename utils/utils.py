import jwt
from fastapi import HTTPException, status
from functools import lru_cache
from configs import appinfo


@lru_cache()
def app_setting():
    return appinfo.Setting()



settings = app_setting()
SECRET_KEY = settings.secret_key.encode('utf-8')


async def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload 
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
