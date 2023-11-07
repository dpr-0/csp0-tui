import json
from dataclasses import dataclass
from typing import AsyncIterator, List, TypeAlias

import httpx
import websockets

from app import exceptions
from app.auth import JWTAuth
from app.base import Service

UserID: TypeAlias = str
ThreadID: TypeAlias = str
Secret: TypeAlias = str
TicketID: TypeAlias = str
NotificationID: TypeAlias = str


class UserService(Service):
    @classmethod
    async def create(cls) -> Secret:
        async with httpx.AsyncClient(base_url=cls.BASE_URL) as client:
            try:
                resp = await client.post("/users")
            except httpx.HTTPError as e:
                raise exceptions.NetworkError from e
        if resp.status_code != httpx.codes.CREATED:
            raise exceptions.ServiceError
        return resp.json()["secret"]

    @classmethod
    async def fetch_thread_ids(cls) -> List[ThreadID]:
        async with httpx.AsyncClient(base_url=cls.BASE_URL, auth=JWTAuth()) as client:
            try:
                resp = await client.get("/threads")
            except httpx.HTTPError as e:
                raise exceptions.NetworkError from e
        if resp.status_code != httpx.codes.OK:
            raise exceptions.APIError(resp.text)
        return resp.json()["ids"]

    @classmethod
    async def start_matching(cls) -> TicketID:
        async with httpx.AsyncClient(base_url=cls.BASE_URL, auth=JWTAuth()) as client:
            try:
                resp = await client.post("/match")
            except httpx.HTTPError as e:
                raise exceptions.NetworkError from e
        if resp.status_code == httpx.codes.TOO_MANY_REQUESTS:
            raise exceptions.APIError("already in matching")
        elif resp.status_code != httpx.codes.OK:
            raise exceptions.ServiceError
        return resp.json()["ticket_id"]


class NotificationService(Service):
    @classmethod
    async def get_last_read_offset(cls) -> float:
        async with httpx.AsyncClient(base_url=cls.BASE_URL, auth=JWTAuth()) as client:
            try:
                resp = await client.get("/users/me/notifications/read-offset")
            except httpx.HTTPError as e:
                raise exceptions.NetworkError from e
        if resp.status_code != httpx.codes.OK:
            raise exceptions.ServiceError
        else:
            return resp.json()["offset"]

    @classmethod
    async def update_last_read_offset(cls, timestamp: float):
        async with httpx.AsyncClient(base_url=cls.BASE_URL, auth=JWTAuth()) as client:
            try:
                resp = await client.patch(
                    "/users/me/notifications/read-offset",
                    json={"new_offset": int(timestamp * 1000)},
                )
            except httpx.HTTPError as e:
                raise exceptions.NetworkError from e
        if resp.status_code != httpx.codes.OK:
            raise exceptions.APIError(resp.text)

    @classmethod
    async def iterate(cls, timestamp: float) -> AsyncIterator[dict]:
        async with httpx.AsyncClient(base_url=cls.BASE_URL, auth=JWTAuth()) as client:
            try:
                async with client.stream(
                    "GET",
                    "/users/me/notifications",
                    params={"t": timestamp},
                    timeout=None,
                ) as resp:
                    async for i in resp.aiter_text():
                        yield json.loads(i)
            except httpx.HTTPError as e:
                raise exceptions.NetworkError from e


@dataclass
class ThreadMessage:
    id: str
    time: float
    user_id: str
    message: str


class ThreadService(Service):
    @classmethod
    async def leave(cls, thread_id: str):
        async with httpx.AsyncClient(base_url=cls.BASE_URL, auth=JWTAuth()) as client:
            try:
                resp = await client.post(f"/threads/{thread_id}/leave")
            except httpx.HTTPError as e:
                raise exceptions.NetworkError from e
        if resp.status_code != httpx.codes.OK:
            raise exceptions.APIError(resp.text)

    @classmethod
    async def fetch_old_messages(
        cls, thread_id: ThreadID, offset: float
    ) -> List[ThreadMessage]:
        async with httpx.AsyncClient(base_url=cls.BASE_URL, auth=JWTAuth()) as client:
            try:
                resp = await client.get(
                    f"/threads/{thread_id}", params={"t": int(offset * 1000)}
                )
            except httpx.HTTPError as e:
                raise exceptions.NetworkError from e
        if resp.status_code != httpx.codes.OK:
            raise exceptions.APIError(resp.text)
        return [
            ThreadMessage(
                id=data["id"],
                user_id=data["uid"],
                message=data["text"],
                time=data["time"],
            )
            for data in resp.json()["data"]
        ]

    @classmethod
    async def iterate_new(
        cls, offset: dict[ThreadID, float]
    ) -> AsyncIterator[ThreadMessage]:
        token = await JWTAuth().async_get_token()
        async with websockets.connect(
            uri=f"{cls.WS_BASE_URL}/messages/down",
            extra_headers={"Authorization": f"Bearer {token}"},
        ) as ws:
            try:
                await ws.send(json.dumps(offset))
                while frame := await ws.recv():
                    if frame == "PING":
                        await ws.send("PONG")
                    else:
                        data = json.loads(frame)
                        yield ThreadMessage(
                            id=data["id"],
                            user_id=data["uid"],
                            message=data["text"],
                            time=data["time"],
                        )
            except websockets.ConnectionClosed:
                print("listen fail")
                print(ws.close_code)

    @classmethod
    async def send_message(cls, thread_id: str, text: str):
        token = await JWTAuth().async_get_token()
        async with websockets.connect(
            uri=f"{cls.WS_BASE_URL}/messages/up",
            extra_headers={"Authorization": f"Bearer {token}"},
        ) as ws:
            try:
                print("sending")
                data = {"tid": thread_id, "text": text}
                await ws.send(json.dumps(data))
                await ws.close()
                await ws.wait_closed()
            except websockets.ConnectionClosed:
                print("send fail")
                print(ws.close_code)


class User:
    def __init__(self, id: UserID, secret: Secret) -> None:
        self.id = id
        self.secret = secret
        self.thread_id: ThreadID | None = None
