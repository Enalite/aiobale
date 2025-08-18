from aiobale import Client, Dispatcher
from aiobale.types import Message
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(client: Client):
    print(f"Starting client {client.id}.")
    yield # Keeps the client loop running
    print(f"Client {client.id} has been stopped.")
    

dp = Dispatcher()
main_client = Client(dispatcher=dp, lifespan=lifespan)


@dp.message()
async def handler(message: Message, client: Client):
    await message.answer(f"Hi from client {client.id}.")
    
    
main_client.run()
