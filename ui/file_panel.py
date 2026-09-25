from textual.widget import Widget
from textual.widgets import Static
from textual.reactive import reactive
from textual import events
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from rich.text import Text
from rich.syntax import Syntax
from rich.panel import Panel
from pathlib import Path
import shutil


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TEXT_EXTENSIONS = {
    ".txt", ".md", ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css",
    ".scss", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".env",
    ".sh", ".bat", ".ps1", ".c", ".cpp", ".h", ".java", ".kt", ".rs",
    ".go", ".rb", ".php", ".xml", ".csv", ".log", ".gitignore", ".dockerfile",
    ".makefile", ".sql", ".r", ".swift", ".dart", ".lua", ".vim",
}

SYNTAX_MAP = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".jsx": "jsx", ".tsx": ".tsx", ".html": "html", ".css": "css",
    ".scss": "scss", ".json": "json", ".yaml": "yaml", ".yml": "yaml",
    ".toml": "toml", ".sh": "bash", ".bat": "bat", ".ps1": "powershell",
    ".c": "c", ".cpp": "cpp", ".h": "c", ".java": "java",
    ".kt": "kotlin", ".rs": "rust", ".go": "go", ".rb": "ruby",
    ".php": "php", ".xml": "xml", ".sql": "sql", ".swift": "swift",
    ".lua": "lua", ".r": "r",
}

MAX_FILE_SIZE = 1 * 1024 * 1024  # 1 MB


def is_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_EXTENSIONS


def read_file_content(path: Path) -> tuple[str, str | None]:
    """Return (content_string, lexer_name_or_None). Raises on error."""
    if path.stat().st_size > MAX_FILE_SIZE:
        return f"[File too large to preview — {path.stat().st_size // 1024} KB]", None
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"[Error reading file: {e}]", None
    lexer = SYNTAX_MAP.get(path.suffix.lower())
    return content, lexer


# ---------------------------------------------------------------------------
# File list widget
# ---------------------------------------------------------------------------

