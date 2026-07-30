"""Argent CLI — 问述科技桌面 AI 助手。"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

ARGENT_HOME = Path(os.environ.get("ARGENT_HOME", Path.home() / ".argent"))
HERMES_HOME = ARGENT_HOME
VERSION = "0.3.0"


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "chat"

    if cmd == "setup":
        return cmd_setup()
    elif cmd == "install":
        return cmd_install()
    elif cmd == "version" or cmd == "--version" or cmd == "-v":
        print(f"Argent v{VERSION}")
    elif cmd == "chat" or cmd == "" or cmd == "--help" or cmd == "-h":
        return cmd_chat()
    else:
        # 其余参数透传给 hermes
        return _exec_hermes(sys.argv[1:])


def cmd_chat():
    """启动 Hermes TUI（HERMES_HOME 指向 Argent 配置目录）。"""
    _exec_hermes(["--tui"])


def cmd_setup():
    """三步引导配置。"""
    print("╔══════════════════════════════════════════╗")
    print("║     欢迎使用 Argent 桌面 AI 助手        ║")
    print("╠══════════════════════════════════════════╣")
    print("║  ①  登录问述科技账号（必须）            ║")
    print("║  ②  选择行业与角色（可选）              ║")
    print("║  ③  配置飞书对接（可选）                ║")
    print("╚══════════════════════════════════════════╝")
    print()

    print("━━━ ① 登录问述科技账号 ━━━")
    from argent_tui.setup import login_whyshu
    if not login_whyshu():
        print("登录失败，请重试 argent setup")
        return
    
    print()
    print("━━━ ② 选择行业与角色（可选） ━━━")
    from argent_tui.setup import select_role
    select_role()

    print()
    print("━━━ ③ 配置飞书对接（可选） ━━━")
    from argent_tui.setup import setup_feishu
    setup_feishu()

    print()
    print("✅ Argent 配置完成！运行 argent 开始对话。")


def cmd_install():
    """安装 Hermes + 配置 whyshu provider。"""
    hermes_bin = shutil.which("hermes")
    if hermes_bin:
        print(f"✅ Hermes 已安装: {hermes_bin}")
    else:
        print("🔧 正在安装 Hermes Agent...")
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "hermes-agent"],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120,
            )
            print("✅ Hermes Agent 已安装")
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            print("⚠️  安装失败。请手动：pip install hermes-agent")
            return

    ARGENT_HOME.mkdir(parents=True, exist_ok=True)
    print("✅ 安装完成！运行 argent setup 配置账号。")


def _write_whyshu_plugin():
    """写入 whyshu provider 插件到 Hermes bundled 目录。"""
    import providers
    bundled = Path(providers.__file__).parent.parent / "plugins" / "model-providers" / "whyshu"
    bundled.mkdir(parents=True, exist_ok=True)
    (bundled / "__init__.py").write_text("""\"\"\"WHYSHU provider profile.\"\"\"
from typing import Any
from providers import register_provider
from providers.base import ProviderProfile

class WhyshuProfile(ProviderProfile):
    def build_api_kwargs_extras(self, *, reasoning_config=None, **ctx: Any):
        return {}, {}

whyshu = WhyshuProfile(
    name="whyshu", aliases=(),
    env_vars=("WHYSHU_API_KEY",),
    base_url="https://whyshu.com/api/argent/v1",
    default_max_tokens=131072,
)
register_provider(whyshu)
""")
    (bundled / "plugin.yaml").write_text("name: whyshu\nkind: model-provider\nversion: 1.0.0\ndescription: 问述科技\n")


def _exec_hermes(args: list):
    """执行 hermes，设置 HERMES_HOME 指向 Argent 配置目录。"""
    env = os.environ.copy()
    env["HERMES_HOME"] = str(HERMES_HOME)
    # 注入 .env 中的环境变量
    env_file = ARGENT_HOME / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.strip() and "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()

    hermes = shutil.which("hermes") or "hermes"
    os.execve(hermes, [hermes] + list(args), env)


if __name__ == "__main__":
    main()
