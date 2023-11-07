from __future__ import annotations

from datetime import datetime, timezone
from typing import TypeAlias

import httpx
from jwt import decode

from app import exceptions
from app.base import Service
from app.cache import Cache

Token: TypeAlias = str
Secret: TypeAlias = str


class JWTService(Service):
    @classmethod
    async def login(cls, secret: Secret) -> JWT:
        async with httpx.AsyncClient(base_url=cls.BASE_URL) as client:
            try:
                resp = await client.post("/tokens", json={"secret": secret})
            except httpx.HTTPError as e:
                raise exceptions.NetworkError from e
        if resp.status_code == httpx.codes.BAD_REQUEST:
            raise exceptions.IncorrectPassword
        elif resp.status_code != httpx.codes.OK:
            print(resp.text)
            raise exceptions.ServiceError
        else:
            jwt = JWT(resp.json()["access_token"])
            Cache.set("jwt", jwt)
            Cache.set("secret", secret)
            return jwt


class JWT:
    def __init__(self, token: str) -> None:
        self.token: Token = token
        header = decode(self.token, options={"verify_signature": False})
        self.user_id = header["id"]
        self.exp = datetime.fromtimestamp(header["exp"], tz=timezone.utc)

    @property
    def expired(self) -> bool:
        return datetime.now(timezone.utc) > self.exp
