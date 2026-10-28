#!/bin/bash
# SuperWiki 安装脚本
# 用法: ./skills.sh [项目路径]
#
# 只把本仓库这一个 skill 链接到全局 agent 兼容 skill 目录：
#   superwiki -> 本仓库根目录
#   目标目录: ~/.agents/skills（agent-compatible）
# 不会写入 OpenCode / Claude Code / Codex / Cursor 各自的 skill 目录。
# 已存在的同名符号链接指向本仓库时跳过，指向别处时更新为本仓库；
# 同名路径不是符号链接时保留并跳过，不覆盖、不清理。
# 不会安装同级其他 skill，也不扫描或链接仓库外的目录。

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_NAME="superwiki"

install_global_link() {
    LABEL="$1"
    SKILLS_DIR="$2"
    LINK_PATH="$SKILLS_DIR/$SKILL_NAME"

    mkdir -p "$SKILLS_DIR"
    echo "安装 $SKILL_NAME 到 $SKILLS_DIR... ($LABEL)"

    if [ -L "$LINK_PATH" ]; then
        LINK_TARGET="$(readlink "$LINK_PATH")"
        if [ "$LINK_TARGET" = "$SCRIPT_DIR" ]; then
            echo "⏭️  符号链接已存在: $LINK_PATH"
        else
            ln -snf "$SCRIPT_DIR" "$LINK_PATH"
            echo "🔄 更新符号链接: $LINK_PATH -> $SCRIPT_DIR"
        fi
    elif [ -e "$LINK_PATH" ]; then
        echo "⚠️  路径已存在且不是符号链接，跳过: $LINK_PATH"
    else
        ln -s "$SCRIPT_DIR" "$LINK_PATH"
        echo "✅ 创建符号链接: $LINK_PATH -> $SCRIPT_DIR"
    fi
}

install_global_link "agent-compatible" "$HOME/.agents/skills"

# 如果指定了项目路径，初始化该项目
if [ -n "$1" ]; then
    echo ""
    echo "初始化项目: $1"
    "$SCRIPT_DIR/superwiki-init" "$1"
fi

echo ""
echo "安装完成！全局 skill 链接: $HOME/.agents/skills/$SKILL_NAME"
echo ""
echo "使用方式:"
echo "  1. 在项目中初始化: $SCRIPT_DIR/superwiki-init /path/to/project"
echo "  2. 使用当前运行时的原生 skill 机制加载: $SKILL_NAME"
