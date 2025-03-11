from email.message import EmailMessage

import aiosmtplib

import settings


async def send_email(recipient: str, subject: str, content: str) -> tuple[int, str]:
    message = EmailMessage()
    message["From"] = f"智能算法刷题平台 <{settings.SMTP_CONF['from']}>"
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(content)
    try:
        await aiosmtplib.send(
            message,
            username=settings.SMTP_CONF["from"],
            password=settings.SMTP_CONF["password"],
            hostname=settings.SMTP_CONF["host"],
            port=settings.SMTP_CONF["port"],
            use_tls=True,
        )
    except Exception as e:
        return 0, str(e)
    return 1, ""
