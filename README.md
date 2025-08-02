<p align="center">
  <img src="https://i.postimg.cc/Ssg1Tfhr/banner.png" alt="Aiobale Banner">
</p>

<h1 align="center">Aiobale — Async Bale API Client, Built on Reverse Engineering & Obsession</h1>

<p align="center">
  A clean, developer-friendly Python client for <b>Bale Messenger’s</b> internal API — reverse-engineered with care, curiosity, and persistence.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/PyPI-v0.1.3-brightgreen?logo=pypi">
  <img src="https://img.shields.io/badge/Python-3.8%20%7C%203.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-green?logo=python">
  <img src="https://img.shields.io/badge/License-MIT-blue?logo=open-source-initiative">
  <img src="https://img.shields.io/badge/Coverage-100%25-brightgreen?logo=codecov&logoColor=white">
</p>

---

**Documentation**: <a href="https://docs.aiobale.ir" target="_blank">https://docs.aiobale.ir</a>

---

### ⚡ What is Aiobale?

**Aiobale** is an asynchronous Python library for accessing **Bale’s internal gRPC API** — built entirely from scratch, without `.proto` files or official documentation.

It transforms the raw complexity of Bale’s encrypted Protobuf-based network into **simple, Pythonic classes and methods** — ready for real-world use.

---

## ✨ Features

- 💬 Asynchronous, fast, and non-blocking — built on top of **aiohttp**
- 🔎 Works directly with **Bale’s internal gRPC API**
- 🔄 Supports phone login, messaging, bots, presence, files, and more
- 🧠 Clean, readable API with type hints and smart data classes
- ⚙️ Handler-based routing with decorators (inspired by modern bot frameworks)
- 🌙 Reverse-engineered from the web client, no official help
- 🛠 Built by one determined developer — with room to grow!

> 🎯 **Use Cases**: Build bots, track stats, explore Bale’s ecosystem, automate tasks, and more.

---

## 📦 Installation

```bash
pip install aiobale
````

Or get the latest development version from GitHub:

```bash
pip install git+https://github.com/Enalite/aiobale.git
```

---

> ⚠️ **Please Read Carefully**

Bale’s official client uses `POST` gRPC requests **primarily for a few authentication methods**.
Excessive use of such requests for **non-authentication purposes** (e.g., messaging, presence, media) may raise flags, result in **rate limiting**, or even lead to **temporary bans**.

**Aiobale is provided as-is, without any guarantees or endorsement from Bale.**
It is intended strictly for **educational and ethical use** — please avoid any misuse, such as spam, scraping, or violating Bale’s terms of service.

---

## 🪄 Example: Echo Bot in 10 Lines

Here’s a minimal bot that replies with the same message (and echoes back documents too):

```python
import asyncio
from aiobale import Client, Dispatcher
from aiobale.types import Message

dp = Dispatcher()
client = Client(dp)

@dp.message()
async def echo(msg: Message):
    if content := msg.content.document:
        return await msg.answer_document(content, use_own_content=True)
    elif text := msg.text:
        return await msg.answer(text)
    await msg.answer("Nothing to echo!")

async def main():
    await client.start()

asyncio.run(main())
```

Want more? Visit [**docs.aiobale.ir**](https://docs.aiobale.ir) for comprehensive examples and advanced handler customization.

---

## 🌐 Documentation

📚 Full documentation available at: [**docs.aiobale.ir**](https://docs.aiobale.ir)
Covers everything from login and messaging to custom handlers, internals, and advanced usage.

---

## 🧑‍💻 Contributing

We’d love your help to improve and grow this project!
Here’s how you can get involved:

* ⭐ **Star** the repo to show your support
* 🐞 Report bugs, request features, or ask questions via Issues
* 🧩 Submit pull requests — code, docs, tests, or even typo fixes
* 📣 Share Aiobale with other developers and reverse engineers
* ✍️ Help document unknown methods or Protobuf structures

> Every contribution matters — even fixing a typo is a step forward.

---

## 👤 Author

Crafted with dedication by **Alireza Jahani** ([`@enalite`](https://github.com/enalite)) —
the result of countless hours spent decoding packets, chasing edge cases, and sipping coffee. ☕

---

## 📄 License

Aiobale is released under the [MIT License](https://github.com/Enalite/aiobale/blob/main/LICENSE).
You’re free to use, modify, and contribute — just use it responsibly.

---

## 🔗 Links

* 📦 PyPI: [pypi.org/project/aiobale](https://pypi.org/project/aiobale)
* 💻 GitHub: [github.com/Enalite/aiobale](https://github.com/Enalite/aiobale)
* 📢 Bale Channel: [ble.ir/aiobale](https://ble.ir/aiobale)
* 💬 Telegram Mirror: [t.me/aiobale](https://t.me/aiobale)
* 📘 Docs: [docs.aiobale.ir](https://docs.aiobale.ir)

---

## 🤝 Final Words

Aiobale is **more than just a library** — it's a gateway to the inner workings of a unique messaging ecosystem.
If you enjoy diving into internals, decoding protocols, and building tools that weren't supposed to exist — you're in the right place.

Let’s shape the future of unofficial Bale tooling — together.
