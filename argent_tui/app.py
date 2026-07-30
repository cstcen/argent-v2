"""Argent TUI — 极简测试版，排查问题用。"""

import os, shutil, re, asyncio
from pathlib import Path
from textual.app import App, ComposeResult
from textual.widgets import Input, Static

ARGENT_HOME = Path(os.environ.get("ARGENT_HOME", Path.home() / ".argent"))

class ArgentApp(App):
    def compose(self):
        yield Static("Argent v2.0.0 - 输入消息按 Enter", id="header")
        yield Static("", id="output")
        yield Input(placeholder="输入消息...", id="inp")

    def on_mount(self):
        self.hermes_bin = shutil.which("hermes")
        self.log_output(f"Hermes: {'✓ ' + self.hermes_bin if self.hermes_bin else '✗ 未安装'}")

    def on_input_submitted(self, event: Input.Submitted):
        text = event.value.strip()
        if not text:
            return
        event.input.value = ""
        self.log_output(f"你: {text}")

        if not self.hermes_bin:
            self.log_output("⚠ hermes 未安装")
            return

        async def chat():
            env = os.environ.copy()
            env["HERMES_HOME"] = str(ARGENT_HOME)
            proc = await asyncio.create_subprocess_exec(
                self.hermes_bin, "chat", "-q", text,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=env,
            )
            stdout, _ = await proc.communicate()
            out = stdout.decode("utf-8", errors="replace").strip()
            clean = re.sub(r'\x1b\[[0-9;]*m', '', out)
            self.log_output(f"Argent: {clean[:500]}")

        asyncio.ensure_future(chat())

    def log_output(self, msg: str):
        widget = self.query_one("#output")
        current = widget.renderable if hasattr(widget, 'renderable') else ""
        widget.update(str(current) + "\n" + msg)


if __name__ == "__main__":
    ArgentApp().run()
