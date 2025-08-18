from aiobale import Client, Dispatcher
from aiobale.types import Message
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(client: Client):
    print(f"Starting client {client.id}.")
    yield # Keeps the client loop running
    print(f"Client {client.id} has been stopped.")
    

dp = Dispatcher()
client = Client(dispatcher=dp, lifespan=lifespan)


@dp.message()
async def handler(message: Message):
    await message.answer("Hi from Aiobale!")
    
    
client.run()
