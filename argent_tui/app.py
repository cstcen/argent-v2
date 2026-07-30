"""Argent TUI — 基于 Textual 的问述科技聊天界面。

启动 hermes 子进程进行 AI 对话，本界面只负责展示和输入。
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, TextArea, RichLog, Input
from textual.containers import Container, Vertical
from textual.binding import Binding

ARGENT_HOME = Path(os.environ.get("ARGENT_HOME", Path.home() / ".argent"))


class ArgentApp(App):
    """Argent 主聊天界面。"""

    CSS = """
    #chat-log { border: none; background: #0D1B2A; }
    #chat-log .textual-rich-log--text { color: #DDE4EC; }
    #user-input { border: solid #2A3A4A; background: #162030; color: #FFFFFF; margin: 1 2; height: 3; }
    #user-input:focus { border: solid #00C896; }
    .header { background: #0D1B2A; color: #00C896; padding: 0 2; height: 3; }
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
        self.hermes = None
        self._start_hermes()
        self.log("[#00C896]Argent v2.0.0[/] — 问述科技桌面 AI 助手")
        self.log("输入消息开始对话，Ctrl+Q 退出\n")
        self.query_one("#user-input").focus()

    def _start_hermes(self):
        """启动 hermes 子进程。"""
        hermes_bin = shutil.which("hermes") or "hermes"
        
        # 设置环境变量
        env = os.environ.copy()
        env["HERMES_HOME"] = str(ARGENT_HOME)
        
        try:
            self.hermes = subprocess.Popen(
                [hermes_bin, "--cli"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                bufsize=1,
            )
        except FileNotFoundError:
            self.log("[red]⚠ hermes 未安装。请运行 argent install[/]")
            return
        except Exception as e:
            self.log(f"[red]⚠ 启动 hermes 失败: {e}[/]")
            return

        self.log("[#00C896]✓[/] Hermes 已连接")

    def on_input_submitted(self, event: Input.Submitted):
        """用户输入消息。"""
        text = event.value.strip()
        if not text:
            return

        event.input.value = ""
        self.log(f"\n[bold #00C896]你:[/] {text}")

        if self.hermes is None or self.hermes.poll() is not None:
            self.log("[red]⚠ Hermes 未连接，正在重连...[/]")
            self._start_hermes()
            if self.hermes is None:
                return

        try:
            self.hermes.stdin.write(text + "\n")
            self.hermes.stdin.flush()
            
            # 读取回复（阻塞直到收到完整回复）
            # 实际实现需要处理流式输出
            response = self._read_response()
            self.log(f"\n[bold #7C3AED]Argent:[/] {response}\n")
        except Exception as e:
            self.log(f"[red]⚠ 对话出错: {e}[/]")

    def _read_response(self) -> str:
        """从 hermes 读取回复。"""
        lines = []
        while True:
            line = self.hermes.stdout.readline()
            if not line:
                break
            line = line.rstrip()
            if line == "---END---" or line == "":
                if lines:
                    break
                continue
            lines.append(line)
        return "\n".join(lines)

    def action_clear(self):
        """清屏。"""
        self.query_one("#chat-log").clear()

    def on_unmount(self):
        """关闭 hermes 子进程。"""
        if self.hermes:
            self.hermes.terminate()
            try:
                self.hermes.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.hermes.kill()


def main():
    app = ArgentApp()
    app.run()


if __name__ == "__main__":
    main()
