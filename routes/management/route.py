import json
import asyncio
from datetime import datetime, date

from fastapi import APIRouter, Body, Query
from fastapi.requests import Request
from fastapi.responses import JSONResponse

import settings
from ..user.models import LoginModel, UserOutModel
from ..user.route import user_logout
from .models import Question, UserScoreRanking
from core.user.auth import authenticate
from core.user.session import login, USER_PREFIX, SESSION_PREFIX
from core.user.security import mask
from utils.responses import SmartOJResponse, ResponseCodes
from utils.dependencies import (
    CurrentAdminDependency,
    SessionRedisDependency,
    UserServiceDependency,
    TagServiceDependency, 
    LanguageServiceDependency,
    QuestionServiceDependency,
    SubmitRecordDependency,
    UserProfilesServiceDependency,
    CommentServiceDependency,
    SolutionServiceDependency
)

router = APIRouter()


@router.post("/user/login", summary="管理员登录")
async def admin_login(request: Request, form: LoginModel):
    """
    ## 参数列表说明:
    **email**: 管理员邮箱号；必须；请求体 </br>
    **password**: 管理员密码；必须；请求体 </br>
    **auth_type**: 用户认证的类型（这里必须填 "password"）；必须；请求体
    ## 响应代码说明:
    **300**: 登录成功 </br>
    **305**: 账号登录失败，可能是邮箱或密码不正确 </br>
    **310**: 账号登录失败，当前账号权限不足
    """
    user: dict | None = await authenticate(
        email=form.email,
        password=form.password,
        auth_type=form.auth_type.value,
    )
    if not user:
        return SmartOJResponse(ResponseCodes.LOGIN_FAILED)
    if not user["is_superuser"]:
        return SmartOJResponse(ResponseCodes.PERMISSION_DENIED)
    session_id = await login(request, user)
    response_data = SmartOJResponse(ResponseCodes.LOGIN_SUCCESS)
    response = JSONResponse(response_data.model_dump())
    response.set_cookie(
        key="session_id",
        value=session_id,
        max_age=settings.SESSION_MAX_AGE,
        httponly=True,
    )
    return response


@router.post("/user/logout", summary="管理员退出登录")
async def admin_logout(request: Request):
    return await user_logout(request)


@router.get("/user", summary="获取当前管理员信息")
async def get_admin_user(admin: CurrentAdminDependency):
    return SmartOJResponse(ResponseCodes.OK, data=mask(admin))


@router.get("/users", summary="分页获取用户信息")
async def get_user_data(
        _: CurrentAdminDependency,
        service: UserServiceDependency,
        page: int = Query(1, ge=1),
        size: int = Query(5, ge=1)
):
    """
    ## 参数列表说明:
    **page**: 查询的页码；必须；默认为1；查询参数 </br>
    **size**: 每页的数据数；必须；请求体；默认为5；查询参数 </br>
    ## 响应代码说明:
    **200**: 业务逻辑执行成功
    """
    users, total = await service.query_by_page(page, size)

    results = []
    for user in users:
        result = UserOutModel.model_validate(user)
        result = result.model_dump()
        user_dynamic = result.pop("user_dynamic")
        result.update(user_dynamic)
        result["is_superuser"] = '是' if result["is_superuser"] else '否'
        result = mask(result, mask_id=False)
        results.append(result)
    return SmartOJResponse(ResponseCodes.OK, data={"total": total, "results": results})


@router.get("/user/status", summary="分页获取用户登录状态信息")
async def get_user_status(
        _: CurrentAdminDependency,
        session_redis: SessionRedisDependency,
        page: int = Query(1, ge=1),
        size: int = Query(5, ge=1),
):
    """
    ## 参数列表说明:
    **page**: 查询的页码；必须；默认为1；查询参数 </br>
    **size**: 每页的数据数；必须；请求体；默认为5；查询参数 </br>
    ## 响应代码说明:
    **200**: 业务逻辑执行成功
    """
    results = []

    session_keys = await session_redis.keys(SESSION_PREFIX + "*")

    # 解析每个 session 的数据，提取 first_login 时间
    sessions = []
    for key in session_keys:
        session_str = await session_redis.get(key)
        session_dict = json.loads(session_str)
        sessions.append({
            "key": key,
            "first_login": session_dict.get("first_login", ""),  # 提取 first_login 时间
            "session_dict": session_dict  # 保存完整的 session_dict
        })

    # 按照 first_login 时间降序排序
    # 如果 first_login 为空字符串，则将其排在最后
    sessions.sort(key=lambda x: x["first_login"] or "0", reverse=True)

    # 分页逻辑
    total = len(sessions)
    start = (page - 1) * size
    end = page * size if page * size < total else total
    paginated_sessions = sessions[start:end]

    # 构造返回结果
    for session in paginated_sessions:
        session_dict = session["session_dict"]
        user_str = await session_redis.get(USER_PREFIX + session_dict["user_id"])
        user_dict = json.loads(user_str)
        result_dict = {
            "session_id": session["key"].split(":")[-1],
            "user_id": session_dict["user_id"],
            "name": user_dict.get("name", ""),
            "host": session_dict.get("host", ""),
            "platform": session_dict.get("platform", ""),
            "browser": session_dict.get("browser", ""),
            "first_login": session_dict.get("first_login", ""),
            "last_active": session_dict.get("last_active", "")
        }
        results.append(result_dict)

    return SmartOJResponse(ResponseCodes.OK, data={"total": total, "results": results})


