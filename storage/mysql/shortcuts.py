from .executors import MySQLExecutors

executors = MySQLExecutors()


async def create_user_and_dynamic(
    name: str,
    password: str = None,
    email: str = "",
    github_token: str = "",
    qq_token: str = "",
    is_superuser: bool = False,
    profile: str = "",
    avatar: str = "",
) -> tuple[int, int]:
    user_row_id = await executors.user.create_user(
        password=password,
        email=email,
        github_token=github_token,
        qq_token=qq_token,
        is_superuser=is_superuser,
    )
    dynamic_id = await executors.user_dynamic.create_user_dynamic(
        user_id=user_row_id,
        name=name,
        profile=profile,
        avatar=avatar,
    )
    return user_row_id, dynamic_id
