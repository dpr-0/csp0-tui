from __future__ import annotations

from textual import work
from textual.app import ComposeResult
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from app.ticket import TicketService
from app.user import UserService


class MatchScreen(Screen):
    class Matched(Message):
        def __init__(self, thread_id: str) -> None:
            self.thread_id = thread_id
            super().__init__()

    BINDINGS = [("enter", "start_match", "match")]

    def __init__(
        self,
        user_id: str,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        self.user_id = user_id
        super().__init__(name, id, classes)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(id="match_screen_welcome_text")
        yield Footer()

    async def on_mount(self):
        self.ticket_id = None
        _tickets = await TicketService.get_tickets()
        tickets = []
        for ticket in _tickets:
            if ticket.thread_id is not None:
                await TicketService.delete_ticket(ticket.id)
            else:
                tickets.append(ticket)

        assert len(tickets) < 2
        if len(tickets) == 1:
            ticket = tickets[0]
            self.ticket_id = ticket.id
            self.query_one(Static).update("Still Matching...")
            self.wait_matching_result(self.ticket_id)
        else:
            self.query_one(Static).update("Press ↩ to match")

    async def action_start_match(self):
        if self.ticket_id is not None:
            return
        try:
            self.ticket_id = await UserService.start_matching()
            self.query_one(Static).update("Matching...")
        except Exception as e:
            self.log.error(e)
        else:
            self.wait_matching_result(self.ticket_id)

    @work(exclusive=True, group="match_screen")
    async def wait_matching_result(self, ticket_id: str):
        while True:
            try:
                thread_id = await TicketService.wait_matching_result(ticket_id)
                await TicketService.delete_ticket(ticket_id)
            except Exception as e:
                self.log.warning(e)
                continue
            else:
                self.post_message(self.Matched(thread_id))
                break

    async def on_match_screen_matched(self, message: MatchScreen.Matched):
        screen_class = self.app.screen_context.next()  # type: ignore
        self.app.switch_screen(screen_class(self.user_id, message.thread_id))
