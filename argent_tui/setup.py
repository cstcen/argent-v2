"""Argent Setup — 问述账号登录、角色选择、飞书配置、Hermes 配置。"""

import webbrowser, time, json, urllib.request, urllib.error, os, subprocess, sys, shutil
from pathlib import Path

ARGENT_HOME = Path(os.environ.get("ARGENT_HOME", Path.home() / ".argent"))
HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
WHYSHU_BASE = os.environ.get("WHYSHU_API_URL", "https://whyshu.com")

PLUGIN_INIT = '''"""WHYSHU provider profile."""
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
'''

PLUGIN_YAML = """name: whyshu
kind: model-provider
version: 1.0.0
description: 问述科技 (WHYSHU) — 积分制 AI 模型服务
author: WHYSHU
"""

CONFIG_YAML = """model:
  default: deepseek-v4-pro
  provider: whyshu
display:
  show_reasoning: false
  interface: tui
custom_providers:
  - name: whyshu
    base_url: https://whyshu.com/api/argent/v1
    api_key_env: WHYSHU_API_KEY
"""


def login_whyshu() -> bool:
    """Device Flow 登录问述科技账号。"""
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

    print(f"\n请在浏览器中打开：\n   {verification_uri}\n")
    print(f"授权码: {user_code}")
    try:
        webbrowser.open(verification_uri)
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
                    "device_code": device_code, "client_id": "argent_cli",
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
        print("❌ 授权超时")
        return False

    ARGENT_HOME.mkdir(parents=True, exist_ok=True)
    (ARGENT_HOME / "auth_token").write_text(token)

    # 写入 .env
    env_path = ARGENT_HOME / ".env"
    lines = []
    if env_path.exists():
        lines = [l for l in env_path.read_text().splitlines() if not l.startswith("WHYSHU_API_KEY=")]
    lines.append(f"WHYSHU_API_KEY={token}")
    env_path.write_text("\n".join(lines) + "\n")

    # ═══ 关键：写入 Hermes 自己目录的 config + 插件 ═══
    HERMES_HOME.mkdir(parents=True, exist_ok=True)
    
    # config.yaml
    (HERMES_HOME / "config.yaml").write_text(CONFIG_YAML)
    
    # whyshu 插件 → Hermes 的 plugins 目录（Hermes 只扫这里）
    plugin_dir = HERMES_HOME / "plugins" / "model-providers" / "whyshu"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "__init__.py").write_text(PLUGIN_INIT)
    (plugin_dir / "plugin.yaml").write_text(PLUGIN_YAML)

    # 同时写一份到 Argent 自己的目录（备用）
    arg_plugin = ARGENT_HOME / "plugins" / "model-providers" / "whyshu"
    arg_plugin.mkdir(parents=True, exist_ok=True)
    (arg_plugin / "__init__.py").write_text(PLUGIN_INIT)
    (arg_plugin / "plugin.yaml").write_text(PLUGIN_YAML)
    (ARGENT_HOME / "config.yaml").write_text(CONFIG_YAML)

    # 同步 .env 到 Hermes
    shutil.copy(ARGENT_HOME / ".env", HERMES_HOME / ".env")
    
    # symlink Hermes → Argent（让两者共用配置）
    try:
        os.symlink(str(ARGENT_HOME / "config.yaml"), str(HERMES_HOME / "config.yaml"))
    except FileExistsError:
        pass

    print("✅ 登录成功！Hermes 已配置 whyshu provider。")
    return True


def select_role():
    choice = input("  是否现在选择角色？[y/N]: ").strip().lower()
    if choice not in ("y", "yes"):
        print("  已跳过。")
        return
    print("  角色选择功能将在后续版本中完善。")


def setup_feishu():
    choice = input("  是否现在配置飞书？[y/N]: ").strip().lower()
    if choice not in ("y", "yes"):
        print("  已跳过。")
        return
    print("  飞书配置功能将在后续版本中完善。")