@router.patch("/user", summary="禁用用户")
async def update_user_deleted(
        admin: CurrentAdminDependency,
        session_redis: SessionRedisDependency,
        service: UserServiceDependency,
        user_id: str = Body(max_length=13),
        is_deleted: bool = Body(),
):
    """
    ## 参数列表说明:
    **user_id**: 要修改信息的用户id（最大长度不超过20）；必须；请求体 </br>
    **is_deleted**: 该用户是否禁用（bool值）；必须；请求体 </br>
    ## 响应代码说明:
    **200**: 业务逻辑执行成功</br>
    **310**: 当前帐号权限不足，管理员不能禁用自己的账号
    """

    async def update_db():
        """更新数据库"""
        await service.update(user_id, {"is_deleted": is_deleted})

    async def update_cache():
        """更新缓存"""
        user_str_id = USER_PREFIX + user_id
        if await session_redis.exists(user_str_id) == 0:
            return
        user_str = await session_redis.get(user_str_id)
        user_dict = json.loads(user_str)
        user_dict["is_deleted"] = is_deleted
        ex = await session_redis.ttl(user_str_id)
        await session_redis.set(user_str_id, json.dumps(user_dict), ex)

    if user_id == admin["user_id"]:
        return SmartOJResponse(ResponseCodes.PERMISSION_DENIED)
    tasks = [update_db(), update_cache()]
    await asyncio.gather(*tasks)
    return SmartOJResponse(ResponseCodes.OK)


@router.delete("/user", summary="强制用户下线")
async def update_user_offline(
        _: CurrentAdminDependency,
        session_redis: SessionRedisDependency,
        session_id: str = Body(max_length=32, embed=True),
):
    """
    ## 参数列表说明:
    **session_id**: 要下线用户的session_id（最大长度不超过32）；必须；请求体 </br>
    ## 响应代码说明:
    **200**: 业务逻辑执行成功
    """
    session_str_id = SESSION_PREFIX + session_id
    await session_redis.delete(session_str_id)
    return SmartOJResponse(ResponseCodes.OK)


@router.get("/questions", summary="题目信息查询")
async def get_question_info(
        _: CurrentAdminDependency,
        service: QuestionServiceDependency,
        page: int = Query(1, ge=1),
        size: int = Query(5, ge=1),
):
    """
    ## 参数列表说明:
    **page**: 查询的页码；必须；默认为1；查询参数 </br>
    **size**: 每页的数据数；必须；请求体；默认为5；查询参数 </br>
    ## 响应代码说明:
    **200**: 业务逻辑执行成功
    """
    questions, total = await service.query_by_page(page, size)
    results = [Question.model_validate(question) for question in questions]
    return SmartOJResponse(ResponseCodes.OK, data={"total": total, "results": results})


@router.post("/tag", summary="添加新标签")
async def tag_add(
        _: CurrentAdminDependency,
        service: TagServiceDependency,
        name: str = Body(),
        score: int = Body(ge=1)
):
    """
    ## 参数列表说明:
    **name**: 添加的标签名；必须；请求体 </br>
    **score**: 添加标签对应的分数；必须；请求体 </br>
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    """
    await service.create(name=name, score=score)
    return SmartOJResponse(ResponseCodes.OK)


@router.put("/tag", summary="更新标签")
async def tag_update(
        _: CurrentAdminDependency,
        service: TagServiceDependency,
        tag_id: int = Body(ge=1),
        name: str = Body(),
        score: int = Body(ge=1)
):
    """
    ## 参数列表说明:
    **tag_id**: 需要更新的标签的id；必须；请求体 </br>
    **name**: 更新的标签名；必须；请求体 </br>
    **score**: 更新标签对应的分数；必须；请求体 </br>
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    """
    await service.update(tag_id=tag_id, document={"name": name, "score": score})
    return SmartOJResponse(ResponseCodes.OK)


@router.delete("/tag", summary="禁用标签")
async def tag_delete(
        _: CurrentAdminDependency,
        service: TagServiceDependency,
        tag_id: int = Body(ge=1),
        is_deleted: bool = Body()
):
    """
    ## 参数列表说明:
    **tag_id**: 需要禁用的标签的id；必须；请求体 </br>
    **is_deleted**: 该标签是否禁用（bool值）；必须；请求体 </br>
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    """
    await service.update(tag_id=tag_id, document={"is_deleted": is_deleted})
    return SmartOJResponse(ResponseCodes.OK)


