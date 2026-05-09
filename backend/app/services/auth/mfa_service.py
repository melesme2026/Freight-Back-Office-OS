from __future__ import annotations

import base64
import hashlib
import hmac
import os
import struct
import time
from urllib.parse import quote

from app.core.exceptions import ValidationError


class MfaService:
    """Small TOTP MFA foundation without introducing paid/external dependencies."""

    ISSUER = "Freight Back Office OS"
    SECRET_BYTES = 20
    TIME_STEP_SECONDS = 30
    CODE_DIGITS = 6
    WINDOW_STEPS = 1

    @classmethod
    def generate_totp_secret(cls) -> str:
        return base64.b32encode(os.urandom(cls.SECRET_BYTES)).decode("ascii").rstrip("=")

    @classmethod
    def provisioning_uri(cls, *, email: str, secret: str, issuer: str | None = None) -> str:
        normalized_issuer = issuer or cls.ISSUER
        label = f"{normalized_issuer}:{email.strip().lower()}"
        return (
            "otpauth://totp/"
            f"{quote(label)}?secret={quote(secret)}&issuer={quote(normalized_issuer)}"
            f"&algorithm=SHA1&digits={cls.CODE_DIGITS}&period={cls.TIME_STEP_SECONDS}"
        )

    @classmethod
    def _secret_bytes(cls, secret: str) -> bytes:
        normalized = secret.strip().replace(" ", "").upper()
        if not normalized:
            raise ValidationError("MFA secret is not configured")
        padding = "=" * ((8 - len(normalized) % 8) % 8)
        try:
            return base64.b32decode(normalized + padding, casefold=True)
        except Exception as exc:
            raise ValidationError("MFA secret is invalid") from exc

    @classmethod
    def _totp_at(cls, secret: str, counter: int) -> str:
        key = cls._secret_bytes(secret)
        msg = struct.pack(">Q", counter)
        digest = hmac.new(key, msg, hashlib.sha1).digest()
        offset = digest[-1] & 0x0F
        code_int = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
        return str(code_int % (10 ** cls.CODE_DIGITS)).zfill(cls.CODE_DIGITS)

    @classmethod
    def verify_totp(cls, *, secret: str | None, code: str | None, at_time: int | None = None) -> bool:
        if not secret or not code:
            return False
        normalized_code = str(code).strip().replace(" ", "")
        if not normalized_code.isdigit() or len(normalized_code) != cls.CODE_DIGITS:
            return False
        timestamp = int(at_time if at_time is not None else time.time())
        counter = timestamp // cls.TIME_STEP_SECONDS
        for offset in range(-cls.WINDOW_STEPS, cls.WINDOW_STEPS + 1):
            expected = cls._totp_at(secret, counter + offset)
            if hmac.compare_digest(expected, normalized_code):
                return True
        return False