class FileList(Widget):
    """Left pane: directory listing."""

    selected_index: reactive[int] = reactive(0)

    def __init__(self, path: Path) -> None:
        super().__init__()
        self.current_path = path
        self.files: list[Path] = []
        self._input_mode: str | None = None   # "rename" | "new_file" | "new_dir"
        self._input_buffer: str = ""

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        self.can_focus = True
        self.load_files()

    def load_files(self) -> None:
        try:
            self.files = sorted(
                self.current_path.iterdir(),
                key=lambda x: (not x.is_dir(), x.name.lower()),
            )
        except PermissionError:
            self.files = []
        self.selected_index = 0
        self.refresh()

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render(self) -> Text:
        text = Text()
        text.append(f" 📁 {self.current_path}\n\n", style="bold cyan")

        if not self.files:
            text.append("  (empty directory)\n", style="dim")
        else:
            for i, f in enumerate(self.files):
                is_sel = i == self.selected_index
                style = "bold white on dark_blue" if is_sel else ""
                icon = "📂 " if f.is_dir() else "📄 "
                line = f"  {icon}{f.name}\n"
                text.append(line, style=style)

        # Input prompt
        if self._input_mode == "rename":
            text.append(f"\n Rename → {self._input_buffer}▌", style="bold yellow")
        elif self._input_mode == "new_file":
            text.append(f"\n New file → {self._input_buffer}▌", style="bold green")
        elif self._input_mode == "new_dir":
            text.append(f"\n New folder → {self._input_buffer}▌", style="bold magenta")

        return text

    # ------------------------------------------------------------------
    # Properties for other widgets
    # ------------------------------------------------------------------

    @property
    def selected_path(self) -> Path | None:
        if self.files and 0 <= self.selected_index < len(self.files):
            return self.files[self.selected_index]
        return None

    # ------------------------------------------------------------------
    # Key handling
    # ------------------------------------------------------------------

    def on_key(self, event: events.Key) -> None:
        if self._input_mode:
            self._handle_input_key(event)
            return
        self._handle_nav_key(event)

    def _handle_nav_key(self, event: events.Key) -> None:
        key = event.key

        if key == "up":
            if self.selected_index > 0:
                self.selected_index -= 1
            self._notify_selection()

        elif key == "down":
            if self.selected_index < len(self.files) - 1:
                self.selected_index += 1
            self._notify_selection()

        elif key == "enter":
            sel = self.selected_path
            if sel and sel.is_dir():
                self.current_path = sel
                self.load_files()
                self._notify_selection()
            elif sel and sel.is_file():
                self._notify_selection(open_file=True)

        elif key == "backspace":
            parent = self.current_path.parent
            if parent != self.current_path:
                self.current_path = parent
                self.load_files()
                self._notify_selection()

        elif key == "d":
            self._delete_selected()

        elif key == "r":
            if self.selected_path:
                self._start_input("rename")

        elif key == "n":
            self._start_input("new_file")

        elif key == "m":
            self._start_input("new_dir")

        elif key == "c":
            sel = self.selected_path
            if sel:
                try:
                    import pyperclip
                    pyperclip.copy(str(sel))
                    self.app.notify(f"Copied: {sel}", title="Clipboard")
                except ImportError:
                    self.app.notify("Install pyperclip for clipboard support", severity="warning")

    def _handle_input_key(self, event: events.Key) -> None:
        key = event.key
        if key == "escape":
            self._cancel_input()
        elif key == "enter":
            self._commit_input()
        elif key == "backspace":
            self._input_buffer = self._input_buffer[:-1]
            self.refresh()
        elif len(key) == 1:
            self._input_buffer += key
            self.refresh()

    # ------------------------------------------------------------------
    # Input mode helpers
    # ------------------------------------------------------------------

    def _start_input(self, mode: str) -> None:
        self._input_mode = mode
        self._input_buffer = ""
        self.refresh()

    def _cancel_input(self) -> None:
        self._input_mode = None
        self._input_buffer = ""
        self.refresh()

    def _commit_input(self) -> None:
        name = self._input_buffer.strip()
        mode = self._input_mode
        self._cancel_input()

        if not name:
            return

        if mode == "rename" and self.selected_path:
            dest = self.selected_path.parent / name
            try:
                self.selected_path.rename(dest)
                self.app.notify(f"Renamed → {name}", title="Rename")
            except Exception as e:
                self.app.notify(str(e), title="Error", severity="error")
            self.load_files()

        elif mode == "new_file":
            new_path = self.current_path / name
            try:
                new_path.touch()
                self.app.notify(f"Created file: {name}", title="New File")
            except Exception as e:
                self.app.notify(str(e), title="Error", severity="error")
            self.load_files()

        elif mode == "new_dir":
            new_path = self.current_path / name
            try:
                new_path.mkdir(parents=True, exist_ok=True)
                self.app.notify(f"Created folder: {name}", title="New Folder")
            except Exception as e:
                self.app.notify(str(e), title="Error", severity="error")
            self.load_files()

        self._notify_selection()

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def _delete_selected(self) -> None:
        sel = self.selected_path
        if not sel:
            return
        try:
            if sel.is_dir():
                shutil.rmtree(sel)
            else:
                sel.unlink()
            self.app.notify(f"Deleted: {sel.name}", title="Deleted", severity="warning")
        except Exception as e:
            self.app.notify(str(e), title="Error", severity="error")
        self.load_files()
        self._notify_selection()

    # ------------------------------------------------------------------
    # Notification helper — posts a message up to the app
    # ------------------------------------------------------------------

    def _notify_selection(self, open_file: bool = False) -> None:
        sel = self.selected_path
        self.post_message(SelectionChanged(sel, open_file=open_file))


# ---------------------------------------------------------------------------
# Custom message
# ---------------------------------------------------------------------------

from textual.message import Message


class SelectionChanged(Message):
    def __init__(self, path: Path | None, open_file: bool = False) -> None:
        super().__init__()
        self.path = path
        self.open_file = open_file


# ---------------------------------------------------------------------------
# File viewer widget
# ---------------------------------------------------------------------------

