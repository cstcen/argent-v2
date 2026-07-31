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
  provider: custom
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

    # ═══ 安装 whyshu provider 插件到 Hermes bundled 目录 ═══
    # bundled dir is where Hermes scans for providers
    import providers as _providers
    bundled = Path(_providers.__file__).parent / ".." / "plugins" / "model-providers" / "whyshu"
    bundled = bundled.resolve()
    bundled.mkdir(parents=True, exist_ok=True)
    (bundled / "__init__.py").write_text(PLUGIN_INIT)
    (bundled / "plugin.yaml").write_text(PLUGIN_YAML)
    print(f"   ✓ whyshu 插件已安装到 Hermes")

    # config.yaml — provider: whyshu
    HERMES_HOME.mkdir(parents=True, exist_ok=True)
    config = """model:
  default: deepseek-v4-pro
  provider: whyshu
display:
  show_reasoning: false
  interface: cli
"""
    (HERMES_HOME / "config.yaml").write_text(config)
    (ARGENT_HOME / "config.yaml").write_text(config)

    # .env
    env_path = ARGENT_HOME / ".env"
    lines = []
    if env_path.exists():
        lines = [l for l in env_path.read_text().splitlines()
                 if not l.startswith(("WHYSHU_API_KEY=", "OPENROUTER_API_KEY="))]
    lines.append(f"WHYSHU_API_KEY={token}")
    env_path.write_text("\n".join(lines) + "\n")
    
    # sync .env to Hermes HOME
    shutil.copy(ARGENT_HOME / ".env", HERMES_HOME / ".env")

    print("✅ 登录成功！Hermes 已配置 whyshu provider。")

    # ── 安装 Skills ──
    _install_skills()

    return True


def select_role():
    """选择行业与角色，写入 config.yaml。"""
    import yaml

    print()
    print("  可用行业角色：")
    roles = [
        ("1", "通用助手", "general", "基础 AI 对话，无行业限制"),
        ("2", "美客多运营", "mercadolibre", "美客多电商运营（店铺日报/关键词/货件管理）"),
        ("3", "美客多老板", "mercadolibre_boss", "美客多店铺概览与分析"),
    ]
    for num, name, _key, desc in roles:
        print(f"  [{num}] {name} — {desc}")
    print(f"  [0] 跳过")

    while True:
        choice = input(f"\n  请选择 [0-{len(roles)}]: ").strip()
        if choice == "0" or choice == "":
            print("  已跳过。稍后运行 argent role 重新配置。")
            return
        selected = [r for r in roles if r[0] == choice]
        if selected:
            _, name, key, _ = selected[0]
            # 写入 config.yaml
            config_path = ARGENT_HOME / "config.yaml"
            if config_path.exists():
                with open(config_path) as f:
                    config = yaml.safe_load(f) or {}
            else:
                config = {}
            config["argent"] = config.get("argent", {})
            config["argent"]["role"] = key
            config["argent"]["role_name"] = name
            with open(config_path, "w") as f:
                yaml.dump(config, f, allow_unicode=True)
            # 同步到 Hermes
            shutil.copy(config_path, HERMES_HOME / "config.yaml")
            print(f"\n  ✅ 已选择角色：{name}")
            print(f"     配置已写入 {config_path}")
            return
        print("  无效选择，请重试。")


def setup_feishu():
    """配置飞书对接。写入 Gateway 配置。"""
    import yaml

    choice = input("  是否现在配置飞书？[y/N]: ").strip().lower()
    if choice not in ("y", "yes"):
        print("  已跳过。稍后运行 argent feishu-setup 配置。")
        return

    print()
    print("  飞书配置需要以下信息：")
    print("  - 飞书 App ID（可在飞书开放平台获取）")
    print("  - 飞书 App Secret")
    print()
    print("  获取方式：https://open.feishu.cn → 开发者后台 → 创建企业自建应用")
    print()

    app_id = input("  App ID: ").strip()
    if not app_id:
        print("  ⚠ App ID 不能为空，已跳过。")
        return

    app_secret = input("  App Secret: ").strip()
    if not app_secret:
        print("  ⚠ App Secret 不能为空，已跳过。")
        return

    # 写入 config.yaml
    config_path = ARGENT_HOME / "config.yaml"
    if config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f) or {}
    else:
        config = {}

    config["gateway"] = config.get("gateway", {})
    config["gateway"]["platforms"] = config["gateway"].get("platforms", {})
    config["gateway"]["platforms"]["feishu"] = {
        "app_id": app_id,
        "app_secret": app_secret,
        "app_type": "self_built",
    }
    with open(config_path, "w") as f:
        yaml.dump(config, f, allow_unicode=True)

    # 同步到 Hermes
    shutil.copy(config_path, HERMES_HOME / "config.yaml")

    # 写入 .env（Feishu 凭证）
    env_path = ARGENT_HOME / ".env"
    lines = []
    if env_path.exists():
        lines = [l for l in env_path.read_text().splitlines()
                 if not l.startswith(("FEISHU_APP_ID=", "FEISHU_APP_SECRET="))]
    lines.append(f"FEISHU_APP_ID={app_id}")
    lines.append(f"FEISHU_APP_SECRET={app_secret}")
    env_path.write_text("\n".join(lines) + "\n")
    shutil.copy(env_path, HERMES_HOME / ".env")

    print(f"\n  ✅ 飞书配置已完成")
    print(f"     运行 argent gateway install 启用飞书推送")


def _install_skills():
    """将 Argent 预置 Skills 复制到 ~/.argent/skills/。"""
    from pathlib import Path

    # Skills 来源：打包在 argent_tui 内的 skills/ 目录
    src = Path(__file__).parent / "skills"
    if not src.is_dir():
        return

    dst = ARGENT_HOME / "skills"
    dst.mkdir(parents=True, exist_ok=True)

    count = 0
    for item in src.iterdir():
        target = dst / item.name
        if item.is_dir() and not (target / "SKILL.md").exists():
            shutil.copytree(item, target, dirs_exist_ok=True)
            count += 1

    if count:
        print(f"  ✅ {count} 个 Skills 已安装到 ~/.argent/skills/")