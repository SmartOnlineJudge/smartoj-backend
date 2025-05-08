import json
import asyncio

from fastapi import APIRouter, Body, Query
from fastapi.requests import Request
from fastapi.responses import JSONResponse

import settings
from ..user.models import LoginModel, UserListModel
from ..user.route import user_logout
from core.user.auth import authenticate, login, USER_PREFIX, SESSION_PREFIX
from core.user.security import mask
from utils.responses import SmartOJResponse, ResponseCodes
from utils.dependencies import (
    CurrentAdminDependency,
    SessionRedisDependency,
    UserDynamicServiceDependency,
    UserServiceDependency
)
from storage.mysql import executors


router = APIRouter()


@router.post("/user/login", summary="管理员登录")
async def admin_login(request: Request, form: LoginModel):
    """
    ## 参数列表说明:
    **email**: 管理员邮箱号；必须；请求体 </br>
    **password**: 管理员密码；必须；请求体 </br>
    **auth_type**: 用户认证的类型（这里必须填 "password"）；必须；请求体 </br>
    **github_token**: 可选 </br>
    **qq_token**: 可选
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


@router.put("/user", summary="修改管理员信息")
async def update_admin_user(
        admin: CurrentAdminDependency,
        session_redis: SessionRedisDependency,
        service: UserDynamicServiceDependency,
        name: str = Body(max_length=20),
        profile: str = Body(max_length=255),
):
    """
    ## 参数列表说明:
    **name**: 管理员名字（最大长度不超过20）；必须；请求体 </br>
    **profile**: 管理员介绍（最大长度不超过255）；必须；请求体
    ## 响应代码说明:
    **200**: 业务逻辑执行成功
    """

    async def update_db():
        """更新数据库"""
        await service.update(admin["user_id"], {'name': name, 'profile': profile})

    async def update_cache():
        """更新缓存"""
        user_str_id = USER_PREFIX + admin["user_id"]
        user_str = await session_redis.get(user_str_id)
        user_dict = json.loads(user_str)
        user_dict["name"] = name
        user_dict["profile"] = profile
        ex = await session_redis.ttl(user_str_id)
        await session_redis.set(user_str_id, json.dumps(user_dict), ex)

    tasks = [update_db(), update_cache()]
    await asyncio.gather(*tasks)
    return SmartOJResponse(ResponseCodes.OK)


@router.get("/users", summary="分页获取用户信息")
async def get_user_data(
        _: CurrentAdminDependency,
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
    users, total = await executors.user.get_page_user_data(page, size)
    results = []
    for user in users:
        model = UserListModel(**user)
        result = mask(model.model_dump())
        result["is_superuser"] = '是' if user["is_superuser"] else '否'
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
async def update_user_down(
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
    questions, total = await executors.question.get_question_info(page, size)
    q_ids = [q["id"] for q in questions]
    results = []
    publishers = await executors.user_dynamic.get_publisher_by_qid(q_ids)
    tags = await executors.tag.get_tags_by_qid(q_ids)
    tests = await executors.test.get_tests_by_qid(q_ids)
    memory_time_limits = await executors.memory_time_limit.get_memory_limits_by_qid(q_ids)
    solving_frameworks = await executors.solving_framework.get_solving_frameworks_by_qid(q_ids)
    judge_templates = await executors.judge_template.get_judge_templates_by_qid(q_ids)
    languages = await executors.language.get_all_languages()
    lang_dict = {lang["id"]: {"id": lang["id"], "name": lang["name"]} for lang in languages}

    def cat_language(datas):
        return [
            {**data, "language": lang_dict.get(data["lid"])}
            for data in datas
        ]

    memory_time_limits = cat_language(memory_time_limits)
    solving_frameworks = cat_language(solving_frameworks)
    judge_templates = cat_language(judge_templates)
    for question in questions:
        qid = question["id"]
        pid = question["publisher_id"]
        publisher = [{"id": publisher["user_id"], "name": publisher["name"]}
                     for publisher in publishers
                     if publisher["user_id"] == pid]
        del question['publisher_id']
        result = {
            **question,
            "publisher": publisher[0],
            "tags": [{"id": tag["id"], "name": tag["name"]} for tag in tags if tag["qid"] == qid],
            "tests": [{"id": test["id"], "input_output": test["input_output"]} for test in tests if test["qid"] == qid],
            "memory_time_limits": [{"id": memory_time_limit["id"], "memory_limit": memory_time_limit["memory_limit"],
                                    "time_limit": memory_time_limit["time_limit"],
                                    "language": memory_time_limit["language"]} for memory_time_limit in
                                   memory_time_limits if memory_time_limit["qid"] == qid],
            "solving_frameworks": [
                {"id": solving_framework["id"], "code_framework": solving_framework["code_framework"],
                 "language": solving_framework["language"]} for
                solving_framework in solving_frameworks if solving_framework["qid"] == qid],
            "judge_templates": [
                {"id": judge_template["id"], "code": judge_template["code"], "language": judge_template["language"]} for
                judge_template in judge_templates if judge_template["qid"] == qid],
        }
        results.append(result)
    return SmartOJResponse(ResponseCodes.OK, data={"total": total, "results": results})
