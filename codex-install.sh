#!/usr/bin/env bash
set -euo pipefail

# Codex-native installer for geo-seo-claude.
# It is additive to the original Claude Code installer and never deletes files.

REPO_URL="https://github.com/blindgodw-sys/geo-seo-claude-codex.git"
CODEX_DIR="${CODEX_HOME:-${HOME}/.codex}"
SKILLS_DIR="${CODEX_DIR}/skills"
INSTALL_DIR="${SKILLS_DIR}/geo"
VENV_DIR="${INSTALL_DIR}/.venv"
VENV_PY="${VENV_DIR}/bin/python3"
BACKUP_DIR="/tmp/geo-codex-install-$(date +%Y%m%d-%H%M%S)"
TEMP_DIR="${BACKUP_DIR}/work"

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_info() { echo -e "${BLUE}-> $1${NC}"; }
print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }

copy_dir_contents() {
    local src="$1"
    local dst="$2"
    mkdir -p "$dst"
    if [ -d "$src" ]; then
        cp -R "$src"/. "$dst"/
    fi
}

patch_markdown() {
    local file="$1"
    perl -0pi -e 's#~/.claude#~/.codex#g' "$file"
    perl -0pi -e 's#Claude Code CLI#Codex CLI#g' "$file"
    perl -0pi -e 's#Claude Code#Codex#g' "$file"
    perl -0pi -e 's#WebFetch#web-access or HTTP fetch#g' "$file"
    perl -0pi -e 's#python3 ~/\.codex/skills/geo/scripts/#~/.codex/skills/geo/scripts/#g' "$file"
    perl -0pi -e "s#python3 -c #${VENV_PY} -c #g" "$file"
    perl -0pi -e "s#python3 -m #${VENV_PY} -m #g" "$file"
    if ! grep -q "Codex 中文报告规则" "$file"; then
        cat >> "$file" <<'EOF'

## Codex 中文报告规则

所有生成报告、摘要、建议和面向用户的分析都必须使用中文。必须保留英文产品名、文件标准、API、爬虫名、平台名或专业技术名词时，在首次出现处添加中文括注，例如 `GEO（生成式引擎优化）`、`llms.txt（大模型说明文件）`、`Schema（结构化数据）`。
EOF
    fi
}

patch_installed_text_refs() {
    local file="$1"
    perl -0pi -e 's#Claude Code CLI#Codex CLI#g' "$file"
    perl -0pi -e 's#Claude Code#Codex#g' "$file"
    perl -0pi -e 's#WebFetch#web-access or HTTP fetch#g' "$file"
    perl -0pi -e 's#~/.claude#~/.codex#g' "$file"
}

