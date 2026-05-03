#!/bin/bash
# ============================================================================
# Nova Agent Installer
# ============================================================================
# Installation script for Linux and macOS.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/eidolonlabs-ai/nova-agent/main/scripts/install.sh | bash
#
# Or with options:
#   curl -fsSL ... | bash -s -- --skip-setup
#
# ============================================================================

set -e
set -o pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

# Configuration
REPO_URL_SSH="git@github.com:eidolonlabs-ai/nova-agent.git"
REPO_URL_HTTPS="https://github.com/eidolonlabs-ai/nova-agent.git"
NOVA_HOME="${NOVA_HOME:-$HOME/.nova}"
INSTALL_DIR=""
INSTALL_DIR_EXPLICIT=false
INSTALL_DIR_CREATED_BY_SCRIPT=false
PYTHON_VERSION="3.12"
BRANCH="main"

# Detect non-interactive mode
if [ -t 0 ]; then
    IS_INTERACTIVE=true
else
    IS_INTERACTIVE=false
fi

# Options
RUN_SETUP=true

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-setup)
            RUN_SETUP=false
            shift
            ;;
        --branch)
            BRANCH="$2"
            shift 2
            ;;
        --dir)
            INSTALL_DIR="$2"
            INSTALL_DIR_EXPLICIT=true
            shift 2
            ;;
        --nova-home)
            NOVA_HOME="$2"
            shift 2
            ;;
        -h|--help)
            echo "Nova Agent Installer"
            echo ""
            echo "Usage: install.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --skip-setup   Skip interactive setup wizard"
            echo "  --branch NAME  Git branch to install (default: main)"
            echo "  --dir PATH     Installation directory (default: ~/.nova/nova-agent)"
            echo "  --nova-home PATH  Data directory (default: ~/.nova)"
            echo "  -h, --help     Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Resolve install directory
if [ "$INSTALL_DIR_EXPLICIT" = true ]; then
    : # user specified
elif [ -n "${NOVA_INSTALL_DIR:-}" ]; then
    INSTALL_DIR="$NOVA_INSTALL_DIR"
else
    INSTALL_DIR="$NOVA_HOME/nova-agent"
fi

# ============================================================================
# Helper functions
# ============================================================================

print_banner() {
    echo ""
    echo -e "${MAGENTA}${BOLD}"
    echo "┌─────────────────────────────────────────────────────────┐"
    echo "│              ✦ Nova Agent Installer                     │"
    echo "├─────────────────────────────────────────────────────────┤"
    echo "│  A minimalist personal AI agent by Eidolon Labs LLC.    │"
    echo "─────────────────────────────────────────────────────────┘"
    echo -e "${NC}"
}

log_info() {
    echo -e "${CYAN}→${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

prompt_yes_no() {
    local question="$1"
    local default="${2:-yes}"
    local prompt_suffix
    local answer=""

    case "$default" in
        [yY]|[yY][eE][sS]|[tT][rR][uU][eE]|1) prompt_suffix="[Y/n]" ;;
        *) prompt_suffix="[y/N]" ;;
    esac

    if [ "$IS_INTERACTIVE" = true ]; then
        read -r -p "$question $prompt_suffix " answer || answer=""
    elif [ -r /dev/tty ] && [ -w /dev/tty ]; then
        printf "%s %s " "$question" "$prompt_suffix" > /dev/tty
        IFS= read -r answer < /dev/tty || answer=""
    else
        answer=""
    fi

    answer="${answer#"${answer%%[![:space:]]*}"}"
    answer="${answer%"${answer##*[![:space:]]}"}"

    if [ -z "$answer" ]; then
        case "$default" in
            [yY]|[yY][eE][sS]|[tT][rR][uU][eE]|1) return 0 ;;
            *) return 1 ;;
        esac
    fi

    case "$answer" in
        [yY]|[yY][eE][sS]) return 0 ;;
        *) return 1 ;;
    esac
}

# ============================================================================
# System detection
# ============================================================================

detect_os() {
    case "$(uname -s)" in
        Linux*)
            OS="linux"
            if [ -f /etc/os-release ]; then
                . /etc/os-release
                DISTRO="$ID"
            else
                DISTRO="unknown"
            fi
            ;;
        Darwin*)
            OS="macos"
            DISTRO="macos"
            ;;
        CYGWIN*|MINGW*|MSYS*)
            OS="windows"
            DISTRO="windows"
            log_error "Windows detected. Please use WSL or install manually."
            exit 1
            ;;
        *)
            OS="unknown"
            DISTRO="unknown"
            log_warn "Unknown operating system"
            ;;
    esac

    log_success "Detected: $OS ($DISTRO)"
}

