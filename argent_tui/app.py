"""Argent TUI — 基于 Textual 的问述科技聊天界面。

每轮对话通过 `hermes -c \"消息\"` 独立调用 Hermes。
"""

import os
import subprocess
import shutil
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
        """检查 hermes 是否可用。"""
        self.hermes_bin = shutil.which("hermes")
        if not self.hermes_bin:
            self.log("[red]⚠ hermes 未安装。请运行 argent install[/]")
            self.log("   pip install hermes-agent\n")
        else:
            self.log(f"[#00C896]✓[/] Hermes 就绪")

    async def on_input_submitted(self, event: Input.Submitted):
        """用户输入消息 — 调用 hermes -c。"""
        text = event.value.strip()
        if not text:
            return

        event.input.value = ""
        self.log(f"\n[bold #00C896]你:[/] {text}")

        if not self.hermes_bin:
            self.log("[red]⚠ hermes 未安装[/]")
            return

        # 显示等待状态
        self.log("[#5E5878]...[/]")
        
        try:
            env = os.environ.copy()
            env["HERMES_HOME"] = str(ARGENT_HOME)
            
            # 异步调用 hermes chat -q "消息"
            proc = await asyncio.create_subprocess_exec(
                self.hermes_bin, "chat", "-q", text,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=60
            )
            
            # 移除最后一条日志（"...")
            # RichLog 没有直接删除最后一条的 API，用 replace
            log_widget = self.query_one("#chat-log")
            
            response = stdout.decode("utf-8", errors="replace").strip()
            if response:
                self.log(f"\n[bold #7C3AED]Argent:[/] {response}\n")
            else:
                err = stderr.decode("utf-8", errors="replace").strip()
                self.log(f"[red]⚠ 无回复[/]")
                if err:
                    self.log(f"[#5E5878]{err[:200]}[/]")
                    
        except asyncio.TimeoutError:
            self.log("[red]⚠ 超时（60秒）[/]")
        except Exception as e:
            self.log(f"[red]⚠ 出错: {e}[/]")

    def action_clear(self):
        """清屏。"""
        self.query_one("#chat-log").clear()


def main():
    app = ArgentApp()
    app.run()


if __name__ == "__main__":
    main()
