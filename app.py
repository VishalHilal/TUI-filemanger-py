from textual.app import App, ComposeResult
from textual.widgets import Header, Footer
from textual.containers import Horizontal
from pathlib import Path

from ui.file_panel import FilePanel


class FileManagerApp(App):
    TITLE = "TUI File Manager"

    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Horizontal(FilePanel(Path.cwd()))
        yield Footer()


if __name__ == "__main__":
    app = FileManagerApp()
    app.run()

