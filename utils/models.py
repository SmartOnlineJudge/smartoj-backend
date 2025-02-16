from datetime import datetime

from pydantic import BaseModel


class DatetimeModel(BaseModel):
    def model_dump(self, *args, **kwargs) -> dict:
        dump = super().model_dump(*args, **kwargs)
        for k, v in dump.items():
            if isinstance(v, datetime):
                dump[k] = v.strftime('%Y-%m-%d %H:%M:%S')
        return dump
