"""Argent TUI — 调试版（写文件日志）。"""
import os, shutil, asyncio
from pathlib import Path
from textual.app import App, ComposeResult
from textual.widgets import Input, Static

ARGENT_HOME = Path(os.environ.get("ARGENT_HOME", Path.home() / ".argent"))
LOG_FILE = ARGENT_HOME / "argent_debug.log"

def dbg(msg: str):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(msg + "\n")

class ArgentApp(App):
    CSS = "Screen { background: #0D1B2A; } #log { padding: 1 2; color: #DDE4EC; } #inp { dock: bottom; margin: 1 2; height: 3; }"

    def compose(self) -> ComposeResult:
        yield Static("", id="log")
        yield Input(placeholder="输入消息...", id="inp")

    def on_mount(self):
        dbg("on_mount start")
        self.hermes_bin = shutil.which("hermes")
        dbg(f"Hermes: {self.hermes_bin}")
        self._log(f"Hermes: {self.hermes_bin or 'NOT FOUND'}")
        dbg("on_mount done")

    def _log(self, msg: str):
        self._log_text = getattr(self, "_log_text", "") + "\n" + str(msg)[:500]
        self.query_one("#log").update(self._log_text)

    def on_input_submitted(self, event: Input.Submitted):
        dbg(f"INPUT: {event.value!r}")
        text = event.value.strip()
        if not text:
            dbg("INPUT: empty")
            return
        event.input.value = ""
        self._log(f"你: {text}")
        dbg("INPUT: logged")

        if not self.hermes_bin:
            self._log("⚠ hermes 未安装")
            dbg("INPUT: no hermes_bin")
            return

        async def chat():
            dbg("CHAT: starting subprocess")
            env = os.environ.copy()
            env["HERMES_HOME"] = str(ARGENT_HOME)
            env_file = ARGENT_HOME / ".env"
            if env_file.exists():
                for line in env_file.read_text().splitlines():
                    if line.strip() and "=" in line and not line.startswith("#"):
                        k, _, v = line.partition("=")
                        env[k.strip()] = v.strip()
            dbg(f"CHAT: calling hermes chat -q {text!r}")
            proc = await asyncio.create_subprocess_exec(
                self.hermes_bin, "--cli", "chat", "-q", text,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=env,
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
            except asyncio.TimeoutError:
                proc.kill()
                stdout, stderr = await proc.communicate()
                dbg("CHAT: TIMEOUT")
            out = stdout.decode("utf-8", errors="replace")
            err = stderr.decode("utf-8", errors="replace")
            dbg(f"CHAT: stdout={len(out)} stderr={len(err)} rc={proc.returncode}")
            self._log(f"stdout: {out[:300]}")
            self._log(f"stderr: {err[:300]}")

        asyncio.ensure_future(chat())
        dbg("INPUT: future created")

def main():
    dbg("=== argent start ===")
    ArgentApp().run()
