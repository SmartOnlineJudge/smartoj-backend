from fastapi import APIRouter

from utils.responses import SmartOJResponse, ResponseCodes
from utils.dependencies import CurrentUserDependency, UserProfilesServiceDependency
from .models import UserProfileOut


router = APIRouter()


@router.get("/user-profile", summary="查询用户画像")
async def query_user_profiles(
    user: CurrentUserDependency,
    service: UserProfilesServiceDependency
):
    """
    ## 响应代码说明:
    **200**: 业务逻辑执行成功
    """
    user_profile = await service.get_user_profile(user["id"])
    if user_profile is None:
        return SmartOJResponse(ResponseCodes.OK, data={})
    result = UserProfileOut.model_validate(user_profile)
    return SmartOJResponse(ResponseCodes.OK, data=result)
