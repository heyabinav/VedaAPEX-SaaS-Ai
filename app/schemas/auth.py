from pydantic import BaseModel, EmailStr, Field, ConfigDict
from pydantic.alias_generators import to_camel
from typing import Optional, Any, Union


class AuthBaseModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class UserRegister(AuthBaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = None
    referral_code: Optional[str] = None


class UserLogin(AuthBaseModel):
    email: EmailStr
    password: str


class AuthResponseUser(AuthBaseModel):
    id: Optional[Union[int, str]] = None
    email: str
    full_name: Optional[str] = None
    referral_code: Optional[str] = ""
    role: str = "user"
    plan: str = "Free"
    is_pro: bool = False
    subscription_start: Optional[str] = None
    subscription_end: Optional[str] = None



class AuthResponseData(AuthBaseModel):
    user: AuthResponseUser
    token: Optional[str] = None
    refresh_token: Optional[str] = None
    requires_email_confirmation: bool = False
    wallet: dict
    subscription: dict
    referral: Optional[Any] = None


class AuthResponse(AuthBaseModel):
    success: bool
    message: str
    data: AuthResponseData
