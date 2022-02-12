from pydantic import BaseModel, Field


class UserIn(BaseModel):
    mobile: str = Field(..., )
    password: str = Field(..., )


class UserCreate(BaseModel):
    fullname: str = Field(..., example="name")
    mobile: str = Field(..., example="mobile number")
    email: str = Field(..., example="email@gmail.com")
    password: str = Field(..., example="password")


class UserList(BaseModel):
    id: str
    fullname: str
    mobile: str
    email: str
    status: str
    created_at: str


class UserPWD(UserList):
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    expired_in: str


class TokenData(BaseModel):
    username: str = None