@router.post("/language", summary="添加新编程语言")
async def language_add(
        _: CurrentAdminDependency,
        service: LanguageServiceDependency,
        name: str = Body(),
        version: str = Body()
):
    """
    ## 参数列表说明:
    **name**: 添加的编程语言名；必须；请求体 </br>
    **version**: 添加编程语言对应的版本；必须；请求体 </br>
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    """
    await service.create(name=name, version=version)
    return SmartOJResponse(ResponseCodes.OK)


@router.put("/language", summary="更新编程语言信息")
async def language_update(
        _: CurrentAdminDependency,
        service: LanguageServiceDependency,
        language_id: int = Body(ge=1),
        name: str = Body(),
        version: str = Body()
):
    """
    ## 参数列表说明:
    **language_id**: 需要更新的编程语言的id；必须；请求体 </br>
    **name**: 更新的编程语言名；必须；请求体 </br>
    **version**: 更新编程语言版本；必须；请求体 </br>
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    """
    await service.update(language_id=language_id, document={"name": name, "version": version})
    return SmartOJResponse(ResponseCodes.OK)


@router.delete("/language", summary="禁用编程语言")
async def language_delete(
        _: CurrentAdminDependency,
        service: LanguageServiceDependency,
        language_id: int = Body(ge=1),
        is_deleted: bool = Body()
):
    """
    ## 参数列表说明:
    **language_id**: 需要禁用的编程语言的id；必须；请求体 </br>
    **is_deleted**: 该语言是否禁用（bool值）；必须；请求体 </br>
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    """
    await service.update(language_id=language_id, document={"is_deleted": is_deleted})
    return SmartOJResponse(ResponseCodes.OK)


@router.get("/dashboard/users", summary="获取用户总数和在线用户数")
async def get_dashboard_users(
    _: CurrentAdminDependency,
    session_redis: SessionRedisDependency,
    service: UserServiceDependency,
):
    """
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    """
    session_keys = await session_redis.keys(SESSION_PREFIX + "*")
    online_users = len(session_keys)
    _, total = await service.query_by_page(1, 1)
    return SmartOJResponse(ResponseCodes.OK, data={"total_users": total, "online_users": online_users})


@router.get("/dashboard/submissions", summary="获取指定日期的提交数量")
async def get_dashboard_submissions(
    _: CurrentAdminDependency,
    service: SubmitRecordDependency,
    target_date: date = Query(datetime.now().date()),
):
    """
    ## 请求参数说明:
    **target_date**: 指定日期；可选，如果没有则默认为当前日期；查询参数
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    """
    count = await service.count_by_date(target_date)
    return SmartOJResponse(ResponseCodes.OK, data={"submissions": count})


@router.get("/dashboard/submission-distribution-by-hour", summary="获取每小时的提交分布")
async def get_dashboard_submission_distribution(
    _: CurrentAdminDependency,
    service: SubmitRecordDependency,
):
    """
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    """
    data = await service.count_submissions_by_hour()
    return SmartOJResponse(ResponseCodes.OK, data={"submission_distribution": data})


@router.get("/dashboard/submission-distribution-by-language", summary="获取编程语言的提交分布")
async def get_dashboard_submission_distribution(
    _: CurrentAdminDependency,
    service: SubmitRecordDependency,
):
    """
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    """
    data = await service.count_submissions_by_language()
    return SmartOJResponse(ResponseCodes.OK, data={"submission_distribution": data})


@router.get("/dashboard/ranking/score", summary="获取用户总分排行榜")
async def get_dashboard_ranking_score(
    _: CurrentAdminDependency,
    service: UserProfilesServiceDependency,
):
    """
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    """
    data = await service.get_top_users_by_score()
    results = [UserScoreRanking.model_validate(d) for d in data]
    return SmartOJResponse(ResponseCodes.OK, data={"results": results})


@router.get("/dashboard/ranking/comment-count", summary="获取用户评论排行榜")
async def get_dashboard_ranking_comment_count(
    _: CurrentAdminDependency,
    service: CommentServiceDependency,
):
    """
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    """
    data = await service.get_top_users_by_comment_count()
    results = []
    for user_id, name, avatar, comment_count in data:
        results.append({
            "user_id": user_id,
            "name": name,
            "avatar": avatar,
            "comment_count": comment_count
        })
    return SmartOJResponse(ResponseCodes.OK, data={"results": results})


@router.get("/dashboard/ranking/solution-count", summary="获取用户题解排行榜")
async def get_dashboard_ranking_solution_count(
    _: CurrentAdminDependency,
    service: SolutionServiceDependency,
):
    """
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    """
    service.create
    data = await service.get_top_users_by_solution_count()
    results = []
    for user_id, name, avatar, solution_count in data:
        results.append({
            "user_id": user_id,
            "name": name,
            "avatar": avatar,
            "solution_count": solution_count
        })
    return SmartOJResponse(ResponseCodes.OK, data={"results": results})
