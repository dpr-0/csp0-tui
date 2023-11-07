from unittest import mock

import pytest

from app import exceptions
from app.app import RandomChatApp
from app.jwt import JWT
from app.widgets.chat import ChatScreen
from app.widgets.login import LoginDescription, LoginInput, LoginScreen
from app.widgets.match import MatchScreen


async def test_press_enter_while_empty_input():
    app = RandomChatApp()
    async with app.run_test() as pilot:
        await pilot.press("enter")
        assert isinstance(app.screen, LoginScreen)


@pytest.mark.parametrize(
    "thread_ids,tickets,screen", [([], [], MatchScreen), (["bob"], [], ChatScreen)]
)
@mock.patch("app.user.ThreadService.fetch_old_messages")
@mock.patch("app.cache.Cache.get")
@mock.patch("app.ticket.TicketService.get_tickets")
@mock.patch("app.user.UserService.fetch_thread_ids")
@mock.patch("app.jwt.JWTService.login")
async def test_loing_success(
    mock_login,
    mock_fetch_thread_ids,
    mock_get_tickets,
    mock_get,
    mock_fetch_old_messages,
    thread_ids,
    tickets,
    screen,
    alice_jwt: str,
):
    jwt = JWT(alice_jwt)
    mock_login.return_value = jwt
    mock_fetch_thread_ids.return_value = thread_ids
    mock_get_tickets.return_value = tickets
    mock_get.return_value = jwt
    mock_fetch_old_messages.return_value = []
    app = RandomChatApp()
    async with app.run_test() as pilot:
        await pilot.click("#login_input")
        await pilot.press("s", "enter")
        assert isinstance(app.screen, screen)


@mock.patch("app.jwt.JWTService.login")
async def test_login_fail(mock_login):
    mock_login.side_effect = exceptions.IncorrectPassword
    app = RandomChatApp()
    async with app.run_test() as pilot:
        await pilot.click("#login_input")
        await pilot.press("f", "enter")
        assert isinstance(app.screen, LoginScreen)
        assert (
            "incorrect password"
            in app.screen.query_one(LoginDescription).renderable.split("\n")[-1]  # type: ignore
        )


@mock.patch("app.user.UserService.create")
async def test_acreate_account(mock_create):
    mock_create.return_value = "secret"
    app = RandomChatApp()
    async with app.run_test() as pilot:
        await pilot.click(LoginDescription, offset=(42, 2))
        assert app.query_one(LoginInput).disabled
        assert app.query_one(LoginInput).value != ""
        assert "Account created" in str(app.query_one(LoginDescription).renderable)
        await pilot.click(LoginDescription, offset=(26, 2))
        assert "Copied" in str(app.query_one(LoginDescription).renderable)
        assert not app.query_one(LoginInput).disabled


@mock.patch("app.user.UserService.create")
async def test_acreate_account_fail(mock_create):
    mock_create.side_effect = exceptions.CreateFail
    app = RandomChatApp()
    async with app.run_test() as pilot:
        await pilot.click(LoginDescription, offset=(42, 2))
        assert not app.query_one(LoginInput).disabled
        assert app.query_one(LoginInput).value == ""
        assert "create fail" in str(app.query_one(LoginDescription).renderable)
