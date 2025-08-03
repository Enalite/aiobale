import asyncio
from aiobale import Client, Dispatcher
from aiobale.types import Message

dp = Dispatcher()
client = Client(dp)


def extract_content(msg: Message):
    if msg.document:
        return 'document', msg.document
    elif msg.text:
        return 'text', msg.text
    return None, None


@dp.message()
async def echo(msg: Message):
    type_, value = extract_content(msg)

    if not value and msg.replied_to:
        # This message was not originally sent by the user; it was forwarded from somewhere else
        type_, value = extract_content(msg.replied_to)

    if type_ == 'document':
        return await msg.answer_document(value, use_own_content=True)
    elif type_ == 'text':
        return await msg.answer(value)

    await msg.answer("Nothing to echo!")


async def main():
    await client.start()


asyncio.run(main())
