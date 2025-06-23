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

FROM = [-1002666164924, -1002035975495, -1001271049026]

TO = [-1002716122948]

TelethonDB.creat_tables()

client = TelegramClient(
    session="session",
    api_hash=os.getenv("API_HASH"),
    api_id=int(os.getenv("API_ID")),
).start(phone=os.getenv("PHONE"))


PATTERN = (
    r"(^[A-Z]{6}\s(BUY|SELL)\sNOW\s\d+\.?\d*[\s\S]*?(\nSl\s*:\s*\d+\.?\d*|\nTp\s*:\s*\d+\.?\d*|\nTp\s*:\s*open))|"
    r"((🔴|🟢)\s*(بيع|شراء)\s*[A-Za-z]+\s*من السعر الحالي\s*:\s*\d+\.\d+\s*"
    r"✅\s*هدف أول\s*:\s*\d+\.\d+\s*"
    r"✅\s*هدف ثاني\s*:\s*\d+\.\d+\s*"
    r"✴️\s*يرجى مراعاة إدارة راس المال.*)"
)


@client.on(events.NewMessage(chats=FROM, forwards=False))
async def get_post(event: events.NewMessage.Event):
    gallery = getattr(event, "messages", None)
    if event.grouped_id and not gallery:
        return

    await copy_messages(event, gallery, TO)
    raise events.StopPropagation


@client.on(events.MessageEdited(chats=FROM))
async def handle_edited_message(event: events.MessageEdited.Event):
    gallery = getattr(event, "messages", None)
    if event.grouped_id and not gallery:
        return

    await edit_copied_messages(event, gallery, TO)
    raise events.StopPropagation


async def copy_messages(
    event: events.NewMessage.Event, gallery: list[Message], to: list[int]
):
    stored_msg = None
    if not event.grouped_id:
        message: Message = event.message
        if not (
            (message.photo and not message.web_preview) or message.video
        ) and re.match(PATTERN, message.text, re.MULTILINE | re.IGNORECASE):
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


async def edit_copied_messages(
    event: events.MessageEdited.Event, gallery: list[Message], to: list[int]
):
    if not event.grouped_id:
        message: Message = event.message
        if not (
            (message.photo and not message.web_preview) or message.video
        ) and re.match(PATTERN, message.text, re.MULTILINE | re.IGNORECASE):
            for channel in to:
                stored_msg = TelethonDB.get_messages(
                    from_message_id=message.id,
                    from_channel_id=event.chat_id,
                    to_channel_id=channel,
                )

                if stored_msg:
                    try:
                        await client.edit_message(
                            channel, stored_msg[0], message.text  # to_message_id
                        )
                    except Exception as e:
                        log.error(f"Failed to edit message: {e}")


async def request_updates(client):
    while True:
        await client.catch_up()
        await asyncio.sleep(5)


log.info("Running....")
client.loop.create_task(request_updates(client))
client.run_until_disconnected()
log.info("Stopping....")
