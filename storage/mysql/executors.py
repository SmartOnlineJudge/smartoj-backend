from typing import Union

from .multi_executor import (
    UserExecutor,
    UserDynamicExecutor,
    QuestionExecutor,
    TagExecutor,
    QuestionTagExecutor,
    LanguageExecutor,
    SolvingFrameworkExecutor,
    TestExecutor,
    JudgeTemplateExecutor,
    MemoryTimeLimitExecutor,
    SolvedHistoryExecutor,
    JudgeHistoryExecutor,
)


MySQLExecutorTyping = Union[
    UserExecutor,
    UserDynamicExecutor,
    QuestionExecutor,
    TagExecutor,
    QuestionTagExecutor,
    LanguageExecutor,
    SolvingFrameworkExecutor,
    TestExecutor,
    JudgeTemplateExecutor,
    MemoryTimeLimitExecutor,
    SolvedHistoryExecutor,
    JudgeHistoryExecutor,
]


class MySQLExecutors:
    def __init__(self):
        self.executor_classes = {
            "user": UserExecutor,
            "user_dynamic": UserDynamicExecutor,
            "question": QuestionExecutor,
            "tag": TagExecutor,
            "question_tag": QuestionTagExecutor,
            "language": LanguageExecutor,
            "solving_framework": SolvingFrameworkExecutor,
            "test": TestExecutor,
            "judge_template": JudgeTemplateExecutor,
            "memory_time_limit": MemoryTimeLimitExecutor,
            "solved_history": SolvedHistoryExecutor,
            "judge_history": JudgeHistoryExecutor,
        }
        self.executor_instances = {}

    def get_executor(self, executor_name: str) -> MySQLExecutorTyping:
        if executor_name not in self.executor_instances:
            executor_instance = self.executor_classes[executor_name]()
            self.executor_instances[executor_name] = executor_instance
        else:
            executor_instance = self.executor_instances[executor_name]
        return executor_instance

    @property
    def user(self) -> UserExecutor:
        return self.get_executor("user")

    @property
    def user_dynamic(self) -> UserDynamicExecutor:
        return self.get_executor("user_dynamic")

    @property
    def question(self) -> QuestionExecutor:
        return self.get_executor("question")

    @property
    def tag(self) -> TagExecutor:
        return self.get_executor("tag")

    @property
    def question_tag(self) -> QuestionTagExecutor:
        return self.get_executor("question_tag")

    @property
    def language(self) -> LanguageExecutor:
        return self.get_executor("language")

    @property
    def solving_framework(self) -> SolvingFrameworkExecutor:
        return self.get_executor("solving_framework")

    @property
    def test(self) -> TestExecutor:
        return self.get_executor("test")

    @property
    def judge_template(self) -> JudgeTemplateExecutor:
        return self.get_executor("judge_template")

    @property
    def memory_time_limit(self) -> MemoryTimeLimitExecutor:
        return self.get_executor("memory_time_limit")

    @property
    def solved_history(self) -> SolvedHistoryExecutor:
        return self.get_executor("solved_history")

    @property
    def judge_history(self) -> JudgeHistoryExecutor:
        return self.get_executor("judge_history")

    async def initialize(self):
        if not self.executor_instances:
            await self.user.initialize_connection_pool()

    async def destroy(self):
        if self.executor_instances:
            await self.user.close()
