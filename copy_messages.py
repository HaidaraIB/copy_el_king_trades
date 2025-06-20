import logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

log = logging.getLogger(__name__)

from telethon_db import TelethonDB

from telethon import events, TelegramClient
from telethon.tl.patched import Message
import asyncio
import os
import re
from dotenv import load_dotenv

load_dotenv()

FROM = [
    -1002666164924,
    -1002666164924,
]

TO = [
    -1002716122948,
]


TelethonDB.creat_tables()

client = TelegramClient(
    session="session",
    api_hash=os.getenv("API_HASH"),
    api_id=int(os.getenv("API_ID")),
).start(phone=os.getenv("PHONE"))


@client.on(events.NewMessage(chats=FROM))
async def get_post(event: events.NewMessage.Event):
    gallery = getattr(event, "messages", None)
    if event.grouped_id and not gallery:
        return

    await copy_messages(event, gallery, TO)

    raise events.StopPropagation


async def copy_messages(
    event: events.NewMessage.Event, gallery: list[Message], to: list[int]
):
    pattern = r"^[A-Z]{6}\s(BUY|SELL)\sNOW\s\d+\.?\d*[\s\S]*?(\nSl\s*:\s*\d+\.?\d*|\nTp\s*:\s*\d+\.?\d*|\nTp\s*:\s*open)"
    stored_msg = None
    if not event.grouped_id:
        message: Message = event.message
        if not (
            (message.photo and not message.web_preview) or message.video
        ) and re.match(pattern, message.text, re.MULTILINE):
            for channel in to:
                if event.is_reply:
                    stored_msg = TelethonDB.get_messages(
                        from_message_id=message.reply_to_msg_id,
                        from_channel_id=event.chat_id,
                        to_channel_id=channel,
                    )
                msg = await client.send_message(
                    channel,
                    message.text,
                    reply_to=stored_msg[0] if stored_msg else None,
                )
                await TelethonDB.add_message(
                    from_message_id=message.id,
                    to_message_id=msg.id,
                    from_channel_id=event.chat_id,
                    to_channel_id=channel,
                )


async def request_updates(client):
    while True:
        await client.catch_up()
        await asyncio.sleep(5)


log.info("Running....")
client.loop.create_task(request_updates(client))
client.run_until_disconnected()
log.info("Stopping....")
