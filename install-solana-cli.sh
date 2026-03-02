#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# Solana CLI installer for Linux Mint 22.3 (and Debian/Ubuntu)
# Uses official Agave install: https://docs.anza.xyz/cli/install/
# Installs: solana, solana-keygen, etc. (CLI only; no Rust/Anchor/Node)
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

CHANNEL="${SOLANA_INSTALL_CHANNEL:-stable}"
# Optional: pin version, e.g. v3.1.9
VERSION="${SOLANA_INSTALL_VERSION:-}"

echo "Solana CLI installer (channel: ${CHANNEL}${VERSION:+, version: ${VERSION}})"
echo "Target: Linux Mint 22.3 / Debian / Ubuntu"
echo ""

# Optional: install deps for systems that might be missing curl
if ! command -v curl &>/dev/null; then
    echo "Installing curl..."
    sudo apt-get update -qq
    sudo apt-get install -y curl
fi

# Agave install (prebuilt binaries; no build deps required)
if [[ -n "$VERSION" ]]; then
    INSTALL_URL="https://release.anza.xyz/${VERSION}/install"
else
    INSTALL_URL="https://release.anza.xyz/${CHANNEL}/install"
fi

echo "Downloading and running Agave install from: ${INSTALL_URL}"
sh -c "$(curl -sSfL "$INSTALL_URL")"

# Ensure PATH includes Solana bin (install script usually adds to ~/.profile or suggests export)
SOLANA_BIN_DIR="${HOME}/.local/share/solana/install/active_release/bin"
if [[ -d "$SOLANA_BIN_DIR" ]]; then
    export PATH="$SOLANA_BIN_DIR:$PATH"
    if ! grep -q "solana/install/active_release/bin" "${HOME}/.profile" 2>/dev/null; then
        echo ""
        echo "Add Solana CLI to your PATH permanently by running:"
        echo "  echo 'export PATH=\"\$HOME/.local/share/solana/install/active_release/bin:\$PATH\"' >> ~/.profile"
        echo "  source ~/.profile"
    fi
fi

# Verify
if command -v solana &>/dev/null; then
    echo ""
    echo "Solana CLI installed successfully:"
    solana --version
    echo ""
    echo "Keygen (for miner keypair):  solana-keygen new -o miner.json"
    echo "Pubkey from keypair:         solana-keygen pubkey miner.json"
else
    echo "Install finished but 'solana' not in PATH. Add the path shown above and run: solana --version"
    exit 1
fi