# ============================================================================
# Dependency checks
# ============================================================================

check_python() {
    log_info "Checking Python $PYTHON_VERSION..."

    # Try python3 first, then python
    for cmd in python3 python; do
        if command -v "$cmd" &> /dev/null; then
            local ver
            ver=$("$cmd" --version 2>/dev/null)
            if "$cmd" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)' 2>/dev/null; then
                PYTHON_PATH="$(command -v "$cmd")"
                log_success "Python found: $ver"
                return 0
            fi
        fi
    done

    log_error "Python $PYTHON_VERSION or newer not found"
    log_info "Install Python $PYTHON_VERSION+ from https://www.python.org/downloads/"

    case "$OS" in
        macos)
            log_info "  brew install python@3.12"
            ;;
        linux)
            case "$DISTRO" in
                ubuntu|debian) log_info "  sudo apt install python3.12 python3.12-venv" ;;
                fedora)        log_info "  sudo dnf install python3.12" ;;
                arch)          log_info "  sudo pacman -S python" ;;
                *)             log_info "  Use your package manager" ;;
            esac
            ;;
    esac

    exit 1
}

check_git() {
    log_info "Checking Git..."

    if command -v git &> /dev/null; then
        GIT_VERSION=$(git --version | awk '{print $3}')
        log_success "Git $GIT_VERSION found"
        return 0
    fi

    log_error "Git not found"
    log_info "Please install Git:"

    case "$OS" in
        linux)
            case "$DISTRO" in
                ubuntu|debian) log_info "  sudo apt install git" ;;
                fedora)        log_info "  sudo dnf install git" ;;
                arch)          log_info "  sudo pacman -S git" ;;
                *)             log_info "  Use your package manager" ;;
            esac
            ;;
        macos)
            log_info "  xcode-select --install"
            log_info "  Or: brew install git"
            ;;
    esac

    exit 1
}

# ============================================================================
# Installation
# ============================================================================

clone_repo() {
    log_info "Installing to $INSTALL_DIR..."

    if [ -d "$INSTALL_DIR" ]; then
        if [ -d "$INSTALL_DIR/.git" ]; then
            log_info "Existing installation found, updating..."
            cd "$INSTALL_DIR"

            local autostash_ref=""
            if [ -n "$(git status --porcelain)" ]; then
                local stash_name
                stash_name="nova-install-autostash-$(date -u +%Y%m%d-%H%M%S)"
                log_info "Local changes detected, stashing before update..."
                git stash push --include-untracked -m "$stash_name"
                autostash_ref="$(git rev-parse --verify refs/stash)"
            fi

            git fetch origin
            git checkout "$BRANCH"
            git pull --ff-only origin "$BRANCH"

            if [ -n "$autostash_ref" ]; then
                local restore_now="yes"
                if [ -t 0 ] && [ -t 1 ]; then
                    echo
                    log_warn "Local changes were stashed before updating."
                    printf "Restore local changes now? [Y/n] "
                    read -r restore_answer
                    case "$restore_answer" in
                        ""|y|Y|yes|YES|Yes) restore_now="yes" ;;
                        *) restore_now="no" ;;
                    esac
                fi

                if [ "$restore_now" = "yes" ]; then
                    log_info "Restoring local changes..."
                    if git stash apply "$autostash_ref"; then
                        git stash drop "$autostash_ref" >/dev/null
                        log_warn "Local changes restored on top of updated codebase."
                    else
                        log_error "Update succeeded, but restoring local changes failed."
                        log_info "Your changes are preserved in git stash."
                        log_info "Restore manually: git stash apply $autostash_ref"
                        exit 1
                    fi
                else
                    log_info "Skipped restoring local changes (preserved in git stash)."
                fi
            fi
        else
            log_error "Directory exists but is not a git repository: $INSTALL_DIR"
            log_info "Remove it or choose a different directory with --dir"
            exit 1
        fi
    else
        log_info "Trying SSH clone..."
        local ssh_err
        ssh_err=$(mktemp)
        if GIT_SSH_COMMAND="ssh -o BatchMode=yes -o ConnectTimeout=5" \
           git clone --branch "$BRANCH" "$REPO_URL_SSH" "$INSTALL_DIR" 2>"$ssh_err"; then
            log_success "Cloned via SSH"
            rm -f "$ssh_err"
        else
            # Only remove the directory if this script created it
            if [ "$INSTALL_DIR_CREATED_BY_SCRIPT" = true ]; then
                rm -rf "$INSTALL_DIR" 2>/dev/null
            fi
            local ssh_reason
            ssh_reason=$(cat "$ssh_err" 2>/dev/null | tail -1)
            rm -f "$ssh_err"
            if [ -n "$ssh_reason" ]; then
                log_info "SSH clone failed: $ssh_reason"
            fi
            log_info "Trying HTTPS..."
            if git clone --branch "$BRANCH" "$REPO_URL_HTTPS" "$INSTALL_DIR"; then
                log_success "Cloned via HTTPS"
            else
                log_error "Failed to clone repository"
                exit 1
            fi
        fi
    fi

    INSTALL_DIR_CREATED_BY_SCRIPT=true

    cd "$INSTALL_DIR"
    log_success "Repository ready"
}

