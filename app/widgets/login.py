from datetime import datetime

import pyperclip  # type: ignore
from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Footer, Header, Input, Static

from app import exceptions
from app.jwt import JWTService
from app.user import User, UserService


class LoginDescription(Static):
    def on_mount(self):
        self.secret_input = self.app.screen.query_one(LoginInput)
        self.prefix_desc = "Press ↩ to login\n\nDon't have an account yet? Click [@click=create_account()]here[/]"
        self.renderable = self.prefix_desc
        self.logs = []

    @property
    def description(self) -> str:
        desc = self.prefix_desc
        if self.logs:
            desc += "\n\n" + "\n".join(self.logs[::-1])
        return desc

    async def action_create_account(self):
        try:
            secret = await UserService.create()
            self.prefix_desc = (
                "Account created\n\nClick [@click=copy_input()]here[/] copy"
            )
            self.logs.clear()
            self.update(self.description)
            self.secret_input.display_secret(secret)
        except exceptions.APIError as e:
            self.append_log(e.msg)

    def action_copy_input(self):
        pyperclip.copy(self.secret_input.value)
        self.prefix_desc = "Copied!\n\nPress ↩ to login"
        self.update(self.description)
        self.secret_input.release()

    def remove_oldest_log(self):
        if self.logs:
            self.logs.pop(0)
            self.update(self.description)

    def append_log(self, msg: str):
        current_time = datetime.now().time().isoformat(timespec="seconds")
        self.logs.append(f"[{current_time}] {msg}")
        self.update(self.description)
        self.set_timer(3.5, self.remove_oldest_log)


class LoginInput(Input):
    BINDINGS = [("escape", "clear", "Clear Input")]

    def display_secret(self, secret: str):
        self.password = False
        self.value = secret
        self.disabled = True

    def release(self):
        self.password = False
        self.disabled = False
        self.action_end()
        self.focus()

    def action_clear(self):
        self.clear()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if not event.value:
            return
        secret = event.value.strip()
        try:
            jwt = await JWTService.login(secret)
            user = User(jwt.user_id, secret)
            thread_ids = await UserService.fetch_thread_ids()
            if len(thread_ids) == 1:
                user.thread_id = thread_ids[0]
        except exceptions.APIError as e:
            self.app.screen.query_one(LoginDescription).append_log(e.msg)
        else:
            screen_class = self.app.screen_context.next()  # type: ignore
            if user.thread_id is not None:
                screen_class = self.app.screen_context.next()  # type: ignore
                self.app.switch_screen(
                    screen_class(user.id, user.thread_id)
                )  # go to chat screen
            else:
                self.app.switch_screen(screen_class(user.id))  # go to match screen


class LoginScreen(Screen[str]):
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Footer()
        yield Container(
            Static("Welcome", classes="login_description"),
            LoginInput(placeholder="Enter code here", password=True, id="login_input"),
            LoginDescription(classes="login_description"),
            id="login_dialog",
        )
