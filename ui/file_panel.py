from textual.widget import Widget
from textual.reactive import reactive
from textual import events
from rich.text import Text
from pathlib import Path


class FilePanel(Widget):

    current_path = reactive(Path.cwd())
    selected_index = reactive(0)

    def __init__(self, path: Path):
        super().__init__()
        self.current_path = path
        self.files = []

    def on_mount(self):
        self.load_files()

    def load_files(self):
        try:
            self.files = list(self.current_path.iterdir())
            self.files.sort(key=lambda x: (not x.is_dir(), x.name.lower()))
        except PermissionError:
            self.files = []

        self.selected_index = 0
        self.refresh()

    def render(self):
        text = Text()
        text.append(f"📁 {self.current_path}\n\n", style="bold cyan")

        for i, file in enumerate(self.files):
            style = "reverse" if i == self.selected_index else ""
            icon = "📂" if file.is_dir() else "📄"
            text.append(f"{icon} {file.name}\n", style=style)

        return text

    async def key_down(self, event: events.Key):
        if event.key == "up":
            if self.selected_index > 0:
                self.selected_index -= 1
                self.refresh()

        elif event.key == "down":
            if self.selected_index < len(self.files) - 1:
                self.selected_index += 1
                self.refresh()

        elif event.key == "enter":
            selected = self.files[self.selected_index]
            if selected.is_dir():
                self.current_path = selected
                self.load_files()

        elif event.key == "backspace":
            self.current_path = self.current_path.parent
            self.load_files()
