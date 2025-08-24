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

## Overview

Aiobale is a modern, fully asynchronous Python client that exposes Bale Messenger’s internal API in a developer-friendly, Pythonic way. It provides high-level primitives (Client, Dispatcher, Methods, Types, Filters) so you can build bots, automation, monitoring tools, and integrations without dealing directly with gRPC or Protobuf. citeturn2view0

**Key facts (snapshot):**
- Public GitHub repository with active commits, releases, and contributors. citeturn0view0
- Latest release: **v0.1.5** (see Releases). citeturn0view0
- Official docs / API reference are published at `docs.aiobale.ir` (Methods, Types, Filters, Examples). citeturn2view0

---

## Why Aiobale?

- **Async-first & lightweight**: built on `aiohttp` for non-blocking, scalable bots. citeturn2view0
- **Reverse-engineered**: provides a usable API surface despite the lack of official `.proto` files. citeturn2view0
- **Type-safe models**: dataclasses/types for messages, users, groups, files, and more (see Types & Responses in docs). citeturn2view0
- **Event-driven Dispatcher**: write clean handlers using decorators (`@dp.message()`, routers, filters). citeturn2view0

---

## Features (Expanded)

- 🚀 Fully async (aiohttp)
- 📬 Messaging: send/update/forward/delete, read receipts
- 📎 Media & Files: upload, download, get file URLs
- 🧭 Groups & Channels: create, invite, moderation, permissions
- 🔔 Presence & Typing: set online, typing indicators
- 🔒 Auth shims: phone auth, code validation, session handling
- 🧰 Utilities: Filters, Router, EventObserver, and pluggable Handlers
(Full Methods & Types: see docs). citeturn2view0

---

## Quick Start — Echo Bot (Detailed)

```python
# echo_bot.py
from aiobale import Client, Dispatcher
from aiobale.types import Message
from aiobale.filters import IsText, IsDocument

dp = Dispatcher()
client = Client(dp, session_file="session.bale")  # persist session to file

@dp.message(IsText())
async def echo_text(msg: Message):
    await msg.answer(f"You said: {msg.text}")

@dp.message(IsDocument())
async def echo_file(msg: Message):
    # reply with same document (use_own_content depends on API semantics)
    if msg.document:
        await msg.answer_document(msg.document, use_own_content=True)

if __name__ == "__main__":
    client.run()
```

> Notes:
> - `session_file` lets Aiobale store and reuse authenticated sessions.
> - Use Filters from `aiobale.filters` to keep handlers focused and small. citeturn2view0

---

## Examples & Recipes

**1) Uploading a file and sending to a chat**

```python
from aiobale import Client, Dispatcher
from aiobale.methods import GetFileUploadUrl, SendMessage

dp = Dispatcher()
client = Client(dp)

async def upload_and_send(peer_id: int, file_path: str):
    # 1. request an upload URL
    upload_info = await client.call(GetFileUploadUrl())
    # 2. upload file to upload_info.upload_url (HTTP PUT/POST as docs specify)
    # 3. then send with SendMessage() attaching file metadata
```

**2) Group utilities — list members & kick user**

```python
from aiobale.methods import LoadMembers, KickUser

members = await client.call(LoadMembers(group_id=12345))
# Kick user
await client.call(KickUser(group_id=12345, user_id=67890))
```

(See the `Methods` reference in the docs for parameters & return types.) citeturn2view0

---

## API Reference (short)

Aiobale exposes `Methods`, `Types`, `Responses`, and `Filters`. Some of the important modules include:

- `aiobale.methods` — high-level method objects: `SendMessage`, `LoadHistory`, `GetFileUrl`, `StartPhoneAuth`, `ValidateCode`, `EditName`, etc. citeturn2view0
- `aiobale.types` — message models: `Message`, `MessageContent`, `DocumentMessage`, `FullUser`, `Group`, `FileInfo`, etc. citeturn2view0
- `aiobale.filters` — ready-made filters: `IsText`, `IsDocument`, `IsPrivate`, `RegexFilter`, logical combinators. citeturn2view0
- `aiobale.events` / `Dispatcher` — decorator-based handlers and router primitives. citeturn2view0

> For a full, machine-readable list of methods and types, consult the official docs. citeturn2view0

---

## Installation

```bash
# Stable release from PyPI
pip install aiobale

# Latest from GitHub
pip install git+https://github.com/Enalite/aiobale.git
```

---

## Development & Tests

```bash
# clone
git clone https://github.com/Enalite/aiobale.git
cd aiobale

# create venv (recommended)
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e .[dev]      # if project exposes dev extras
```

Run examples from `examples/` to quickly validate typical flows. citeturn1view1turn2view0

---

## Roadmap & Changelog (summary)

- v0.1.5 — Recent release with documentation and stability improvements. citeturn0view0
- Planned: improved error handling, more examples (webhooks, metrics), typed stubs, CI test coverage.

For full changelog see `Releases` on GitHub. citeturn0view0

---

## Security & Responsible Use

Aiobale speaks to an internal API — treat credentials and sessions carefully. Do **not** use this project to perform actions that violate Bale’s Terms of Service. Misuse can lead to account bans or legal consequences. The maintainers are not responsible for abusive usage. citeturn2view0

---

## Contributing & Code of Conduct

- Read `CONTRIBUTING.md` (if present), open issues, and submit PRs.
- Keep changes focused, add tests for bug fixes, and document new features.
- Be respectful — follow a friendly code of conduct in issue discussions and PRs.

---

## Maintainers & Support

Maintained by the Aiobale team — see the GitHub contributors list. For discussions, use the project channels (Bale, Telegram) and GitHub Issues. citeturn0view0turn2view0

---

## Attribution & Credits

Built by reverse-engineering Bale’s client and network traffic — credit to the project maintainers and contributors who documented the protocol. Documentation site generated with Sphinx + Furo. citeturn2view0

---

<p align="center">
  <strong>Enjoy building — and please use responsibly.</strong><br>
  <em>Aiobale — connecting Python people to Bale.</em>
</p>
