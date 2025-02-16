from fastapi import APIRouter
from fastapi.requests import Request

from utils.user.auth import logout
from utils.responses import SmartOJResponse, ResponseCodes


router = APIRouter()


@router.post("/logout", summary="用户退出登录")
async def user_logout(request: Request):
    await logout(request)
    response = SmartOJResponse(ResponseCodes.OK)
    response.delete_cookie("session_id", httponly=True)
    return response
