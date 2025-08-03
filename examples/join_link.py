import asyncio
import re
from typing import Optional
from aiobale import Client, Dispatcher
from aiobale.types import Message
from aiobale.filters import IsText

dp = Dispatcher()
client = Client(dp)


def get_link(text: str) -> Optional[dict]:
    text = text.strip()

    join_pattern = r"^(?:https?://)?ble\.ir/join/([a-zA-Z0-9_-]+)$"
    username_link_pattern = r"^(?:https?://)?ble\.ir/([a-zA-Z0-9_.-]+)$"
    at_username_pattern = r"^@([a-zA-Z0-9_.-]+)$"

    if match := re.match(join_pattern, text):
        return {"type": "join", "value": match.group(1)}
    elif match := re.match(username_link_pattern, text):
        return {"type": "username", "value": match.group(1)}
    elif match := re.match(at_username_pattern, text):
        return {"type": "username", "value": match.group(1)}
    else:
        return None


@dp.message(IsText())
async def join(msg: Message):
    link_data = get_link(msg.text)
    if not link_data:
        return await msg.answer("No link found!!!")
    
    link_type, link_value = link_data["type"], link_data["value"]
    if link_type == "join":
        await client.join_chat(link_value)
        await msg.answer("Joined the private group/channel.")
    else:
        result = await client.search_username(link_value)
        if result.group is None:
            return await msg.answer("Could not fetch public group/channel data.")
        
        chat_id = result.group.id
        await client.join_public_chat(chat_id)
        await msg.answer("Joined the public group/channel.")
    

async def main():
    await client.start()


asyncio.run(main())
