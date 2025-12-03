from datetime import datetime

from sqlmodel import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func, text

from ..base import MySQLService
from ..user.models import User
from .models import Comment


class SolutionService(MySQLService):
    pass


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
        comment.is_deleted = True
        self.session.add(comment)
        await self.session.commit()
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
                Comment.created_at < last_created_at
            )
            .options(selectinload(Comment.user).selectinload(User.user_dynamic))
            .order_by(Comment.created_at.desc())
            .limit(size)
        )
        comments = await self.session.exec(statement)
        return comments.all()
