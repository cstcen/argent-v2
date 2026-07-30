"""Argent TUI — 线程版（subprocess.run 在后台线程）。"""
import os, shutil, asyncio, subprocess, re, threading
from pathlib import Path
from textual.app import App, ComposeResult
from textual.widgets import Input, Static

ARGENT_HOME = Path(os.environ.get("ARGENT_HOME", Path.home() / ".argent"))

def clean_response(raw: str) -> str:
    clean = re.sub(r'\x1b\[[0-9;]*m', '', raw)
    m = re.search(r'╮\s*\n\s*(.*?)\s*\n\s*╰', clean, re.DOTALL)
    if m: clean = m.group(1).strip()
    clean = re.sub(r'(Query|Initializing|Session|Duration|Messages|Resume|hermes):.*\n?', '', clean, flags=re.MULTILINE)
    return clean.strip()

class ArgentApp(App):
    CSS = "Screen { background: #0D1B2A; } #log { padding: 1 2; color: #DDE4EC; height: 1fr; } #inp { dock: bottom; margin: 1 2; height: 3; }"

    def compose(self) -> ComposeResult:
        yield Static("Argent v2 — 键入消息", id="log")
        yield Input(placeholder="输入消息，Enter 发送...", id="inp")

    def on_mount(self):
        self.hermes_bin = shutil.which("hermes")
        self._append(f"Hermes: {self.hermes_bin or 'NOT FOUND'}")
        self.query_one("#inp").focus()

    def _append(self, msg: str):
        w = self.query_one("#log")
        text = getattr(self, "_text", "") + "\n" + msg
        self._text = text
        w.update(text[-2000:])

    def on_input_submitted(self, event: Input.Submitted):
        text = event.value.strip()
        if not text: return
        event.input.value = ""
        self._append(f"你: {text}")
        if not self.hermes_bin: return

        # 在独立线程中运行，不阻塞 UI
        threading.Thread(target=self._run_hermes, args=(text,), daemon=True).start()

    def _run_hermes(self, text: str):
        env = os.environ.copy()
        env["HERMES_HOME"] = str(ARGENT_HOME)
        env_file = ARGENT_HOME / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.strip() and "=" in line and not line.startswith("#"):
                    k, _, v = line.partition("=")
                    env[k.strip()] = v.strip()
        try:
            r = subprocess.run(
                [self.hermes_bin, "chat", "-q", text],
                capture_output=True, text=True, env=env, timeout=60,
            )
            out = (r.stdout + r.stderr).strip()
            clean = clean_response(out) or out[:300]
        except subprocess.TimeoutExpired:
            clean = "⚠ 超时"
        except Exception as e:
            clean = f"⚠ {e}"

        def update():
            self._append(f"Argent:\n{clean}")
        self.call_from_thread(update)

def main():
    ArgentApp().run()
