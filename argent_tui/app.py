"""Argent TUI — 基于 Textual 的问述科技聊天界面。

每轮对话通过 `hermes chat -q \"消息\"` 独立调用 Hermes。
"""

import os
import shutil
import re
import asyncio
from pathlib import Path
from textual.app import App, ComposeResult
from textual.widgets import Header, RichLog, Input
from textual.containers import Vertical
from textual.binding import Binding

ARGENT_HOME = Path(os.environ.get("ARGENT_HOME", Path.home() / ".argent"))


class ArgentApp(App):
    """Argent 主聊天界面。"""

    CSS = """
    #chat-log { border: none; background: #0D1B2A; }
    #user-input { border: solid #2A3A4A; background: #162030; color: #FFFFFF; margin: 1 2; height: 3; }
    #user-input:focus { border: solid #00C896; }
    Screen { background: #0D1B2A; }
    """

    BINDINGS = [
        Binding("ctrl+q", "quit", "退出"),
        Binding("ctrl+l", "clear", "清屏"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True, name="Argent")
        with Vertical(id="chat-container"):
            yield RichLog(id="chat-log", highlight=True, markup=True)
            yield Input(id="user-input", placeholder="输入消息，Enter 发送...")

    def on_mount(self):
        self._check_hermes()
        self.log("[#00C896]Argent v2.0.0[/] — 问述科技桌面 AI 助手")
        self.log("输入消息开始对话，Ctrl+Q 退出\n")
        self.query_one("#user-input").focus()

    def _check_hermes(self):
        self.hermes_bin = shutil.which("hermes")
        if not self.hermes_bin:
            self.log("[red]⚠ hermes 未安装[/]")
        else:
            self.log(f"[#00C896]✓[/] Hermes 就绪")

    async def _run_hermes(self, text: str) -> str:
        """在后台线程中运行 hermes，不阻塞 UI。"""
        env = os.environ.copy()
        env["HERMES_HOME"] = str(ARGENT_HOME)

        proc = await asyncio.create_subprocess_exec(
            self.hermes_bin, "chat", "-q", text,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        except asyncio.TimeoutError:
            proc.kill()
            return "[red]⚠ 超时（60秒）[/]"

        out = stdout.decode("utf-8", errors="replace").strip()
        err = stderr.decode("utf-8", errors="replace").strip()

        if out:
            clean = re.sub(r'\x1b\[[0-9;]*m', '', out)
            clean = re.sub(r'╭─.*?╮\n?', '', clean, flags=re.DOTALL)
            clean = re.sub(r'╰─.*?╯\n?', '', clean, flags=re.DOTALL)
            clean = re.sub(r'Session:.*', '', clean)
            clean = re.sub(r'Duration:.*', '', clean)
            clean = re.sub(r'Messages:.*', '', clean)
            clean = re.sub(r'Resume this session.*', '', clean)
            clean = re.sub(r'\n{3,}', '\n\n', clean)
            return clean.strip() or out[:500]
        elif err:
            return f"[red]⚠ {err[:300]}[/]"
        return f"[red]⚠ 无响应（返回码: {proc.returncode}）[/]"

    async def on_input_submitted(self, event: Input.Submitted):
        text = event.value.strip()
        if not text:
            return
        event.input.value = ""
        event.input.disabled = True

        self.log(f"\n[bold #00C896]你:[/] {text}")

        if not getattr(self, "hermes_bin", None):
            self.log("[red]⚠ hermes 未安装[/]")
            event.input.disabled = False
            return

        # 非阻塞 — 用 call_later 调度
        self.set_timer(0.05, lambda: self._chat_turn(text))

    def _chat_turn(self, text: str):
        """通过 asyncio 在后台运行对话。"""
        async def run():
            response = await self._run_hermes(text)
            self.log(f"\n[bold #7C3AED]Argent:[/]\n{response}\n")
            inp = self.query_one("#user-input")
            inp.disabled = False
            inp.focus()
        asyncio.create_task(run())

    def action_clear(self):
        self.query_one("#chat-log").clear()


def main():
    app = ArgentApp()
    app.run()


if __name__ == "__main__":
    main()
