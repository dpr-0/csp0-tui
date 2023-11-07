from app.app import RandomChatApp
from app.widgets.login import LoginScreen


async def test_app_first_start():
    app = RandomChatApp()
    async with app.run_test():
        assert isinstance(app.screen, LoginScreen)
