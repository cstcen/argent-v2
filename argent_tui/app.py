"""Argent TUI — 基于 Textual 的问述科技聊天界面。"""

import os, shutil, re, asyncio
from pathlib import Path
from textual.app import App, ComposeResult
from textual.widgets import Input, Static

ARGENT_HOME = Path(os.environ.get("ARGENT_HOME", Path.home() / ".argent"))

def clean_response(raw: str) -> str:
    """过滤 Hermes 输出，只保留 AI 回复内容。"""
    # 去掉终端颜色码
    clean = re.sub(r'\x1b\[[0-9;]*m', '', raw)
    # 去掉 Query: / Initializing... 等前缀
    clean = re.sub(r'^Query:.*\n?', '', clean, flags=re.MULTILINE)
    clean = re.sub(r'^Initializing.*\n?', '', clean, flags=re.MULTILINE)
    clean = re.sub(r'^\s*⚠.*\n?', '', clean, flags=re.MULTILINE)
    # 去掉 Hermes 装饰框（╭╮╰╯框起来的内容）
    clean = re.sub(r'^[─╭╮╰╯].*\n?', '', clean, flags=re.MULTILINE)
    # 去掉 Session: / Duration: / Messages: / Resume 行
    clean = re.sub(r'^(Session|Duration|Messages|Resume).*\n?', '', clean, flags=re.MULTILINE)
    clean = re.sub(r'^hermes --resume.*\n?', '', clean, flags=re.MULTILINE)
    # 去掉 ⚕ Hermes 标题行
    clean = re.sub(r'^.*⚕ Hermes.*\n?', '', clean)
    # 压缩多个空行
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
        if self.hermes_bin:
            self.log("#00C896", "✓ Hermes 就绪")
        else:
            self.log("red", "⚠ hermes 未安装，请运行 argent install")

    def log(self, color: str, msg: str):
        chat = self.query_one("#chat-log")
        chat.update(chat.renderable + f"\n[{color}]{msg}[/]")

    def on_input_submitted(self, event: Input.Submitted):
        text = event.value.strip()
        if not text:
            return
        event.input.value = ""
        self.log("#00C896", f"你: {text}")

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
            self.log("#7C3AED", f"Argent:\n{clean}\n")

        asyncio.ensure_future(chat())


def main():
    ArgentApp().run()


if __name__ == "__main__":
    main()
