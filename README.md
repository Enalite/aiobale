<p align="center">
  <img src="https://i.postimg.cc/Ssg1Tfhr/banner.png" alt="Aiobale Banner" width="900">
</p>

<h1 align="center">⚡ Aiobale ⚡</h1>
<p align="center"><strong>Async Python Client for Bale Messenger — Modern, Fast, Pythonic</strong></p>

<p align="center">
  <a href="https://pypi.org/project/aiobale"><img src="https://img.shields.io/pypi/v/aiobale?color=brightgreen&logo=pypi" alt="PyPI"></a>
  <a href="https://pepy.tech/project/aiobale"><img src="https://static.pepy.tech/badge/aiobale" alt="Downloads"></a>
  <a href="https://github.com/Enalite/aiobale"><img src="https://img.shields.io/github/stars/Enalite/aiobale?style=social" alt="Stars"></a>
  <a href="https://github.com/Enalite/aiobale"><img src="https://img.shields.io/github/forks/Enalite/aiobale?style=social" alt="Forks"></a>
  <img src="https://img.shields.io/github/last-commit/Enalite/aiobale" alt="Last Commit">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow?logo=open-source-initiative" alt="License"></a>
</p>

---

## 🎉 Welcome! Short & snappy intro

Aiobale is your **friendly, async-first** bridge into Bale Messenger. Think of it as a lightweight, Pythonic toolkit that saves you from tearing your hair out over gRPC and Protobuf — while still giving you power, flexibility, and speed. Perfect for prototyping bots, building integrations, or automating everyday tasks. ✨

This README keeps the essentials upfront and then dives into practical examples, tips, and troubleshooting — so you can get productive fast.

---

## 🚀 What you can build (Ideas)

- Chatbots (auto-responses, moderation, welcome flows) 🤖  
- File processors (auto-download images, apply transforms, re-upload) 📁➡️🖼️  
- Monitoring tools (watch groups/channels & trigger alerts) 🔔  
- Integrations (forward messages to external services, webhooks) 🔗  
- Rapid prototypes and POCs — because async makes iteration fast ⚡

---

## ✨ Key Features (quick)

- Fully async, non-blocking (built on `aiohttp`)  
- Clear, typed models: `Message`, `User`, `Group`, `FileInfo`  
- Dispatcher + filters for neat handler organization (`@dp.message()`)  
- Methods for file upload/download, group management, messaging  
- Session persistence (session files) and auto-reconnect behavior

---

## ✅ Quick Start — Echo Bot (use this exact code)

Copy-paste this and you're running an echo bot in minutes. This is the **same echo code** used in the previous README — unchanged and ready-to-go:

```python
from aiobale import Client, Dispatcher
from aiobale.types import Message

dp = Dispatcher()
client = Client(dp)

@dp.message()
async def echo(msg: Message):
    if content := msg.document:
        await msg.answer_document(content, use_own_content=True)
    elif text := msg.text:
        await msg.answer(text)
    else:
        await msg.answer("Nothing to echo!")

client.run()
```

> Tip: run inside a virtualenv and use `session_file="session.bale"` in `Client(...)` if you want to persist auth between restarts.

---

## 🧪 More examples (short recipes)

**1) Send a quick text message**

```python
await client.send_message(peer_id=12345, message="Hello from Aiobale!", chat_type=1)
```

**2) Download a file by URL from a message**

```python
if msg.document:
    file_url = msg.document.url  # consult docs: some files need GetFileUrl method
    # download with aiohttp and process locally
```


(See `aiobale.methods` for full parameter lists and return types.)

---

## 🛠 Installation

```bash
# Stable release
pip install aiobale

# From GitHub (latest)
pip install git+https://github.com/Enalite/aiobale.git
```

---

## 🧭 Docs & API reference

Full API docs, examples, and method/type reference live on the project's docs site: **docs.aiobale.ir** — check `Methods`, `Types`, and `Filters` sections for complete signatures and usage patterns.

---

## ❓ FAQ & Troubleshooting (fast)

**Q: My bot disconnects randomly — what now?**  
A: Aiobale supports auto-reconnect but network flakiness, invalid sessions, or rate-limits may cause disconnects. Try enabling a `session_file`, check logs, and reduce request burst rates.

**Q: I'm getting permission errors in groups.**  
A: Make sure the authenticated account has the required admin/moderator permissions for those actions. Some methods require owner/admin privileges.

**Q: Where are the method docs?**  
A: `docs.aiobale.ir` and the `aiobale.methods` module source are your friends. Use those to inspect available method classes and their fields.

---

## 🧑‍🤝‍🧑 Contributing & Support

We ❤️ contributions! Ways to help:

- Star the repo ⭐  
- Open issues for bugs or feature requests  
- Submit PRs: small, focused, and with tests if possible  
- Help expand examples and docs — real-world examples are gold

For discussions and quick help, use the Bale channel or Telegram mirror (links below).

---

## ⚖️ License

Aiobale is published under the **MIT License**. See `LICENSE` for full terms.

---

## 🔗 Links & Community

- PyPI: https://pypi.org/project/aiobale  
- GitHub: https://github.com/Enalite/aiobale  
- Docs: https://docs.aiobale.ir  
- Bale channel: https://ble.ir/aiobale  
- Telegram mirror: https://t.me/aiobale

---

<p align="center">
  Built with ❤️ — go build something cool. If you want, I can also prepare a polished `CONTRIBUTING.md`, `ISSUE_TEMPLATE`, or a GitHub Actions CI file to go with this README.
</p>
