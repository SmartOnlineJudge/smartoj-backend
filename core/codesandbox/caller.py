from json.decoder import JSONDecodeError

import httpx

import settings


class CodeSandboxCaller:
    def __init__(self):
        self.url = settings.CODESANDBOX_URL

    async def call(
        self,
        *,
        user_id: str,
        question_id: int,
        solution_code: str,
        language: str,
        judge_template: str,
        tests: list[dict],
        time_limit: int,
        memory_limit: float
    ):
        data = {
            "language": language,
            "question_id": question_id,
            "judge_template": judge_template,
            "solution_code": solution_code,
            "tests": tests,
            "time_limit": time_limit,
            "memory_limit": memory_limit,
            "user_id": user_id
        }
        async with httpx.AsyncClient(timeout=time_limit / 1000 + 100) as client:
            response = await client.post(self.url, json=data)
        try:
            return response.json()
        except JSONDecodeError:
            return {"code": 500, "message": "响应解码异常", "results": []}


codesandbox_caller = CodeSandboxCaller()
