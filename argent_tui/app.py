"""Argent TUI — 极简调试版 v3."""
import os, shutil, asyncio
from pathlib import Path
from textual.app import App, ComposeResult
from textual.widgets import Input, Static

ARGENT_HOME = Path(os.environ.get("ARGENT_HOME", Path.home() / ".argent"))

class ArgentApp(App):
    CSS = "Screen { background: #0D1B2A; } #log { padding: 1 2; color: #DDE4EC; } #inp { dock: bottom; margin: 1 2; height: 3; }"

    def compose(self) -> ComposeResult:
        yield Static("", id="log")
        yield Input(placeholder="输入消息...", id="inp")

    def on_mount(self):
        self.hermes_bin = shutil.which("hermes")
        msg = f"Hermes: {self.hermes_bin or 'NOT FOUND'}"
        print(msg, flush=True)
        self._log(msg)
        print("on_mount done", flush=True)

    def _log(self, msg: str):
        print(f"LOG: {msg[:100]}", flush=True)
        self._log_text = getattr(self, "_log_text", "") + "\n" + str(msg)[:500]
        self.query_one("#log").update(self._log_text)

    def on_input_submitted(self, event: Input.Submitted):
        print(f"INPUT: {event.value!r}", flush=True)
        text = event.value.strip()
        if not text:
            print("INPUT: empty!", flush=True)
            return
        event.input.value = ""
        self._log(f"你: {text}")
        print("INPUT: logged", flush=True)

        if not self.hermes_bin:
            self._log("⚠ hermes 未安装")
            return

        async def chat():
            print("CHAT: starting subprocess", flush=True)
            env = os.environ.copy()
            env["HERMES_HOME"] = str(ARGENT_HOME)
            env_file = ARGENT_HOME / ".env"
            if env_file.exists():
                for line in env_file.read_text().splitlines():
                    if line.strip() and "=" in line and not line.startswith("#"):
                        k, _, v = line.partition("=")
                        env[k.strip()] = v.strip()
            print(f"CHAT: calling hermes chat -q {text!r}", flush=True)
            proc = await asyncio.create_subprocess_exec(
                self.hermes_bin, "chat", "-q", text,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=env,
            )
            stdout, stderr = await proc.communicate()
            out = stdout.decode("utf-8", errors="replace")
            err = stderr.decode("utf-8", errors="replace")
            print(f"CHAT: stdout[{len(out)}] stderr[{len(err)}] rc={proc.returncode}", flush=True)
            self._log(f"stdout: {out[:200]}")
            self._log(f"stderr: {err[:200]}")

        asyncio.ensure_future(chat())
        print("INPUT: future created", flush=True)

def main():
    ArgentApp().run()
