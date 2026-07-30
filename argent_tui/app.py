"""Argent TUI — 基于 Textual 的问述科技聊天界面。"""

import os, shutil, re, asyncio
from pathlib import Path
from textual.app import App, ComposeResult
from textual.widgets import Input, Static

ARGENT_HOME = Path(os.environ.get("ARGENT_HOME", Path.home() / ".argent"))

def clean_response(raw: str) -> str:
    """过滤 Hermes 输出，只保留 AI 回复内容。"""
    clean = re.sub(r'\x1b\[[0-9;]*m', '', raw)
    clean = re.sub(r'^Query:.*\n?', '', clean, flags=re.MULTILINE)
    clean = re.sub(r'^Initializing.*\n?', '', clean, flags=re.MULTILINE)
    clean = re.sub(r'^\s*⚠.*\n?', '', clean, flags=re.MULTILINE)
    clean = re.sub(r'^[─╭╮╰╯].*\n?', '', clean, flags=re.MULTILINE)
    clean = re.sub(r'^(Session|Duration|Messages|Resume).*\n?', '', clean, flags=re.MULTILINE)
    clean = re.sub(r'^hermes --resume.*\n?', '', clean, flags=re.MULTILINE)
    clean = re.sub(r'^.*⚕ Hermes.*\n?', '', clean)
    clean = re.sub(r'\n{3,}', '\n\n', clean)
    return clean.strip()


class ArgentApp(App):
    CSS = """
    Screen { background: #0D1B2A; }
    #chat-log { height: 1fr; padding: 1 2; color: #DDE4EC; overflow-y: auto; }
    #user-input { dock: bottom; margin: 1 2; height: 3; border: solid #2A3A4A; background: #162030; color: #FFFFFF; }
    #user-input:focus { border: solid #00C896; }
    """

    def compose(self) -> ComposeResult:
        yield Static("Argent v2.0.0 — 问述科技 AI 助手\n", id="chat-log")
        yield Input(placeholder="输入消息，Enter 发送...", id="user-input")

    def on_mount(self):
        self.hermes_bin = shutil.which("hermes")
        msg = "✓ Hermes 就绪" if self.hermes_bin else "⚠ hermes 未安装"
        self._append(msg)

    def _append(self, msg: str):
        chat = self.query_one("#chat-log")
        chat.update(chat.renderable + "\n" + msg)

    def on_input_submitted(self, event: Input.Submitted):
        text = event.value.strip()
        if not text:
            return
        event.input.value = ""
        self._append(f"[bold #00C896]你:[/] {text}")

        if not self.hermes_bin:
            return

        async def chat():
            env = os.environ.copy()
            env["HERMES_HOME"] = str(ARGENT_HOME)
            proc = await asyncio.create_subprocess_exec(
                self.hermes_bin, "chat", "-q", text,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=env,
            )
            stdout, _ = await proc.communicate()
            out = stdout.decode("utf-8", errors="replace")
            clean = clean_response(out)
            self._append(f"\n[bold #7C3AED]Argent:[/]\n{clean}\n")

        asyncio.ensure_future(chat())


def main():
    ArgentApp().run()