class FileViewer(Static):
    """Right pane: file content / metadata preview."""

    def __init__(self) -> None:
        super().__init__("")
        self._current_file: Path | None = None
        self._scroll_offset: int = 0
        self._lines: list[str] = []

    def show_path(self, path: Path | None, force_open: bool = False) -> None:
        """Update the viewer for the given path."""
        if path is None:
            self.update(_empty_panel())
            return

        if path.is_dir():
            self._show_dir_info(path)
        elif path.is_file():
            if force_open or is_text_file(path):
                self._show_file(path)
            else:
                self._show_binary_info(path)

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------

    def _show_dir_info(self, path: Path) -> None:
        try:
            children = list(path.iterdir())
            dirs = sum(1 for c in children if c.is_dir())
            files = sum(1 for c in children if c.is_file())
            body = Text()
            body.append(f"  Type:     ", style="dim")
            body.append("Directory\n", style="bold cyan")
            body.append(f"  Path:     ", style="dim")
            body.append(f"{path}\n", style="white")
            body.append(f"  Contents: ", style="dim")
            body.append(f"{dirs} folders, {files} files\n", style="white")
        except PermissionError:
            body = Text("  Permission denied", style="red")
        self.update(Panel(body, title=f"[bold]{path.name}[/bold]", border_style="cyan"))

    def _show_binary_info(self, path: Path) -> None:
        size = path.stat().st_size
        body = Text()
        body.append(f"  Type:      ", style="dim")
        body.append("Binary file\n", style="bold yellow")
        body.append(f"  Extension: ", style="dim")
        body.append(f"{path.suffix or '(none)'}\n", style="white")
        body.append(f"  Size:      ", style="dim")
        body.append(f"{size:,} bytes\n", style="white")
        body.append(f"\n  Press [bold]Enter[/bold] on a text file to view its contents.")
        self.update(Panel(body, title=f"[bold]{path.name}[/bold]", border_style="yellow"))

    def _show_file(self, path: Path) -> None:
        self._current_file = path
        self._scroll_offset = 0
        content, lexer = read_file_content(path)
        self._lines = content.splitlines()

        if lexer:
            renderable = Syntax(
                content,
                lexer,
                theme="monokai",
                line_numbers=True,
                word_wrap=False,
            )
        else:
            renderable = Text(content)

        size = path.stat().st_size
        title = f"[bold]{path.name}[/bold]  [dim]{size:,} bytes · {len(self._lines)} lines[/dim]"
        self.update(Panel(renderable, title=title, border_style="green"))


def _empty_panel():
    body = Text()
    body.append("\n  Select a file and press ", style="dim")
    body.append("Enter", style="bold green")
    body.append(" to read it.\n\n", style="dim")
    body.append("  Navigate with ", style="dim")
    body.append("↑ ↓", style="bold")
    body.append(",  open dirs with ", style="dim")
    body.append("Enter", style="bold")
    body.append(",  go up with ", style="dim")
    body.append("Backspace", style="bold")
    body.append(".\n", style="dim")
    return Panel(body, title="[dim]File Viewer[/dim]", border_style="dim")


# ---------------------------------------------------------------------------
# Combined panel (exported, used by app.py)
# ---------------------------------------------------------------------------

class FilePanel(Widget):
    """Horizontal split: FileList (left) + FileViewer (right)."""

    DEFAULT_CSS = """
    FilePanel {
        layout: horizontal;
        height: 1fr;
    }
    FileList {
        width: 40%;
        border-right: solid cyan;
        overflow-y: auto;
    }
    FileViewer {
        width: 60%;
        overflow-y: auto;
        padding: 0 1;
    }
    """

    def __init__(self, path: Path) -> None:
        super().__init__()
        self._path = path

    def compose(self) -> ComposeResult:
        self._list = FileList(self._path)
        self._viewer = FileViewer()
        yield self._list
        yield self._viewer

    def on_mount(self) -> None:
        self._viewer.show_path(None)
        self._list.focus()

    def on_selection_changed(self, message: SelectionChanged) -> None:
        self._viewer.show_path(message.path, force_open=message.open_file)
