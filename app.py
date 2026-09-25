from textual.app import App, ComposeResult
from textual.widgets import Header, Footer
from textual.containers import Horizontal
from pathlib import Path

from ui.file_panel import FilePanel


class FileManagerApp(App):
    TITLE = "TUI File Manager"

    CSS = """
    Screen {
        background: $surface;
    }
    """

    BINDINGS = [
        ("q",         "quit",       "Quit"),
        ("up",        "",           "Up"),
        ("down",      "",           "Down"),
        ("enter",     "",           "Open / Read"),
        ("backspace", "",           "Go up"),
        ("d",         "",           "Delete"),
        ("r",         "",           "Rename"),
        ("n",         "",           "New file"),
        ("m",         "",           "New folder"),
        ("c",         "",           "Copy path"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield FilePanel(Path.cwd())
        yield Footer()


if __name__ == "__main__":
    app = FileManagerApp()
    app.run()
