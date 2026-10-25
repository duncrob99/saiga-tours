#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export PATH="$HOME/.cargo/bin:$PATH"
export CARGO_TARGET_DIR="${SAIGA_POC_TARGET_DIR:-$HOME/.cache/saiga-poc/cargo-target}"
mkdir -p "$CARGO_TARGET_DIR" "$HOME/.cache/saiga-poc"
if ! command -v cargo >/dev/null; then
  curl --fail --location --silent --show-error --proto '=https' --tlsv1.2 https://sh.rustup.rs -o /tmp/saiga-rustup-init.sh
  sh /tmp/saiga-rustup-init.sh -y --profile minimal --no-modify-path
fi
rustup target add wasm32-unknown-unknown
echo "SAIGA dev validation — $(date -Is)"
cargo --version
echo "Checking browser"; cargo check -p saiga-poc-browser --target wasm32-unknown-unknown
echo "Checking generator"; cargo check -p saiga-poc-generator
echo "Checking admin"; cargo check -p saiga-poc-admin --target wasm32-unknown-unknown
echo "Running host-side test suite"; cargo test -p saiga-poc-generator
echo "Building generator (incremental, persistent cache)"; cargo build -p saiga-poc-generator
echo "SAIGA_DEV_CHECK_SUCCESS"
