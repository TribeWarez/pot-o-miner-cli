#!/bin/bash
# Manual Solana installation script for Docker containers
# Run this inside the Docker container if automatic installation fails

set -e

echo "Installing Solana CLI manually..."

# Try multiple methods
METHODS=(
    "curl -sSfL https://release.solana.com/stable/install | sh"
    "curl -k -sSfL https://release.solana.com/stable/install | sh"
    "wget -qO- https://release.solana.com/stable/install | sh"
)

for method in "${METHODS[@]}"; do
    echo "Trying: $method"
    if eval "$method"; then
        export PATH="/root/.local/share/solana/install/active_release/bin:$PATH"
        if solana --version; then
            echo "✅ Solana installed successfully!"
            exit 0
        fi
    fi
done

# Fallback: Download binary directly from GitHub
echo "Trying direct binary download..."
SOLANA_VERSION="1.18.26"
ARCH="x86_64-unknown-linux-gnu"

mkdir -p /root/.local/share/solana/install/active_release/bin

# Try downloading from GitHub releases
if curl -L -o /tmp/solana.tar.bz2 \
    "https://github.com/anza-xyz/agave/releases/download/v${SOLANA_VERSION}/solana-release-${ARCH}.tar.bz2" 2>/dev/null; then
    tar -xjf /tmp/solana.tar.bz2 -C /root/.local/share/solana/install/active_release --strip-components=1
    export PATH="/root/.local/share/solana/install/active_release/bin:$PATH"
    if solana --version; then
        echo "✅ Solana installed from GitHub!"
        exit 0
    fi
fi

echo "❌ Failed to install Solana automatically"
echo "Please install manually or use system Solana installation"
exit 1
