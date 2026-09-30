from pydantic import BaseModel


class RegisterRequest(BaseModel):
    login_name: str
    nickname: str
    password: str


class LoginRequest(BaseModel):
    login_name: str
    password: str


class UserOut(BaseModel):
    id: int
    login_name: str
    nickname: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class MeResponse(BaseModel):
    id: int
    login_name: str
    nickname: str
    daily_goal: int
