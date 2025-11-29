from datetime import datetime, date

from sqlmodel import SQLModel


class SmartOJSQLModel(SQLModel):
    """
    针对字段类型为日期时间的序列化操作进一步封装。
    """

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.strftime("%Y-%m-%d %H:%M:%S"),
            date: lambda dt: dt.strftime("%Y-%m-%d")
        }

    def model_dump(self, *args, **kwargs) -> dict:
        dump = super().model_dump(*args, **kwargs)
        for k, v in dump.items():
            if isinstance(v, datetime):
                dump[k] = v.strftime("%Y-%m-%d %H:%M:%S")
            elif isinstance(v, date):
                dump[k] = v.strftime("%Y-%m-%d")
        return dump
