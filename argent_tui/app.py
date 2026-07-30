"""Argent TUI — 基于 Textual 的问述科技聊天界面。

每轮对话通过 `hermes chat -q \"消息\"` 独立调用 Hermes。
"""

import os
import subprocess
import shutil
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

    def on_input_submitted(self, event: Input.Submitted):
        text = event.value.strip()
        if not text:
            return

        event.input.value = ""
        self.log(f"\n[bold #00C896]你:[/] {text}")

        if not self.hermes_bin:
            self.log("[red]⚠ hermes 未安装[/]")
            return

        env = os.environ.copy()
        env["HERMES_HOME"] = str(ARGENT_HOME)

        try:
            result = subprocess.run(
                [self.hermes_bin, "chat", "-q", text],
                capture_output=True, text=True,
                env=env, timeout=60,
            )
            out = result.stdout.strip()
            err = result.stderr.strip()

            if out:
                # 过滤 ANSI 转义序列，保留纯文本
                import re
                clean = re.sub(r'\x1b\[[0-9;]*m', '', out)
                clean = re.sub(r'╭─.*?╮\n?', '', clean, flags=re.DOTALL)
                clean = re.sub(r'╰─.*?╯\n?', '', clean, flags=re.DOTALL)
                clean = clean.strip()
                if clean:
                    self.log(f"\n[bold #7C3AED]Argent:[/]\n{clean}\n")
                else:
                    self.log(f"\n[bold #7C3AED]Argent:[/]\n{out[:500]}\n")
            elif err:
                self.log(f"[red]⚠ {err[:300]}[/]")
            else:
                self.log(f"[red]⚠ 无响应（返回码: {result.returncode}）[/]")

        except subprocess.TimeoutExpired:
            self.log("[red]⚠ 超时（60秒）[/]")
        except Exception as e:
            self.log(f"[red]⚠ 出错: {e}[/]")

    def action_clear(self):
        self.query_one("#chat-log").clear()


def main():
    app = ArgentApp()
    app.run()


if __name__ == "__main__":
    main()
