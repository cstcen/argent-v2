#!/usr/bin/env bash
# Argent v2 — 问述科技桌面 AI 助手 一键安装
set -euo pipefail

ARGENT_HOME="${ARGENT_HOME:-$HOME/.argent}"
RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
log_info()  { echo -e "${CYAN}→${NC} $*"; }
log_ok()    { echo -e "${GREEN}✓${NC} $*"; }
log_error() { echo -e "${RED}✗${NC} $*"; exit 1; }

ARGENT_VERSION="v2.0.0"
PIP_MIRROR=""  # 国内镜像，默认空
curl -s --connect-timeout 3 https://pypi.tuna.tsinghua.edu.cn/ &>/dev/null && PIP_MIRROR="-i https://pypi.tuna.tsinghua.edu.cn/simple" || true

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║    Argent ${ARGENT_VERSION}  安装中...              ║"
echo "║    问述科技 · 桌面 AI 助手                ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── 1. Python 环境 ──
log_info "检查 Python..."
if ! command -v python3 &>/dev/null; then
    log_error "未检测到 Python 3。请先安装 Python 3.10+：https://python.org"
fi
PY=$(python3 -c "import sys; v=sys.version_info; exit(0 if v>=(3,10) else 1)" 2>/dev/null && echo "ok" || echo "old")
if [ "$PY" != "ok" ]; then
    log_error "需要 Python 3.10+，当前版本：$(python3 --version)"
fi
log_ok "Python $(python3 --version | cut -d' ' -f2)"

# ── 2. 虚拟环境 & 安装 Argent ──
mkdir -p "$ARGENT_HOME"
ARGENT_VENV="$ARGENT_HOME/venv"
if [ ! -d "$ARGENT_VENV" ]; then
  log_info "创建 Python 虚拟环境..."
  python3 -m venv "$ARGENT_VENV"
fi
source "$ARGENT_VENV/bin/activate"
log_info "安装 Argent TUI..."
pip install $PIP_MIRROR --upgrade pip -q
pip install $PIP_MIRROR -q git+https://github.com/cstcen/argent-v2.git 2>&1 | tail -1 || log_error "Argent 安装失败"
log_ok "Argent TUI 已安装"

# 创建 argent 命令
mkdir -p "$ARGENT_HOME/bin"
cat > "$ARGENT_HOME/bin/argent" << 'ARGENTEOF'
#!/usr/bin/env bash
source "$HOME/.argent/venv/bin/activate"
exec python -m argent_tui.cli "$@"
ARGENTEOF
chmod +x "$ARGENT_HOME/bin/argent"
log_ok "argent 命令已创建"

# PATH
if [[ ":$PATH:" != *":$ARGENT_HOME/bin:"* ]]; then
  echo "export PATH=\"$ARGENT_HOME/bin:\$PATH\"" >> "$HOME/.bashrc"
fi

# ── 3. 安装/更新 Hermes（官方脚本）───
log_info "安装 Hermes Agent..."
rm -f "$HOME/.local/bin/hermes" 2>/dev/null || true
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash 2>&1 | tail -5
command -v hermes &>/dev/null || log_error "Hermes 安装失败，请检查网络后重试"
log_ok "Hermes Agent 已安装"

# ── 4. 配置 ──
if [ ! -f "$ARGENT_HOME/config.yaml" ]; then
    log_info "创建默认配置..."
    cat > "$ARGENT_HOME/config.yaml" << 'YAML'
model:
  default: deepseek-v4-pro
  provider: whyshu
display:
  show_reasoning: false
  interface: tui
YAML
    log_ok "默认配置已创建"
else
    log_info "config.yaml 已存在，跳过"
fi

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║    Argent ${ARGENT_VERSION}  安装完成!              ║"
echo "╠══════════════════════════════════════════╣"
echo "║  下一步:                                  ║"
echo "║    source ~/.bashrc                      ║"
echo "║    argent setup   配置账号                ║"
echo "║    argent         开始对话                ║"
echo "╚══════════════════════════════════════════╝"
echo ""

if [ -t 0 ]; then
  exec "$SHELL" -l
fi
