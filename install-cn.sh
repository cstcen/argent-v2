#!/usr/bin/env bash
# Argent — 问述科技桌面 AI 助手 一键安装
set -euo pipefail

ARGENT_HOME="${ARGENT_HOME:-$HOME/.argent}"
RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
log_info()  { echo -e "${CYAN}→${NC} $*"; }
log_ok()    { echo -e "${GREEN}✓${NC} $*"; }
log_error() { echo -e "${RED}✗${NC} $*"; exit 1; }

ARGENT_VERSION="v0.3.2"
PIP_MIRROR="-i https://pypi.tuna.tsinghua.edu.cn/simple"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║    Argent ${ARGENT_VERSION}  安装中...              ║"
echo "║    问述科技 · 桌面 AI 助手                ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── 1. Node.js（Hermes TUI 依赖）───
log_info "检查 Node.js..."
if ! command -v node &>/dev/null; then
    log_info "正在安装 Node.js..."
    sudo apt install -y nodejs 2>/dev/null || {
        curl -fsSL https://deb.nodesource.com/setup_20.x 2>/dev/null | sudo bash 2>/dev/null
        sudo apt install -y nodejs 2>/dev/null
    } || log_info "请手动安装 Node.js: sudo apt install nodejs"
fi
command -v node &>/dev/null && log_ok "Node.js $(node --version)" || true

# ── 2. Python ──
log_info "检查 Python..."
command -v python3 &>/dev/null || log_error "请先安装 Python 3.10+"
log_ok "Python $(python3 --version | cut -d' ' -f2)"

# ── 3. venv + Argent ──
mkdir -p "$ARGENT_HOME"
ARGENT_VENV="$ARGENT_HOME/venv"
if [ ! -d "$ARGENT_VENV" ]; then
  python3 -m venv "$ARGENT_VENV"
fi
source "$ARGENT_VENV/bin/activate"

# 确保基础构建工具
pip install $PIP_MIRROR --upgrade pip setuptools wheel -q 2>/dev/null || true

log_info "安装 Argent TUI..."
pip install $PIP_MIRROR --no-build-isolation -q https://whyshu.com/dl/argent.tar.gz 2>&1 | tail -1 || log_error "Argent 安装失败"
log_ok "Argent TUI 已安装"

# 创建 argent 命令（覆盖旧版）
mkdir -p "$ARGENT_HOME/bin"
rm -f "$HOME/.local/bin/argent" "$HOME/.local/bin/argent.exe" 2>/dev/null || true
rm -f "$ARGENT_HOME/venv/bin/argent" 2>/dev/null || true  # pip 装的旧入口
cat > "$ARGENT_HOME/bin/argent" << 'ARGENTEOF'
#!/usr/bin/env bash
source "$HOME/.argent/venv/bin/activate"

# 内置命令：不依赖 argent Python 代码版本，shell 直接处理
case "${1:-chat}" in
  update)
    echo "🔄 正在更新 Argent..."
    pip install --no-cache-dir --force-reinstall --no-deps -q https://whyshu.com/dl/argent.tar.gz
    V=$(python -c "from argent_tui import __version__; print(__version__)" 2>/dev/null || echo "?")
    echo "✅ 已更新至 Argent v${V}"
    ;;
  whoami|balance|points)
    pip install --no-cache-dir --force-reinstall --no-deps -q https://whyshu.com/dl/argent.tar.gz 2>/dev/null
    exec python -m argent_tui.cli "$@"
    ;;
  version|--version|-v)
    echo "Argent v0.3.2"
    ;;
  *)
    exec python -m argent_tui.cli "$@"
    ;;
esac
ARGENTEOF
chmod +x "$ARGENT_HOME/bin/argent"
log_ok "argent 命令已创建"

if [[ ":$PATH:" != *":$ARGENT_HOME/bin:"* ]]; then
  echo "export PATH=\"$ARGENT_HOME/bin:\$PATH\"" >> "$HOME/.bashrc"
fi

# ── 4. Hermes（官方脚本，失败则 pip 镜像）───
log_info "安装 Hermes Agent..."
rm -f "$HOME/.local/bin/hermes" 2>/dev/null || true
if curl -fsSL --connect-timeout 10 https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash 2>&1 | tail -3; then
    :
elif command -v hermes &>/dev/null; then
    :
else
    log_info "GitHub 不可达，使用镜像安装..."
    pip install $PIP_MIRROR -q hermes-agent 2>&1 | tail -3
fi
command -v hermes &>/dev/null || log_error "Hermes 安装失败，请检查网络"
log_ok "Hermes Agent 已安装"

# ── 5. 配置 ──
if [ ! -f "$ARGENT_HOME/config.yaml" ]; then
    cat > "$ARGENT_HOME/config.yaml" << 'YAML'
model:
  default: deepseek-v4-pro
  provider: whyshu
display:
  show_reasoning: false
  interface: tui
YAML
fi

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║    Argent ${ARGENT_VERSION}  安装完成!              ║"
echo "╠══════════════════════════════════════════╣"
echo "║    argent setup   配置账号                ║"
echo "║    argent         开始对话                ║"
echo "╚══════════════════════════════════════════╝"
echo ""

if [ -t 0 ]; then exec "$SHELL" -l; fi
