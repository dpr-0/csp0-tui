from textual.app import App

from app.screen_state import ScreenContext


class RandomChatApp(App):
    TITLE = "Chat Side Project Type-0"
    CSS_PATH = "app.tcss"

    def on_mount(self):
        self.screen.visible = False
        self.screen.disabled = True
        self.screen_context = ScreenContext()
        self.push_screen(self.screen_context.next()())


if __name__ == "__main__":
    RandomChatApp().run()
