#!/usr/bin/env bash
# OmniSim Universal CLI Standalone Installer
# Installs OmniSim in an isolated environment and links the CLI to your PATH.

set -euo pipefail

INSTALL_DIR="${HOME}/.local/share/omnisim"
BIN_DIR="${HOME}/.local/bin"
RELEASE_URL="https://github.com/Deeven-Seru/omnisim/releases/download/v1.0.0/omnisim_engine-1.0.0-py3-none-any.whl"

echo "=== Installing OmniSim CLI (v1.0.0) ==="

# Check Python availability (Python 3.10+)
PYTHON_BIN=""
for cmd in python3.12 python3.11 python3.10 python3; do
    if command -v "$cmd" >/dev/null 2>&1; then
        PYTHON_BIN=$(command -v "$cmd")
        break
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    echo "Error: Python 3.10+ is required but not found on your system." >&2
    exit 1
fi

echo "Using Python: $PYTHON_BIN"

# Create isolated installation directory
mkdir -p "$INSTALL_DIR" "$BIN_DIR"
rm -rf "$INSTALL_DIR/venv"
"$PYTHON_BIN" -m venv "$INSTALL_DIR/venv"

# Install wheel
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip >/dev/null
"$INSTALL_DIR/venv/bin/pip" install "$RELEASE_URL" >/dev/null

# Link CLI executable
ln -sf "$INSTALL_DIR/venv/bin/omnisim" "$BIN_DIR/omnisim"

echo "=== OmniSim successfully installed to $BIN_DIR/omnisim ==="

# PATH check
case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *)
        echo ""
        echo "Notice: $BIN_DIR is not in your PATH."
        echo "Add the following to your ~/.zshrc or ~/.bashrc:"
        echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
        echo ""
        ;;
esac

"$BIN_DIR/omnisim" --help >/dev/null 2>&1 || true
echo "Run 'omnisim --help' to get started."
