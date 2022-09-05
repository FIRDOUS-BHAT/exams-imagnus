import datetime
import uuid

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from starlette.config import Config

from auth import model
from configs.connection import database
from db.table import users
from utils import util
from utils.util import get_current_user

config = Config(".env")


class Auth(BaseModel):
    username: str
    password: str


router = APIRouter()


@router.post('/auth/token/', response_model=model.Token)
def generate_token(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.username != "test" or form_data.password != "test":
        raise HTTPException(status_code=208, detail="Bad username or password")

    # subject identifier for who this token is for example id or username from database
    access_token_expires = util.timedelta(
        minutes=int(config('ACCESS_TOKEN_EXPIRE_MINUTES')))
    access_token = util.create_access_token(
        data={"sub": form_data.username},
        expires_delta=access_token_expires,
    )

    results = {
        "access_token": access_token,
        "token_type": "bearer",
        "expired_in": int(config('ACCESS_TOKEN_EXPIRE_MINUTES')) * 60,

    }
    return results


@router.post("/auth/register", response_model=model.UserList)
async def register(user: model.UserCreate = Depends(get_current_user)):
    userDB = await util.findExistedUser(user.mobile)
    emailDB = await util.findExistedEmail(user.email)

    if userDB:
        raise HTTPException(
            status_code=208, detail="Mobile number already exists")

    if emailDB:
        raise HTTPException(status_code=208, detail="Email Id already exists")

    gid = str(uuid.uuid1())
    gdate = str(datetime.datetime.now())
    query = users.insert().values(
        id=gid,
        fullname=user.fullname,
        mobile=user.mobile,
        email=user.email,
        created_at=gdate,
        password=util.get_password_hash(user.password),
        status="1"
    )

    await database.execute(query)
    return {
        **user.dict(),
        "id": gid,
        "created_at": gdate,
        "status": "1"
    }


@router.post("/auth/login", response_model=model.Token)
async def login(form_data: model.UserIn = Depends(get_current_user)):
    # async def login(form_data: OAuth2PasswordRequestForm = Depends()):

    userDB = await util.findExistedUser(form_data.mobile)
    if not userDB:
        raise HTTPException(status_code=208, detail="Mobile number not found")

    user = model.UserPWD(**userDB)
    isValid = util.verify_password(form_data.password, user.password)
    if not isValid:
        raise HTTPException(
            status_code=208, detail="Incorrect Mobile number or password")

    results = {

        "user_info": user
    }

    return results
