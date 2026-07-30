#!/usr/bin/env bash
# Argent v2 — 问述科技桌面 AI 助手 一键安装
set -euo pipefail

ARGENT_HOME="${ARGENT_HOME:-$HOME/.argent}"
RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
log_info()  { echo -e "${CYAN}→${NC} $*"; }
log_ok()    { echo -e "${GREEN}✓${NC} $*"; }
log_error() { echo -e "${RED}✗${NC} $*"; exit 1; }

ARGENT_VERSION="v2.0.0"

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

# ── 2. 安装 Argent TUI ──
log_info "安装 Argent TUI..."
pip3 install --user -q git+https://github.com/cstcen/argent-v2.git 2>&1 | tail -1 || log_error "Argent 安装失败"
log_ok "Argent TUI 已安装"

# ── 3. 检查/安装 Hermes ──
if command -v hermes &>/dev/null; then
    log_ok "Hermes 已安装: $(which hermes)"
else
    log_info "安装 Hermes Agent（约需 30 秒）..."
    pip3 install --user -q hermes-agent 2>&1 | tail -1 || {
        log_info "pip 安装失败，尝试 pipx..."
        pipx install hermes-agent 2>/dev/null || log_error "Hermes 安装失败，请手动安装：pip install hermes-agent"
    }
    log_ok "Hermes Agent 已安装"
fi

# ── 4. 配置 ──
mkdir -p "$ARGENT_HOME"
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

# ── 5. PATH ──
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
    log_info "已添加 ~/.local/bin 到 PATH（重启终端后生效）"
fi

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║    Argent ${ARGENT_VERSION}  安装完成!              ║"
echo "╠══════════════════════════════════════════╣"
echo "║  下一步:                                  ║"
echo "║    argent setup   配置账号                ║"
echo "║    argent         开始对话                ║"
echo "╚══════════════════════════════════════════╝"
echo ""
