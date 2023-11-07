from __future__ import annotations

import asyncio
import time
from typing import List

from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Footer, Header, Input, Static

from app.user import NotificationService, ThreadMessage, ThreadService


class MessageRow(Horizontal):
    pass


class MessageStatic(Static):
    pass


class Thread(VerticalScroll):
    class NewThreadMessage(Message):
        def __init__(
            self, thread_msgs: List[ThreadMessage], auto_scroll: bool = True
        ) -> None:
            self.thread_msgs = thread_msgs
            self.auto_scroll = auto_scroll
            super().__init__()

    def on_thread_new_thread_message(self, message: Thread.NewThreadMessage):
        msg_rows = []
        if len(self.children) > 0:
            after = self.children[-1].id
        else:
            after = None

        for msg in message.thread_msgs:
            if self.screen.user_id == msg.user_id:  # type: ignore
                classes = "right_message_row"
            else:
                classes = None

            msg_rows.append(MessageRow(MessageStatic(msg.message), classes=classes))

        self.mount_all(msg_rows, after=after)
        if message.auto_scroll and not self.is_vertical_scrollbar_grabbed:
            self.scroll_end(animate=False)


class ChatScreen(Screen):
    class ThreadDeleted(Message):
        pass

    BINDINGS = [
        ("ctrl+l", "leave", "Leave Chat"),
    ]

    def __init__(
        self,
        user_id: str,
        thread_id: str,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        self.user_id = user_id
        self.thread_id = thread_id
        self.leaving_lock = asyncio.Lock()
        super().__init__(name, id, classes)

    def compose(self) -> ComposeResult:
        self.thread = Thread()
        self.thread_input = Input(id="chat_input", placeholder="Enter text here")
        yield Header(show_clock=True)
        yield Vertical(
            self.thread,
            self.thread_input,
            id="chat_middle",
        )
        yield Footer()

    async def on_mount(self):
        self.notification_worker = self.listen_notification()
        now = time.time()
        old_msgs = await ThreadService.fetch_old_messages(self.thread_id, now)
        old_msgs.sort(key=lambda x: x.time)
        self.thread.post_message(Thread.NewThreadMessage(old_msgs))
        self.message_worker = self.listen_message({self.thread_id: now})

    async def on_input_submitted(self, event: Input.Submitted):
        if not event.value:
            return
        text = event.value.strip()
        await ThreadService.send_message(self.thread_id, text)
        self.thread_input.clear()

    @work(exclusive=True, group="chat_screen_listen_notification")
    async def listen_notification(self):
        offset = await NotificationService.get_last_read_offset()
        sub_pattern = {
            "details": {"thread_id": self.thread_id},
        }

        async for n in NotificationService.iterate(offset):
            await NotificationService.update_last_read_offset(n["time"])
            match n:
                case sub_pattern if n["code"] == "thread_leaved":  # noqa: F841
                    self.post_message(self.ThreadDeleted())
                    return
                case sub_pattern if n["code"] == "thread_joined":  # noqa: F841
                    pass

    @work(exclusive=True, group="chat_screen_listen_message")
    async def listen_message(self, offset):
        async for msg in ThreadService.iterate_new(offset):
            self.thread.post_message(Thread.NewThreadMessage([msg]))

    async def action_leave(self):
        async with self.leaving_lock:
            try:
                await ThreadService.leave(self.thread_id)  # type: ignore
            except Exception as e:
                self.log.error(e)

    def on_chat_screen_thread_deleted(self, message: ChatScreen.ThreadDeleted):
        self.notification_worker.cancel()
        screen_class = self.app.screen_context.next()  # type: ignore
        self.app.switch_screen(screen_class(self.user_id))