setup_venv() {
    log_info "Creating virtual environment..."

    if [ -d "venv" ]; then
        log_info "Virtual environment already exists, recreating..."
        rm -rf venv
    fi

    "$PYTHON_PATH" -m venv venv
    log_success "Virtual environment ready ($("./venv/bin/python" --version 2>/dev/null))"
}

install_deps() {
    log_info "Installing dependencies..."

    ./venv/bin/pip install --upgrade pip setuptools wheel >/dev/null 2>&1
    if ./venv/bin/pip install -e ".[dev]"; then
        log_success "Dependencies installed"
    else
        log_error "Package installation failed"
        exit 1
    fi
}

setup_path() {
    log_info "Setting up nova command..."

    NOVA_BIN="$INSTALL_DIR/venv/bin/nova"

    if [ ! -x "$NOVA_BIN" ]; then
        log_warn "nova entry point not found at $NOVA_BIN"
        log_info "Try: cd $INSTALL_DIR && ./venv/bin/pip install -e ."
        return 0
    fi

    local command_link_dir="$HOME/.local/bin"
    mkdir -p "$command_link_dir"
    ln -sf "$NOVA_BIN" "$command_link_dir/nova"
    log_success "Symlinked nova → ~/.local/bin/nova"

    # Check if ~/.local/bin is on PATH
    if ! echo "$PATH" | tr ':' '\n' | grep -q "^$command_link_dir$"; then
        SHELL_CONFIGS=()
        LOGIN_SHELL="$(basename "${SHELL:-/bin/bash}")"
        case "$LOGIN_SHELL" in
            zsh)
                [ -f "$HOME/.zshrc" ] && SHELL_CONFIGS+=("$HOME/.zshrc")
                [ -f "$HOME/.zprofile" ] && SHELL_CONFIGS+=("$HOME/.zprofile")
                if [ ${#SHELL_CONFIGS[@]} -eq 0 ]; then
                    touch "$HOME/.zshrc"
                    SHELL_CONFIGS+=("$HOME/.zshrc")
                fi
                ;;
            bash)
                [ -f "$HOME/.bashrc" ] && SHELL_CONFIGS+=("$HOME/.bashrc")
                [ -f "$HOME/.bash_profile" ] && SHELL_CONFIGS+=("$HOME/.bash_profile")
                ;;
            *)
                [ -f "$HOME/.bashrc" ] && SHELL_CONFIGS+=("$HOME/.bashrc")
                [ -f "$HOME/.zshrc" ] && SHELL_CONFIGS+=("$HOME/.zshrc")
                ;;
        esac
        [ -f "$HOME/.profile" ] && SHELL_CONFIGS+=("$HOME/.profile")

        PATH_LINE='export PATH="$HOME/.local/bin:$PATH"'

        if [ "$IS_INTERACTIVE" = true ] && [ ${#SHELL_CONFIGS[@]} -gt 0 ]; then
            echo ""
            log_info "~/.local/bin is not on your PATH."
            log_info "Nova needs to add it to your shell config(s):"
            for sc in "${SHELL_CONFIGS[@]}"; do
                log_info "  $sc"
            done
            if prompt_yes_no "Add ~/.local/bin to PATH in these files?" "yes"; then
                for SHELL_CONFIG in "${SHELL_CONFIGS[@]}"; do
                    if ! grep -v '^[[:space:]]*#' "$SHELL_CONFIG" 2>/dev/null | grep -qE 'PATH=.*\.local/bin'; then
                        echo "" >> "$SHELL_CONFIG"
                        echo "# Nova Agent — ensure ~/.local/bin is on PATH" >> "$SHELL_CONFIG"
                        echo "$PATH_LINE" >> "$SHELL_CONFIG"
                        log_success "Added ~/.local/bin to PATH in $SHELL_CONFIG"
                    fi
                done
            else
                log_warn "Skipped PATH modification."
                log_info "Add manually: $PATH_LINE"
            fi
        else
            log_warn "Non-interactive mode: skipping automatic PATH modification."
            log_info "After installation, add this to your shell config:"
            log_info "  $PATH_LINE"
        fi
    else
        log_info "~/.local/bin already on PATH"
    fi

    export PATH="$command_link_dir:$PATH"
    log_success "nova command ready"
}

copy_config_templates() {
    log_info "Setting up configuration files..."

    mkdir -p "$NOVA_HOME"/{skills,sessions}

    # Copy SOUL.md template
    if [ ! -f "$NOVA_HOME/SOUL.md" ]; then
        if [ -f "$INSTALL_DIR/config/SOUL.md.example" ]; then
            cp "$INSTALL_DIR/config/SOUL.md.example" "$NOVA_HOME/SOUL.md"
            log_success "Created $NOVA_HOME/SOUL.md from template"
        fi
    else
        log_info "$NOVA_HOME/SOUL.md already exists, keeping it"
    fi

    # Copy skills
    if [ -d "$INSTALL_DIR/config/skills" ] && [ ! -d "$NOVA_HOME/skills" ] || [ -z "$(ls -A "$NOVA_HOME/skills" 2>/dev/null)" ]; then
        cp -r "$INSTALL_DIR/config/skills/"* "$NOVA_HOME/skills/" 2>/dev/null || true
        log_success "Copied starter skills to $NOVA_HOME/skills/"
    fi

    # Copy config.yaml template if no global config exists
    if [ ! -f "$NOVA_HOME/config.yaml" ]; then
        if [ -f "$INSTALL_DIR/config.yaml.example" ]; then
            cp "$INSTALL_DIR/config.yaml.example" "$NOVA_HOME/config.yaml"
            log_success "Created $NOVA_HOME/config.yaml from template"
        fi
    else
        log_info "$NOVA_HOME/config.yaml already exists, keeping it"
    fi
}

run_setup_wizard() {
    if [ "$RUN_SETUP" = false ]; then
        log_info "Skipping setup wizard (--skip-setup)"
        return 0
    fi

    echo ""
    log_info "Running setup wizard..."
    echo ""

    # Run nova setup if available
    if command -v nova &> /dev/null; then
        nova setup
    else
        log_warn "nova command not on PATH yet"
        log_info "Run 'nova setup' after restarting your shell, or:"
        log_info "  cd $INSTALL_DIR && source venv/bin/activate && nova setup"
    fi
}

print_completion() {
    echo ""
    echo -e "${GREEN}${BOLD}"
    echo "┌─────────────────────────────────────────────────────────┐"
    echo "│                   ✦ Installation Complete               │"
    echo "├─────────────────────────────────────────────────────────┤"
    echo "│                                                         │"
    echo "│  Next steps:                                            │"
    echo "│    1. Restart your shell (or: source ~/.zshrc)          │"
    echo "│    2. Run: nova setup                                   │"
    echo "│    3. Run: nova chat                                    │"
    echo "│                                                         │"
    echo "│  Update Nova:                                           │"
    echo "│    nova update                                          │"
    echo "│                                                         │"
    echo "│  Docs: https://github.com/eidolonlabs-ai/nova-agent     │"
    echo "│                                                         │"
    echo "└─────────────────────────────────────────────────────────┘"
    echo -e "${NC}"
}

# ============================================================================
# Main
# ============================================================================

print_banner
detect_os
check_python
check_git
clone_repo
setup_venv
install_deps
setup_path
copy_config_templates
run_setup_wizard
print_completion
