"""Argent TUI — Textual 聊天界面，每轮对话调用 hermes chat -q。"""

import os, shutil, re, asyncio
from pathlib import Path
from textual.app import App, ComposeResult
from textual.widgets import Header, RichLog, Input
from textual.containers import Vertical
from textual.binding import Binding

ARGENT_HOME = Path(os.environ.get("ARGENT_HOME", Path.home() / ".argent"))


class ArgentApp(App):
    CSS = """
    #chat-log { border: none; background: #0D1B2A; }
    #user-input { border: solid #2A3A4A; background: #162030; color: #FFFFFF; margin: 1 2; height: 3; }
    #user-input:focus { border: solid #00C896; }
    Screen { background: #0D1B2A; }
    """
    BINDINGS = [Binding("ctrl+q", "quit", "退出"), Binding("ctrl+l", "clear", "清屏")]

    def compose(self):
        yield Header(show_clock=True, name="Argent")
        with Vertical(id="chat-container"):
            yield RichLog(id="chat-log", highlight=True, markup=True)
            yield Input(id="user-input", placeholder="输入消息，Enter 发送...")

    def on_mount(self):
        self.hermes_bin = shutil.which("hermes")
        self.log("[#00C896]Argent v2.0.0[/] — 问述科技桌面 AI 助手")
        if self.hermes_bin:
            self.log(f"[#00C896]✓[/] Hermes 就绪\n")
        else:
            self.log("[red]⚠ hermes 未安装[/]\n")
        self.query_one("#user-input").focus()

    async def _call_hermes(self, text: str) -> str:
        env = os.environ.copy()
        env["HERMES_HOME"] = str(ARGENT_HOME)
        proc = await asyncio.create_subprocess_exec(
            self.hermes_bin, "chat", "-q", text,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=env,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        except asyncio.TimeoutError:
            proc.kill()
            return "[red]⚠ 超时[/]"
        
        out = stdout.decode("utf-8", errors="replace").strip()
        err = stderr.decode("utf-8", errors="replace").strip()
        
        if out:
            clean = re.sub(r'\x1b\[[0-9;]*m', '', out)
            return clean.strip() or out[:500]
        if err:
            return f"[red]⚠ {err[:300]}[/]"
        return f"[red]⚠ 无响应[/]"

    def on_input_submitted(self, event: Input.Submitted):
        text = event.value.strip()
        if not text or not self.hermes_bin:
            return
        event.input.value = ""
        self.log(f"\n[bold #00C896]你:[/] {text}")
        
        async def do_chat():
            response = await self._call_hermes(text)
            self.call_from_thread(lambda: self._show_response(response))
        
        asyncio.ensure_future(do_chat())

    def _show_response(self, response: str):
        self.log(f"\n[bold #7C3AED]Argent:[/]\n{response}\n")

    def action_clear(self):
        self.query_one("#chat-log").clear()


def main():
    ArgentApp().run()
