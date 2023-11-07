from dataclasses import dataclass
from typing import List, TypeAlias

import httpx

from app import exceptions
from app.auth import JWTAuth
from app.base import Service

ThreadID: TypeAlias = str


@dataclass
class Ticket:
    id: str
    thread_id: str | None


class TicketService(Service):
    @classmethod
    async def get_tickets(cls) -> List[Ticket]:
        async with httpx.AsyncClient(base_url=cls.BASE_URL, auth=JWTAuth()) as client:
            try:
                resp = await client.get("/tickets")
            except httpx.HTTPError as e:
                raise exceptions.NetworkError from e
        if resp.status_code != httpx.codes.OK:
            raise exceptions.APIError(str(resp.status_code))
        return [Ticket(id=i["id"], thread_id=i["thread_id"]) for i in resp.json()]

    @classmethod
    async def delete_ticket(cls, ticket_id: str):
        async with httpx.AsyncClient(base_url=cls.BASE_URL, auth=JWTAuth()) as client:
            try:
                resp = await client.delete(f"/tickets/{ticket_id}")
            except httpx.HTTPError as e:
                raise exceptions.NetworkError from e
        if resp.status_code != httpx.codes.NO_CONTENT:
            raise exceptions.APIError(str(resp.status_code))

    @classmethod
    async def wait_matching_result(cls, ticket_id: str) -> ThreadID:
        thread_id = None
        async with httpx.AsyncClient(base_url=cls.BASE_URL, auth=JWTAuth()) as client:
            try:
                async with client.stream(
                    "GET", f"/match/tickets/{ticket_id}", timeout=None
                ) as resp:
                    async for thread_id in resp.aiter_lines():
                        thread_id = thread_id
            except httpx.HTTPError as e:
                raise exceptions.NetworkError from e
        if resp.status_code == httpx.codes.FORBIDDEN:
            raise exceptions.APIError("wrong ticket")
        elif resp.status_code == 524:
            raise TimeoutError(str(resp.text))
        elif resp.status_code != httpx.codes.OK:
            raise exceptions.APIError(str(resp.text))
        elif thread_id is None:
            raise Exception(f"got stream resp but thread is {thread_id}")
        else:
            return thread_id
