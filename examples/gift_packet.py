import asyncio
from aiobale import Client, Dispatcher
from aiobale.filters import IsGift, IsPrivate
from aiobale.types import Message

dp = Dispatcher()
client = Client(dp)


@dp.message(IsGift(), IsPrivate())
async def handler(msg: Message):
    await client.open_gift(msg)

    await asyncio.sleep(2)
    await msg.answer("Thanks! That was kind — but let me give it back to you.")
    
    packet = msg.content.gift
    await client.send_gift(
        msg.chat.id,
        msg.chat.type,
        packet.total_amount,
        "Thanks... I really appreciate it though.",
    )


client.run()