main() {
    echo ""
    echo "GEO-SEO Codex Skill Installer"
    echo "============================="
    echo ""

    mkdir -p "$TEMP_DIR" "$SKILLS_DIR"

    print_info "Checking prerequisites"
    command -v git >/dev/null || { print_error "git is required"; exit 1; }
    command -v codex >/dev/null || { print_error "codex CLI is required"; exit 1; }

    PYTHON_CMD=""
    USE_UV_VENV=0
    for candidate in python3.13 python3.12 python3.11 python3.10 python3 python; do
        if command -v "$candidate" >/dev/null; then
            if "$candidate" - <<'PY' >/dev/null 2>&1
import ensurepip
import sys
raise SystemExit(0 if sys.version_info >= (3, 8) else 1)
PY
            then
                PYTHON_CMD="$candidate"
                break
            fi
            if [ -z "$PYTHON_CMD" ]; then
                PYTHON_CMD="$candidate"
            fi
        fi
    done
    if [ -z "$PYTHON_CMD" ]; then
        print_error "Python 3.8+ is required"
        exit 1
    fi
    if ! "$PYTHON_CMD" - <<'PY' >/dev/null 2>&1
import ensurepip
PY
    then
        if command -v uv >/dev/null; then
            USE_UV_VENV=1
            print_warning "Python ensurepip is unavailable; using uv to create the venv"
        else
            print_error "Python venv support is unavailable and uv was not found"
            exit 1
        fi
    fi
    print_success "Python found: $($PYTHON_CMD --version)"
    print_success "Codex found: $(codex --version)"

    print_info "Resolving source directory"
    SCRIPT_DIR=""
    if [ -n "${BASH_SOURCE[0]:-}" ] && [ "${BASH_SOURCE[0]}" != "bash" ]; then
        SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)" || true
    fi

    if [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/codex/geo/SKILL.md" ]; then
        SOURCE_DIR="$SCRIPT_DIR"
        print_success "Using local checkout: $SOURCE_DIR"
    else
        print_info "Cloning upstream"
        git clone --depth 1 "$REPO_URL" "$TEMP_DIR/repo"
        SOURCE_DIR="$TEMP_DIR/repo"
    fi

    if [ -d "$INSTALL_DIR" ]; then
        mkdir -p "$BACKUP_DIR"
        mv "$INSTALL_DIR" "$BACKUP_DIR/previous-geo"
        print_warning "Existing geo skill moved to $BACKUP_DIR/previous-geo"
    fi
    mkdir -p "$INSTALL_DIR"

    print_info "Installing Codex main skill"
    copy_dir_contents "$SOURCE_DIR/codex/geo" "$INSTALL_DIR"
    copy_dir_contents "$SOURCE_DIR/scripts" "$INSTALL_DIR/scripts"
    copy_dir_contents "$SOURCE_DIR/schema" "$INSTALL_DIR/schema"
    copy_dir_contents "$SOURCE_DIR/templates" "$INSTALL_DIR/templates"
    copy_dir_contents "$SOURCE_DIR/agents" "$INSTALL_DIR/agents"
    [ -f "$SOURCE_DIR/docs/codex-port-plan.md" ] && cp "$SOURCE_DIR/docs/codex-port-plan.md" "$INSTALL_DIR/codex-port-plan.md"
    [ -f "$SOURCE_DIR/requirements.txt" ] && cp "$SOURCE_DIR/requirements.txt" "$INSTALL_DIR/requirements.txt"
    print_success "Main skill installed at $INSTALL_DIR"

    print_info "Installing focused sub-skills"
    SKILL_COUNT=0
    for skill_dir in "$SOURCE_DIR"/skills/geo-*; do
        [ -d "$skill_dir" ] || continue
        skill_name="$(basename "$skill_dir")"
        target_dir="${SKILLS_DIR}/${skill_name}"
        if [ -d "$target_dir" ]; then
            mkdir -p "$BACKUP_DIR/previous-subskills"
            mv "$target_dir" "$BACKUP_DIR/previous-subskills/${skill_name}"
        fi
        copy_dir_contents "$skill_dir" "$target_dir"
        SKILL_COUNT=$((SKILL_COUNT + 1))
    done
    if [ -d "$SOURCE_DIR/codex/geo-update" ]; then
        copy_dir_contents "$SOURCE_DIR/codex/geo-update" "$SKILLS_DIR/geo-update"
    fi
    print_success "$SKILL_COUNT sub-skill(s) installed"

    print_info "Patching installed markdown references"
    PATCH_COUNT=0
    while IFS= read -r md; do
        patch_markdown "$md"
        PATCH_COUNT=$((PATCH_COUNT + 1))
    done < <(
        find "$INSTALL_DIR" -type f -name '*.md'
        for skill_dir in "$SOURCE_DIR"/skills/geo-*; do
            [ -d "$skill_dir" ] || continue
            find "$SKILLS_DIR/$(basename "$skill_dir")" -maxdepth 2 -type f -name '*.md'
        done
    )
    print_success "$PATCH_COUNT markdown file(s) patched"

    print_info "Patching installed script text references"
    SCRIPT_REF_COUNT=0
    while IFS= read -r text_file; do
        patch_installed_text_refs "$text_file"
        SCRIPT_REF_COUNT=$((SCRIPT_REF_COUNT + 1))
    done < <(find "$INSTALL_DIR/scripts" -type f -name '*.py')
    print_success "$SCRIPT_REF_COUNT script file(s) patched"

    print_info "Creating isolated Python environment"
    if [ -d "$VENV_DIR" ]; then
        mkdir -p "$BACKUP_DIR"
        mv "$VENV_DIR" "$BACKUP_DIR/previous-venv"
        print_warning "Existing venv moved to $BACKUP_DIR/previous-venv"
    fi
    if [ "$USE_UV_VENV" = "1" ]; then
        uv venv --python "$PYTHON_CMD" "$VENV_DIR" --quiet
        uv pip install --python "$VENV_PY" -r "$SOURCE_DIR/requirements.txt" --quiet
    else
        "$PYTHON_CMD" -m venv "$VENV_DIR"
        "$VENV_PY" -m pip install --upgrade pip --quiet
        "$VENV_PY" -m pip install -r "$SOURCE_DIR/requirements.txt" --quiet
    fi
    print_success "Dependencies installed into $VENV_DIR"

    print_info "Pinning script shebangs to venv interpreter"
    SCRIPT_COUNT=0
    while IFS= read -r py; do
        perl -i -pe "if (\$. == 1) { \$_ = qq(#!${VENV_PY}\\n) }" "$py"
        chmod +x "$py"
        SCRIPT_COUNT=$((SCRIPT_COUNT + 1))
    done < <(find "$INSTALL_DIR/scripts" -type f -name '*.py')
    print_success "$SCRIPT_COUNT Python script(s) made executable"

    print_info "Verifying installation"
    test -f "$INSTALL_DIR/SKILL.md"
    test -x "$INSTALL_DIR/scripts/geo_cli.py"
    test -d "$INSTALL_DIR/schema"
    test -d "$INSTALL_DIR/templates"
    test -x "$VENV_PY"
    AGENT_COUNT="$(find "$INSTALL_DIR/agents" -maxdepth 1 -type f -name 'geo-*.md' | wc -l | tr -d ' ')"
    if [ "$AGENT_COUNT" != "5" ]; then
        print_error "Expected 5 installed agent rubric files, found $AGENT_COUNT"
        exit 1
    fi
    print_success "File verification passed"

    echo ""
    echo "Install complete."
    echo "Installed to: $INSTALL_DIR"
    echo "Backup/temp directory: $BACKUP_DIR"
    echo ""
    echo "Verify Codex visibility with:"
    echo "  codex debug prompt-input 'geo audit https://example.com'"
    echo ""
    echo "Run a smoke command with:"
    echo "  $INSTALL_DIR/scripts/geo_cli.py quick https://example.com"
    echo ""
}

main "$@"
