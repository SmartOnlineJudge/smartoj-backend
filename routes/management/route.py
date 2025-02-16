from fastapi import APIRouter, Depends
from fastapi.requests import Request

import settings
from ..user.models import LoginModel, UserOutModel
from ..user.route import user_logout
from utils.user.auth import authenticate, login, get_current_admin
from utils.responses import SmartOJResponse, ResponseCodes


router = APIRouter()


@router.post("/login", summary="管理员登录")
async def admin_login(form: LoginModel):
    user: dict | None = await authenticate(
        email=form.email,
        password=form.password,
        auth_type=form.auth_type.value,
    )
    if not user:
        return SmartOJResponse(ResponseCodes.LOGIN_FAILED)
    if not user["is_superuser"]:
        return SmartOJResponse(ResponseCodes.PERMISSION_DENIED)
    session_id = await login(user["user_id"])
    response = SmartOJResponse(ResponseCodes.LOGIN_SUCCESS)
    response.set_cookie(
        key="session_id",
        value=session_id,
        max_age=settings.SESSION_MAX_AGE,
        httponly=True,
    )
    return response


@router.post("/logout", summary="管理员退出登录")
async def admin_logout(request: Request):
    return await user_logout(request)


@router.get("/admin", summary="获取当前管理员信息")
async def get_admin_user(admin: dict = Depends(get_current_admin)):
    admin_model = UserOutModel(**admin)
    return SmartOJResponse(ResponseCodes.OK, data=admin_model.model_dump())
