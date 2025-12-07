from datetime import datetime
from typing import Any

from sqlmodel import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func, text

from ..base import MySQLService
from ..user.models import User
from .models import Comment, Solution, Message


class SolutionService(MySQLService):
    async def query_by_user_and_question_id(self, user_id: int, question_id: int):
        statement = (
            select(Solution)
            .where(
                Solution.user_id == user_id, 
                Solution.is_deleted == False,
                Solution.question_id == question_id
            )
            .options(selectinload(Solution.user).selectinload(User.user_dynamic))
        )
        solution = await self.session.exec(statement)
        return solution.first()

    async def query_by_primary_key(self, solution_id: int):
        statement = (
            select(Solution)
            .where(Solution.id == solution_id, Solution.is_deleted == False)
            .options(selectinload(Solution.user).selectinload(User.user_dynamic))
        )
        solution = await self.session.exec(statement)
        return solution.first()

    async def get_solutions_by_user_id(self, user_id: int, page: int = 1, size: int = 5):
        solutions_statement = (
            select(Solution)
            .where(
                Solution.user_id == user_id,
                Solution.is_deleted == False
            )
            .options(selectinload(Solution.question))
            .order_by(Solution.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        solutions = await self.session.exec(solutions_statement)
        # 计算总数
        total_statement = (
            select(func.count(Solution.id))
            .where(
                Solution.user_id == user_id,
                Solution.is_deleted == False
            )
        )
        total = await self.session.scalar(total_statement)
        return solutions.all(), total

    async def create(self, user_id: int, content: str, title: str, question_id: int):
        solution = Solution(
            user_id=user_id,
            content=content,
            title=title,
            question_id=question_id
        )
        self.session.add(solution)
        await self.session.commit()

    async def update(self, solution_id: int, user_id: int, content: str, title: str):
        sql = text("UPDATE solution SET content = :content, title = :title WHERE id = :solution_id AND user_id = :user_id")
        await self.session.exec(sql, params={"solution_id": solution_id, "user_id": user_id, "content": content, "title": title})
        await self.session.commit()

    async def logic_delete(self, solution_id: int, user_id: int, superuser_mode: bool = False):
        if superuser_mode:  # 管理员模式，不需要验证该题解是否是自己的
            statement = select(Solution).where(Solution.id == solution_id)
        else:
            statement = select(Solution).where(Solution.id == solution_id, Solution.user_id == user_id)
        result = await self.session.exec(statement)
        solution = result.first()

        if solution is None:
            return False

        delete_comment_sql = text("UPDATE comment SET is_deleted = 1 WHERE target_id = :solution_id and type = 'solution'")
        self.session.begin()
        try:
            solution.is_deleted = True
            self.session.add(solution)
            await self.session.exec(delete_comment_sql, params={"solution_id": solution_id})
            await self.session.commit()
        except Exception as _:
            await self.session.rollback()
            return False
        return True
    
    async def increment_(self, solution_id: int, field: str):
        sql = text(f"UPDATE solution SET {field} = {field} + 1 WHERE id = :solution_id")
        await self.session.exec(sql, params={"solution_id": solution_id})
        await self.session.commit()

    async def increment_view_count(self, solution_id: int):
        return await self.increment_(solution_id, "view_count")

    async def increment_comment_count(self, solution_id: int):
        return await self.increment_(solution_id, "comment_count")

    async def get_solution_list(self, question_id: int, last_created_at: datetime, size: int = 5):
        statement = (
            select(Solution, func.substr(Solution.content, 1, 50).label("content_preview"))
            .where(
                Solution.question_id == question_id,
                Solution.is_deleted == False,
                Solution.created_at < last_created_at
            )
            .options(selectinload(Solution.user).selectinload(User.user_dynamic))
            .order_by(Solution.created_at.desc())
            .limit(size)
        )
        solutinos = await self.session.exec(statement)
        return solutinos.all()


class CommentService(MySQLService):
    async def create(
        self, 
        user_id: int, 
        content: str, 
        root_comment_id: int, 
        target_id: int, 
        to_comment_id: int, 
        type: str
    ):
        comment = Comment(
            user_id=user_id,
            content=content,
            root_comment_id=root_comment_id,
            target_id=target_id,
            to_comment_id=to_comment_id,
            type=type
        )
        self.session.add(comment)
        await self.session.commit()
        await self.session.refresh(comment)
        return {"id": comment.id, "created_at": comment.created_at}

    async def logic_delete(self, comment_id: int, user_id: int, superuser_mode: bool = False):
        if superuser_mode:  # 管理员模式，不需要验证该评论是否是自己的
            statement = select(Comment).where(Comment.id == comment_id)
        else:
            statement = select(Comment).where(Comment.id == comment_id, Comment.user_id == user_id)
        result = await self.session.exec(statement)
        comment = result.first()
        if comment is None:
            return False
        
        # 如果评论是一级评论：
        # 1. 类型是solution：将全部子评论和自己删除，将题解的评论数减去该一级评论的回复数+1
        # 2. 类型是question：将全部子评论和自己删除
        # 如果评论是子评论：
        # 1. 类型是solution：将自己删除，将题解的评论数和一级评论的回复数减去1
        # 2. 类型是question：将自己删除，将一级评论的回复数减去1
        decrement_count = 0
        delete_children_sql = None
        update_solution_comment_count_sql = None
        update_root_comment_reply_count_sql = None

        if comment.type == "solution":
            update_solution_comment_count_sql = text("UPDATE solution SET comment_count = comment_count - :decrement_count WHERE id = :target_id")
        if comment.root_comment_id is None:
            delete_children_sql = text("UPDATE comment SET is_deleted = 1 WHERE root_comment_id = :comment_id")
            if comment.type == "solution":
                decrement_count = comment.reply_count + 1
        else:
            update_root_comment_reply_count_sql = text("UPDATE comment SET reply_count = reply_count - 1 WHERE id = :root_comment_id")
            if comment.type == "solution":
                decrement_count = 1
            
        self.session.begin()
        try:
            comment.is_deleted = True
            self.session.add(comment)
            if delete_children_sql is not None:
                await self.session.exec(delete_children_sql, params={"comment_id": comment_id})
            if update_solution_comment_count_sql is not None:
                await self.session.exec(update_solution_comment_count_sql, params={"decrement_count": decrement_count, "target_id": comment.target_id})
            if update_root_comment_reply_count_sql is not None:
                await self.session.exec(update_root_comment_reply_count_sql, params={"root_comment_id": comment.root_comment_id})
            await self.session.commit()
        except Exception as _:
            await self.session.rollback()
            return False
        return True

    async def get_root_comments(self, target_id: int, comment_type: str, page: int = 1, size: int = 10):
        statement = (
            select(Comment)
            .where(
                Comment.target_id == target_id,
                Comment.type == comment_type,
                Comment.root_comment_id.is_(None),
                Comment.is_deleted == False
            )
            .options(selectinload(Comment.user).selectinload(User.user_dynamic))
            .order_by(Comment.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        comments = await self.session.exec(statement)
        # 统计一级评论的数量
        count_statement = statement = (
            select(func.count(Comment.id))
            .where(
                Comment.target_id == target_id,
                Comment.type == comment_type,
                Comment.root_comment_id.is_(None),
                Comment.is_deleted == False
            )
        )
        total = await self.session.scalar(count_statement)
        return comments.all(), total
    
    async def get_comment_count(self, target_id: int, comment_type: str):
        statement = (
            select(func.count(Comment.id))
            .where(
                Comment.target_id == target_id,
                Comment.type == comment_type,
                Comment.is_deleted == False
            )
        )
        return await self.session.scalar(statement)

    async def increment_reply_count(self, comment_id: int):
        sql = text("UPDATE comment SET reply_count = reply_count + 1 WHERE id = :comment_id")
        await self.session.exec(sql, params={"comment_id": comment_id})
        await self.session.commit()

    async def get_child_comments(self, root_comment_id: int, last_created_at: datetime, size: int = 5):
        statement = (
            select(Comment)
            .where(
                Comment.root_comment_id == root_comment_id,
                Comment.is_deleted == False,
                Comment.created_at > last_created_at
            )
            .options(selectinload(Comment.user).selectinload(User.user_dynamic))
            .order_by(Comment.created_at)
            .limit(size)
        )
        comments = await self.session.exec(statement)
        return comments.all()

    async def get_comments_by_user_id(self, user_id: int, page: int = 1, size: int = 10):
        statement = (
            select(Comment)
            .where(Comment.user_id == user_id, Comment.is_deleted == False)
            .order_by(Comment.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        comments = await self.session.exec(statement)
        count_statement = (
            select(func.count(Comment.id))
            .where(Comment.user_id == user_id, Comment.is_deleted == False)
        )
        total = await self.session.scalar(count_statement)
        return comments.all(), total

    async def query_by_primary_key(self, comment_id: int):
        statement = (
            select(Comment)
            .where(Comment.id == comment_id, Comment.is_deleted == False)
            .options(selectinload(Comment.user).selectinload(User.user_dynamic))
        )
        return await self.session.scalar(statement)


class MessageService(MySQLService):
    async def create(self, sender_id: int | None, recipient_id: int, title: str, content: str, type: str):
        message = Message(
            sender_id=sender_id,
            recipient_id=recipient_id,
            title=title,
            content=content,
            type=type
        )
        self.session.add(message)
        await self.session.commit()

    async def get_message_count(self, recipient_id: int, is_read: bool | None = None):
        if is_read is not None:
            statement = (
                select(func.count(Message.id))
                .where(
                    Message.recipient_id == recipient_id,
                    Message.is_read == is_read,
                    Message.is_deleted == False
                )
            )
        else:
            statement = (
                select(func.count(Message.id))
                .where(
                    Message.recipient_id == recipient_id,
                    Message.is_deleted == False
                )
            )
        return await self.session.scalar(statement)

    async def get_messages_by_recipient_id(self, recipient_id: int, page: int = 1, size: int = 5):
        statement = (
            select(Message)
            .where(
                Message.recipient_id == recipient_id,
                Message.is_deleted == False
            )
            .order_by(Message.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        messages = await self.session.exec(statement)
        return messages.all()

    async def update(self, message_id: int, document: dict[str, Any]):
        message = await self.session.get(Message, message_id)
        if message is None:
            return
        for key, value in document.items():
            setattr(message, key, value)
        self.session.add(message)
        await self.session.commit()

    async def query_by_primary_key(self, message_id: int):
        statement = (
            select(Message)
            .where(Message.id == message_id, Message.is_deleted == False)
        )
        return await self.session.scalar(statement)
