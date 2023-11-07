import asyncio
from typing import AsyncGenerator, Generator

from httpx import Auth, Request, Response

from app.cache import Cache
from app.jwt import JWT, JWTService


class JWTAuth(Auth):
    def __init__(self) -> None:
        self._lock = asyncio.Lock()

    def sync_auth_flow(self, request: Request) -> Generator[Request, Response, None]:
        raise RuntimeError("Cannot use a async authentication class with httpx.Client")

    async def async_login(self, secret: str):
        jwt = await JWTService.login(secret)
        Cache.set("jwt", jwt)
        return jwt

    async def async_get_token(self) -> str:
        async with self._lock:
            secret = Cache.get("secret")
            assert secret
            jwt: JWT = Cache.get("jwt")  # type: ignore
            if jwt is not None:
                if jwt.expired:
                    jwt = await self.async_login(secret)
            else:
                jwt = await self.async_login(secret)
        return jwt.token

    async def async_auth_flow(
        self, request: Request
    ) -> AsyncGenerator[Request, Response]:
        token = await self.async_get_token()
        request.headers["Authorization"] = f"Bearer {token}"
        yield request
