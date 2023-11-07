from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Type

from textual.screen import Screen

from app.widgets.chat import ChatScreen
from app.widgets.login import LoginScreen
from app.widgets.match import MatchScreen


class ScreenState(ABC):
    @abstractmethod
    def next(self, context: ScreenContext):
        raise NotImplementedError


class StartState(ScreenState):
    def next(self, context: ScreenContext) -> Type[Screen]:
        context.set_state(LoginState())
        return LoginScreen


class LoginState(ScreenState):
    def next(self, context: ScreenContext) -> Type[Screen]:
        context.set_state(MatchingState())
        return MatchScreen


class MatchingState(ScreenState):
    def next(self, context: ScreenContext) -> Type[Screen]:
        context.set_state(ChatState())
        return ChatScreen


class ChatState(ScreenState):
    def next(self, context: ScreenContext) -> Type[Screen]:
        context.set_state(MatchingState())
        return MatchScreen


class ScreenContext:
    def __init__(self) -> None:
        self._current_state: ScreenState = StartState()

    def set_state(self, state: ScreenState):
        self._current_state = state

    def next(self) -> Type[Screen]:
        return self._current_state.next(self)
