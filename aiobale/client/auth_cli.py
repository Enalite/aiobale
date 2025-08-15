from __future__ import annotations

import asyncio
import time
from colorama import Fore, init
from typing import TYPE_CHECKING, Optional

from ..exceptions import AiobaleError
from ..enums import SendCodeType, AuthErrors
from ..types.responses import PhoneAuthResponse

if TYPE_CHECKING:
    from .client import Client

init(autoreset=True)


class PhoneLoginCLI:
    """
    CLI for phone-based login using aiobale.
    Default UI language is English.
    If the user types 'fin', all subsequent messages are shown using the provided
    Fingilish (fa) strings. If the user types 'en', UI returns to English strings.
    """

    def __init__(self, client: Client):
        self.client = client
        self.fingilish_mode = False  # off by default

    # ---------------------------
    # Output & input helpers
    # ---------------------------
    def _print(self, en: str, fa: str, color=Fore.WHITE):
        msg = fa if self.fingilish_mode else en
        print(color + msg)

    def _input(self, en_prompt: str, fa_prompt: str, color=Fore.WHITE) -> str:
        prompt = fa_prompt if self.fingilish_mode else en_prompt
        return input(color + prompt)

    # ---------------------------
    # Flow
    # ---------------------------
    async def start(self):
        while True:
            phone_number = await self._request_phone_number()
            resp = await self._send_login_request(phone_number)
            if not resp:
                continue
            success = await self._handle_code_entry(resp, phone_number)
            if success:
                break

    async def _request_phone_number(self):
        # Explain both in EN (default) and FA (for fin mode)
        self._print(
            "📱 Enter your phone number in international format:\n"
            "   Example for Iran: 98XXXXXXXXXX (without the + sign)\n"
            "   Type 'fin' anytime to switch to Fingilish\n",
            "📱 shomare telefon ro be format beynolmelali vared kon:\n"
            "   mesal baraye Iran: 98XXXXXXXXXX (bedone +)\n"
            "   agar mikhay zaban en beshe bezan: en\n",
            Fore.CYAN,
        )
        while True:
            raw = self._input("Phone number: ", "Shomare: ", Fore.YELLOW)
            raw = raw.replace("+", "").strip()

            low = raw.lower()
            if low == "fin":
                self.fingilish_mode = True
                self._print("✅ Fingilish mode ON.\n", "✅ halat Fingilish fa'al shod.\n", Fore.GREEN)
                continue
            if low == "en":
                self.fingilish_mode = False
                self._print("✅ English mode ON.\n", "✅ halat English fa'al shod.\n", Fore.GREEN)
                continue

            if raw.isdigit():
                return int(raw)

            self._print(
                "❌ Invalid phone number format. Please check and try again.\n",
                "❌ format shomare dorost nist. check kon va dobare emtehan kon.\n",
                Fore.MAGENTA,
            )

    async def _send_login_request(
        self,
        phone_number: int,
        code_type: Optional[SendCodeType] = SendCodeType.DEFAULT,
    ) -> Optional[PhoneAuthResponse]:
        try:
            resp = await self.client.start_phone_auth(phone_number, code_type=code_type)
        except AiobaleError as e:
            # handle library-specific errors gracefully
            self._print(
                f"⚠️ Aiobale error while starting phone auth: {e}\n",
                f"⚠️ khata dar zaman ersal darkhast auth: {e}\n",
                Fore.RED,
            )
            return None

        if isinstance(resp, AuthErrors):
            if resp == AuthErrors.NUMBER_BANNED:
                self._print(
                    "🚫 This phone number is banned. Please try another number.\n",
                    "🚫 in shomare ban shode. shomare digari emtehan kon.\n",
                    Fore.RED,
                )
            elif resp == AuthErrors.RATE_LIMIT:
                self._print(
                    "🚫 Too many attempts! Please wait a while before trying again.\n",
                    "🚫 talash ziad shod! kami sabr kon va dobare emtehan kon.\n",
                    Fore.RED,
                )
            elif resp == AuthErrors.INVALID:
                self._print(
                    "❌ Invalid phone number format. Please check and try again.\n",
                    "❌ format shomare namotabar. check kon va tekrar kon.\n",
                    Fore.MAGENTA,
                )
            else:
                self._print(
                    "ℹ️ An unknown authentication error occurred.\n",
                    "ℹ️ khataye gheire moshakhas dar ehraze hoviat pish amad.\n",
                    Fore.CYAN,
                )
            return None
        return resp

    async def _handle_code_entry(self, resp: PhoneAuthResponse, phone_number: int):
        max_attempts = 3
        attempts = 0
        expiration_timestamp = resp.code_expiration_date.value / 1000
        last_sent_time = time.time()
        next_code_type = resp.next_send_code_type

        self._print("✅ Code sent!", "✅ code ersal shod!", Fore.GREEN)
        self._print(
            "🔑 Enter your code. Available commands:\n"
            "   'resend'  - request a new code\n"
            "   'restart' - enter your phone number again\n"
            "   'fin'     - enable Fingilish mode\n"
            "   'en'      - switch back to English\n",
            "🔑 code ra vared kon. dasturat:\n"
            "   'resend' - ersal dobare\n"
            "   'restart' - vorood-e dobare shomare\n"
            "   'fin' - raftan be zaban fingilishi\n"
            "   'en' - raftan be zaban en\n",
            Fore.CYAN,
        )

        while True:
            if time.time() > expiration_timestamp:
                self._print(
                    "⌛ Code expired. Restarting phone entry...\n",
                    "⌛ zaman code tamoom shod. bargasht be marhale shomare...\n",
                    Fore.RED,
                )
                return False

            try:
                remaining_time = expiration_timestamp - time.time()
                cooldown = resp.code_timeout.value
                elapsed = time.time() - last_sent_time

                self._print(
                    f"⏳ Time left before expiration: {int(remaining_time)} sec",
                    f"⏳ zaman baghi mande ta enghaza: {int(remaining_time)} sanie",
                    Fore.YELLOW,
                )
                self._print(
                    f"⌛ New code timeout: {int(cooldown - elapsed)} sec\n",
                    f"⌛ ta ersale dobare: {int(cooldown - elapsed)} sanie\n",
                    Fore.YELLOW,
                )

                try:
                    code = await asyncio.wait_for(
                        asyncio.to_thread(
                            self._input, "Enter code: ", "code ra vared kon: ", Fore.BLUE
                        ),
                        timeout=remaining_time,
                    )
                except asyncio.TimeoutError:
                    self._print(
                        "⏰ Code entry timed out. Please try again.\n",
                        "⏰ mohlat vared kardan code tamoom shod. mojadadan talash konid.\n",
                        Fore.RED,
                    )
                    return False

                code = code.strip().lower()

                # language toggles first
                if code == "fin":
                    self.fingilish_mode = True
                    self._print("✅ Fingilish mode ON.", "✅ halat Fingilish fa'al shod.", Fore.GREEN)
                    continue
                if code == "en":
                    self.fingilish_mode = False
                    self._print("✅ English mode ON.", "✅ halat English fa'al shod.", Fore.GREEN)
                    continue

                if code == "restart":
                    self._print(
                        "🔄 Restarting phone entry...\n",
                        "🔄 bargasht be marhale vared kardane shomare...\n",
                        Fore.MAGENTA,
                    )
                    return False

                if code == "resend":
                    if elapsed < cooldown:
                        wait_seconds = int(cooldown - elapsed)
                        self._print(
                            f"⚠️ Wait {wait_seconds} sec before requesting a new code.\n",
                            f"⚠️ {wait_seconds} sanie sabr kon bad dobare darkhast kon.\n",
                            Fore.RED,
                        )
                        continue

                    if next_code_type is None:
                        self._print(
                            "⚠️ Resend is not available.\n",
                            "⚠️ emkane ersale dobare vojod nadarad.\n",
                            Fore.RED,
                        )
                        continue

                    resp = await self._send_login_request(
                        phone_number, code_type=next_code_type
                    )
                    if not resp:
                        return False

                    last_sent_time = time.time()
                    expiration_timestamp = resp.code_expiration_date.value / 1000
                    self._print("✅ Code resent!\n", "✅ code dobare ersal shod!\n", Fore.GREEN)
                    continue

                # Validate the code (with AiobaleError handling)
                try:
                    res = await self.client.validate_code(code, resp.transaction_hash)
                except AiobaleError as e:
                    self._print(
                        f"⚠️ Aiobale error while validating code: {e}\n",
                        f"⚠️ khata dar zamineh-e validate kardan code: {e}\n",
                        Fore.RED,
                    )
                    return False

                if isinstance(res, AuthErrors):
                    if res == AuthErrors.WRONG_CODE:
                        self._print(
                            "❌ Incorrect code. Please try again.\n",
                            "❌ code eshtebah ast. tekrar kon.\n",
                            Fore.RED,
                        )
                        attempts += 1
                        if attempts >= max_attempts:
                            self._print(
                                "❌ Too many failed attempts. Restarting phone entry...\n",
                                "❌ tedade talash ghalat ziad shod. bargasht be shomare...\n",
                                Fore.RED,
                            )
                            return False
                    elif res == AuthErrors.PASSWORD_NEEDED:
                        return await self._handle_password_entry(resp.transaction_hash)
                    elif res == AuthErrors.SIGN_UP_NEEDED:
                        self._print(
                            "❌ First sign up using official Bale client.\n",
                            "❌ aval dakhel khod bale sabt nam konid.\n",
                            Fore.RED,
                        )
                        return False
                    else:
                        self._print(
                            "ℹ️ An unknown authentication error occurred.\n",
                            "ℹ️ khataye gheire moshakhas dar ehraz hoviat.\n",
                            Fore.CYAN,
                        )
                        return False

                await self._on_login_success(res)
                return True

            except Exception as e:
                self._print(
                    f"⚠️ Unexpected error: {e}\n",
                    f"⚠️ khataye gheire montazer: {e}\n",
                    Fore.RED,
                )
                return False

    async def _handle_password_entry(self, transaction_hash: str):
        max_attempts = 3
        attempts = 0
        self._print(
            "🔐 This account requires a password.\n",
            "🔐 in hesab be password niaz darad.\n",
            Fore.MAGENTA,
        )

        while attempts < max_attempts:
            try:
                password = await asyncio.wait_for(
                    asyncio.to_thread(
                        self._input, "Enter password: ", "ramz ra vared kon: ", Fore.BLUE
                    ),
                    timeout=60,
                )
            except asyncio.TimeoutError:
                self._print(
                    "⏰ Password entry timed out. Restarting...\n",
                    "⏰ zaman vared kardan ramz tamam shod. bargasht...\n",
                    Fore.RED,
                )
                return False

            # Validate password with AiobaleError handling
            try:
                res = await self.client.validate_password(password.strip(), transaction_hash)
            except AiobaleError as e:
                self._print(
                    f"⚠️ Aiobale error while validating password: {e}\n",
                    f"⚠️ khata dar zamineh-e validate kardan ramz: {e}\n",
                    Fore.RED,
                )
                return False

            if isinstance(res, AuthErrors):
                if res == AuthErrors.WRONG_PASSWORD:
                    self._print(
                        "❌ Incorrect password. Try again.\n",
                        "❌ ramz eshtebah. tekrar kon.\n",
                        Fore.RED,
                    )
                    attempts += 1
                    continue
                else:
                    self._print(
                        "ℹ️ An unknown authentication error occurred.\n",
                        "ℹ️ khata-ye na moshakas dar ehraz hoviat.\n",
                        Fore.CYAN,
                    )
                    return False

            await self._on_login_success(res)
            return True

        self._print(
            "❌ Too many failed password attempts. Restarting...\n",
            "❌ tedade talash barai vorood ramz ziad shod. bargasht...\n",
            Fore.RED,
        )
        return False

    async def _on_login_success(self, res):
        self._print(
            f"🎉 Login successful! Welcome {res.user.name}",
            f"🎉 vorood movafagh! khosh amadid {res.user.name}",
            Fore.GREEN,
        )
