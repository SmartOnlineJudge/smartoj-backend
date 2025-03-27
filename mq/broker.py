from taskiq_redis import RedisAsyncResultBackend
from taskiq_aio_pika import AioPikaBroker

import settings
from utils.mail import send_email


_mq_conf = settings.REDIS_CONF["mq"]
if _mq_conf["PASSWORD"] is not None:
    _redis_url = f"redis://:{_mq_conf['PASSWORD']}@{_mq_conf['HOST']}:{_mq_conf['PORT']}/{_mq_conf['DB']}"
else:
    _redis_url = f"redis://{_mq_conf['HOST']}:{_mq_conf['PORT']}/{_mq_conf['DB']}"

broker = AioPikaBroker(
    url=settings.RABBITMQ_CONF["url"],
).with_result_backend(RedisAsyncResultBackend(redis_url=_redis_url))


@broker.task("send-email")
async def send_email_task(recipient: str, subject: str, content: str):
    await send_email(recipient, subject, content)
