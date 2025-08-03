import asyncio
from PIL import Image
from io import BytesIO
from aiobale import F, Client, Dispatcher
from aiobale.types import Message, FileInput

dp = Dispatcher()
# If you have already logged in, don't use `new.bale`
client = Client(dp, session_file="new.bale")


def make_thumbnail(image_path: str) -> bytes:
    with Image.open(image_path) as img:
        image_format = img.format
        original_width, original_height = img.size
        new_width = 50
        new_height = int((original_height / original_width) * new_width)
        resized = img.resize((new_width, new_height), Image.LANCZOS)

        output = BytesIO()
        resized.save(output, format=image_format)
        return output.getvalue()


def get_image_size(image_path: str) -> tuple[int, int]:
    with Image.open(image_path) as img:
        return img.width, img.height


@dp.message(F.text == "image")
async def image(msg: Message):
    image_path = "image.jpg"
    image_tumnbnail = make_thumbnail(image_path)
    img_w, img_h = get_image_size(image_path)

    # You can also use `client.send_photo`
    await msg.answer_photo(
        FileInput("image.jpg"),
        caption="Test caption",
        cover_thumb=FileInput(image_tumnbnail),
        cover_width=img_w,
        cover_height=img_h,
    )


@dp.message(F.text == "doc")
async def doc(msg: Message):
    await msg.reply_document(FileInput("image.jpg"))


async def main():
    await client.start()


asyncio.run(main())
