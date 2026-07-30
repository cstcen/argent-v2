"""Argent Setup — 问述账号登录、角色选择、飞书配置、Hermes 配置。"""

import webbrowser
import time
import json
import urllib.request
import urllib.error
import os
import subprocess
import sys
from pathlib import Path

ARGENT_HOME = Path(os.environ.get("ARGENT_HOME", Path.home() / ".argent"))
WHYSHU_BASE = os.environ.get("WHYSHU_API_URL", "https://whyshu.com")


def login_whyshu() -> bool:
    """Device Flow 登录问述科技账号，返回成功/失败。"""
    try:
        req = urllib.request.Request(
            f"{WHYSHU_BASE}/api/oauth/device",
            data=json.dumps({"client_id": "argent_cli"}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        device_code = data["device_code"]
        user_code = data["user_code"]
        verification_uri = data["verification_uri_complete"]
    except Exception as e:
        print(f"❌ 授权请求失败: {e}")
        return False

    print(f"\n请在浏览器中打开以下地址完成登录：")
    print(f"\n   {verification_uri}\n")
    print(f"授权码: {user_code}")
    
    try:
        webbrowser.open(verification_uri)
        print("✓ 已自动打开浏览器")
    except Exception:
        pass

    print("\n等待授权...", end="", flush=True)
    token = None
    for _ in range(60):
        time.sleep(2)
        print(".", end="", flush=True)
        try:
            req = urllib.request.Request(
                f"{WHYSHU_BASE}/api/oauth/token",
                data=json.dumps({
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    "device_code": device_code,
                    "client_id": "argent_cli",
                }).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            if "access_token" in data:
                token = data["access_token"]
                break
        except urllib.error.HTTPError as e:
            if e.code == 400:
                body = json.loads(e.read().decode())
                if body.get("error") == "authorization_pending":
                    continue
    print()

    if not token:
        print("❌ 授权超时，请重新运行 argent setup")
        return False

    ARGENT_HOME.mkdir(parents=True, exist_ok=True)
    (ARGENT_HOME / "auth_token").write_text(token)

    # 写入 WHYSHU_API_KEY 到 .env
    env_path = ARGENT_HOME / ".env"
    lines = []
    if env_path.exists():
        lines = [l for l in env_path.read_text().splitlines()
                 if not l.startswith("WHYSHU_API_KEY=")]
    lines.append(f"WHYSHU_API_KEY={token}")
    env_path.write_text("\n".join(lines) + "\n")

    # 写入 Hermes config.yaml
    _write_hermes_config()

    # 安装 whyshu provider 插件
    _install_whyshu_plugin()

    print("✅ 登录成功！")
    return True


def _write_hermes_config():
    """写入 Hermes 配置文件到 ~/.argent/config.yaml。"""
    config_path = ARGENT_HOME / "config.yaml"
    if config_path.exists():
        print("   config.yaml 已存在，跳过。")
        return

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
    print("   ✓ 默认配置已写入")


def _install_whyshu_plugin():
    """安装 whyshu provider 插件到 Hermes 插件目录。"""
    plugin_dir = ARGENT_HOME / "plugins" / "model-providers" / "whyshu"
    plugin_dir.mkdir(parents=True, exist_ok=True)

    (plugin_dir / "__init__.py").write_text("""\"\"\"WHYSHU provider profile.\"\"\"
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

    (plugin_dir / "plugin.yaml").write_text("""name: whyshu
kind: model-provider
version: 1.0.0
description: 问述科技 (WHYSHU) — 积分制 AI 模型服务
author: WHYSHU
""")
    print("   ✓ whyshu provider 插件已安装")


def select_role():
    """选择行业与角色（可选）。"""
    choice = input("  是否现在选择角色？[y/N]: ").strip().lower()
    if choice not in ("y", "yes"):
        print("  已跳过。稍后运行 argent role 配置。")
        return
    print("  角色选择功能将在后续版本中完善。")


def setup_feishu():
    """配置飞书对接（可选）。"""
    choice = input("  是否现在配置飞书？[y/N]: ").strip().lower()
    if choice not in ("y", "yes"):
        print("  已跳过。稍后运行 argent feishu-setup 配置。")
        return
    print("  飞书配置功能将在后续版本中完善。")
    print("  请访问 https://whyshu.com 获取飞书 Bot 配置指引。")
