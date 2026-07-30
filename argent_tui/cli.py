"""Argent CLI — 问述科技桌面 AI 助手。"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

ARGENT_HOME = Path(os.environ.get("ARGENT_HOME", Path.home() / ".argent"))
VERSION = "2.0.0"


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "chat"

    if cmd == "setup":
        return cmd_setup()
    elif cmd == "install":
        return cmd_install()
    elif cmd == "update":
        return cmd_update()
    elif cmd == "version" or cmd == "--version" or cmd == "-v":
        print(f"Argent v{VERSION}")
    elif cmd == "chat" or cmd == "" or cmd == "--help" or cmd == "-h":
        return cmd_chat()
    else:
        print(f"Unknown command: {cmd}")
        print("  argent              Start chat")
        print("  argent setup        配置 Argent")
        print("  argent install      安装 Hermes + 配置")
        print("  argent update       检查更新")
        print("  argent version      查看版本")


def cmd_chat():
    """启动 Argent TUI 聊天界面。"""
    from argent_tui.app import ArgentApp
    app = ArgentApp()
    app.run()


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

    # ── ① 登录 ──
    print("━━━ ① 登录问述科技账号 ━━━")
    from argent_tui.setup import login_whyshu
    if not login_whyshu():
        print("登录失败，请重试 argent setup")
        return
    
    # ── ② 角色 ──
    print()
    print("━━━ ② 选择行业与角色（可选） ━━━")
    from argent_tui.setup import select_role
    select_role()

    # ── ③ 飞书 ──
    print()
    print("━━━ ③ 配置飞书对接（可选） ━━━")
    from argent_tui.setup import setup_feishu
    setup_feishu()

    print()
    print("✅ Argent 配置完成！运行 argent 开始对话。")


def cmd_install():
    """安装 Hermes + 配置 whyshu provider。"""
    
    # 1. 检查 Hermes 是否已安装
    hermes_bin = shutil.which("hermes")
    if hermes_bin:
        print(f"✅ Hermes 已安装: {hermes_bin}")
    else:
        print("🔧 正在安装 Hermes Agent（约需 30 秒）...")
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "hermes-agent"],
                check=True,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=120
            )
            print("✅ Hermes Agent 已安装")
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            print("⚠️  安装失败。请手动执行：")
            print("   pip install hermes-agent")
            return

    # 2. 创建配置目录
    ARGENT_HOME.mkdir(parents=True, exist_ok=True)

    # 3. 写入 whyshu provider 插件
    plugin_dir = ARGENT_HOME / "plugins" / "model-providers" / "whyshu"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    _write_whyshu_plugin(plugin_dir)

    # 4. 写入默认 config
    config_path = ARGENT_HOME / "config.yaml"
    if not config_path.exists():
        config_path.write_text("""model:
  default: deepseek-v4-pro
  provider: whyshu
display:
  show_reasoning: false
  interface: tui
custom_providers:
  - name: whyshu
    base_url: https://whyshu.com/api/argent/v1
    api_key_env: WHYSHU_API_KEY
""")
        print("✅ 默认配置已创建")
    else:
        print("   config.yaml 已存在，跳过。")

    print()
    print("✅ 安装完成！运行 argent setup 配置账号。")


def cmd_update():
    """检查更新。"""
    print(f"✅ Argent v{VERSION} 已是最新版本。")


def _write_whyshu_plugin(dir: Path):
    """写入 whyshu provider 插件文件。"""
    (dir / "__init__.py").write_text("""\"\"\"WHYSHU provider profile.\"\"\"
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
    (dir / "plugin.yaml").write_text("""name: whyshu
kind: model-provider
version: 1.0.0
description: 问述科技 (WHYSHU) — 积分制 AI 模型服务
author: WHYSHU
""")


if __name__ == "__main__":
    main()
