#!/usr/bin/env bash
#
# DNS Science CoreDNS Manager Installer
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/straticus1/dnsscience-coredns-manager/main/install.sh | bash
#
# Or with options:
#   curl -fsSL https://raw.githubusercontent.com/straticus1/dnsscience-coredns-manager/main/install.sh | bash -s -- --prefix /opt/dnsscience
#
# Copyright (c) 2025 After Dark Systems, LLC
# License: Apache-2.0

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://github.com/straticus1/dnsscience-coredns-manager"
REPO_NAME="dnsscience-coredns-manager"
MIN_PYTHON_VERSION="3.11"
DEFAULT_PREFIX="$HOME/.local"

# Parse arguments
PREFIX="${DEFAULT_PREFIX}"
INSTALL_METHOD="pip"
DEV_MODE=false
SKIP_DEPS=false

print_banner() {
    echo -e "${PURPLE}"
    cat << 'EOF'
    ____  _   _______   _____      _
   / __ \/ | / / ___/  / ___/_____(_)__  ____  _________
  / / / /  |/ /\__ \   \__ \/ ___/ / _ \/ __ \/ ___/ _ \
 / /_/ / /|  /___/ /  ___/ / /__/ /  __/ / / / /__/  __/
/_____/_/ |_//____/  /____/\___/_/\___/_/ /_/\___/\___/

           CoreDNS Manager Installer
EOF
    echo -e "${NC}"
    echo -e "${CYAN}Enterprise-grade DNS resolver management${NC}"
    echo ""
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_command() {
    command -v "$1" &> /dev/null
}

version_gte() {
    # Returns 0 if $1 >= $2
    printf '%s\n%s\n' "$2" "$1" | sort -V -C
}

get_python_version() {
    "$1" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")'
}

find_python() {
    local candidates=("python3.12" "python3.11" "python3" "python")

    for cmd in "${candidates[@]}"; do
        if check_command "$cmd"; then
            local version
            version=$(get_python_version "$cmd" 2>/dev/null || echo "0.0")
            if version_gte "$version" "$MIN_PYTHON_VERSION"; then
                echo "$cmd"
                return 0
            fi
        fi
    done
    return 1
}

check_dependencies() {
    log_info "Checking dependencies..."

    local missing=()

    # Check for git
    if ! check_command git; then
        missing+=("git")
    else
        log_success "git found"
    fi

    # Check for Python
    if ! PYTHON_CMD=$(find_python); then
        missing+=("python >= ${MIN_PYTHON_VERSION}")
    else
        local py_version
        py_version=$(get_python_version "$PYTHON_CMD")
        log_success "Python ${py_version} found (${PYTHON_CMD})"
    fi

    # Check for pip
    if ! "$PYTHON_CMD" -m pip --version &> /dev/null; then
        missing+=("pip")
    else
        log_success "pip found"
    fi

    # Optional: Check for CoreDNS
    if check_command coredns; then
        log_success "CoreDNS found"
    else
        log_warn "CoreDNS not found (optional - install separately for full functionality)"
    fi

    # Optional: Check for Unbound
    if check_command unbound; then
        log_success "Unbound found"
    else
        log_warn "Unbound not found (optional - install separately for migration features)"
    fi

    # Optional: Check for kubectl
    if check_command kubectl; then
        log_success "kubectl found"
    else
        log_warn "kubectl not found (optional - needed for Kubernetes features)"
    fi

    if [ ${#missing[@]} -gt 0 ]; then
        log_error "Missing required dependencies:"
        for dep in "${missing[@]}"; do
            echo "  - $dep"
        done
        echo ""
        echo "Please install missing dependencies and try again."
        exit 1
    fi

    echo ""
}

install_from_pip() {
    log_info "Installing via pip..."

    # Create virtual environment if not in one
    if [ -z "${VIRTUAL_ENV:-}" ]; then
        local venv_path="${PREFIX}/share/dnsscience-coredns-manager/venv"

        if [ ! -d "$venv_path" ]; then
            log_info "Creating virtual environment at ${venv_path}..."
            mkdir -p "$(dirname "$venv_path")"
            "$PYTHON_CMD" -m venv "$venv_path"
        fi

        # shellcheck source=/dev/null
        source "${venv_path}/bin/activate"
        log_success "Virtual environment activated"
    fi

    # Upgrade pip
    pip install --upgrade pip

    # Install the package
    if [ "$DEV_MODE" = true ]; then
        log_info "Installing in development mode..."
        pip install -e "git+${REPO_URL}.git#egg=dnsscience-coredns-manager[dev]"
    else
        pip install "git+${REPO_URL}.git"
    fi

    log_success "Package installed successfully"
}

install_from_source() {
    log_info "Installing from source..."

    local install_dir="${PREFIX}/share/dnsscience-coredns-manager"

    # Clone or update repository
    if [ -d "${install_dir}/repo" ]; then
        log_info "Updating existing installation..."
        cd "${install_dir}/repo"
        git pull origin main
    else
        log_info "Cloning repository..."
        mkdir -p "$install_dir"
        git clone "$REPO_URL" "${install_dir}/repo"
        cd "${install_dir}/repo"
    fi

    # Create virtual environment
    local venv_path="${install_dir}/venv"
    if [ ! -d "$venv_path" ]; then
        log_info "Creating virtual environment..."
        "$PYTHON_CMD" -m venv "$venv_path"
    fi

    # shellcheck source=/dev/null
    source "${venv_path}/bin/activate"

    # Upgrade pip
    pip install --upgrade pip

    # Install package
    if [ "$DEV_MODE" = true ]; then
        pip install -e ".[dev]"
    else
        pip install -e .
    fi

    log_success "Package installed from source"
}

create_symlinks() {
    log_info "Creating command symlinks..."

    local bin_dir="${PREFIX}/bin"
    local venv_bin="${PREFIX}/share/dnsscience-coredns-manager/venv/bin"

    mkdir -p "$bin_dir"

    # Create wrapper scripts
    for cmd in dnsctl dnsctl-api dnsctl-mcp; do
        local wrapper="${bin_dir}/${cmd}"
        cat > "$wrapper" << EOF
#!/usr/bin/env bash
# DNS Science CoreDNS Manager - ${cmd}
exec "${venv_bin}/${cmd}" "\$@"
EOF
        chmod +x "$wrapper"
        log_success "Created ${wrapper}"
    done
}

setup_completions() {
    log_info "Setting up shell completions..."

    local completions_dir="${PREFIX}/share/dnsscience-coredns-manager/completions"
    mkdir -p "$completions_dir"

    # Bash completions
    if [ -d "${PREFIX}/share/bash-completion/completions" ] || [ -d "/etc/bash_completion.d" ]; then
        log_info "Generating bash completions..."
        if check_command dnsctl; then
            dnsctl --show-completion bash > "${completions_dir}/dnsctl.bash" 2>/dev/null || true
        fi
    fi

    # Zsh completions
    if [ -d "${PREFIX}/share/zsh/site-functions" ]; then
        log_info "Generating zsh completions..."
        if check_command dnsctl; then
            dnsctl --show-completion zsh > "${completions_dir}/_dnsctl" 2>/dev/null || true
        fi
    fi

    # Fish completions
    if [ -d "${PREFIX}/share/fish/vendor_completions.d" ]; then
        log_info "Generating fish completions..."
        if check_command dnsctl; then
            dnsctl --show-completion fish > "${completions_dir}/dnsctl.fish" 2>/dev/null || true
        fi
    fi
}

print_post_install() {
    echo ""
    echo -e "${GREEN}=== Installation Complete ===${NC}"
    echo ""
    echo "Add the following to your shell profile (.bashrc, .zshrc, etc.):"
    echo ""
    echo -e "${CYAN}  export PATH=\"\${PATH}:${PREFIX}/bin\"${NC}"
    echo ""
    echo "Then reload your shell or run:"
    echo ""
    echo -e "${CYAN}  source ~/.bashrc  # or ~/.zshrc${NC}"
    echo ""
    echo -e "${PURPLE}Quick Start:${NC}"
    echo ""
    echo "  dnsctl --help           # Show available commands"
    echo "  dnsctl service status   # Check DNS resolver status"
    echo "  dnsctl query trace google.com  # Trace DNS resolution"
    echo ""
    echo -e "${BLUE}Documentation:${NC} https://docs.dnsscience.io/coredns-manager"
    echo -e "${BLUE}Support:${NC} https://github.com/straticus1/dnsscience-coredns-manager/issues"
    echo ""
}

usage() {
    cat << EOF
DNS Science CoreDNS Manager Installer

Usage: $0 [options]

Options:
    -h, --help          Show this help message
    -p, --prefix PATH   Installation prefix (default: ${DEFAULT_PREFIX})
    -s, --source        Install from source instead of pip
    -d, --dev           Install development dependencies
    --skip-deps         Skip dependency checking

Examples:
    # Install to default location
    curl -fsSL https://raw.githubusercontent.com/straticus1/dnsscience-coredns-manager/main/install.sh | bash

    # Install to custom location
    curl -fsSL ... | bash -s -- --prefix /opt/dnsscience

    # Install with development dependencies
    curl -fsSL ... | bash -s -- --dev
EOF
}

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                exit 0
                ;;
            -p|--prefix)
                PREFIX="$2"
                shift 2
                ;;
            -s|--source)
                INSTALL_METHOD="source"
                shift
                ;;
            -d|--dev)
                DEV_MODE=true
                shift
                ;;
            --skip-deps)
                SKIP_DEPS=true
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done

    print_banner

    log_info "Installation prefix: ${PREFIX}"
    log_info "Installation method: ${INSTALL_METHOD}"
    [ "$DEV_MODE" = true ] && log_info "Development mode: enabled"
    echo ""

    # Check dependencies
    if [ "$SKIP_DEPS" = false ]; then
        check_dependencies
    fi

    # Install
    if [ "$INSTALL_METHOD" = "source" ]; then
        install_from_source
    else
        install_from_pip
    fi

    # Create symlinks
    create_symlinks

    # Setup completions
    setup_completions

    # Print post-install instructions
    print_post_install
}

main "$@"
