#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# Cloudflare Workers Builds does not guarantee Rust is pre-installed.
# Install an isolated user toolchain in the ephemeral Cloudflare build container.
export RUSTUP_HOME="${RUSTUP_HOME:-$HOME/.rustup}"
export CARGO_HOME="${CARGO_HOME:-$HOME/.cargo}"
export PATH="$CARGO_HOME/bin:$PATH"
if ! command -v rustup >/dev/null 2>&1; then
  curl --fail --location --silent --show-error --proto '=https' --tlsv1.2 \
    https://sh.rustup.rs -o /tmp/saiga-rustup-init.sh
  sh /tmp/saiga-rustup-init.sh -y --profile minimal --default-toolchain stable --no-modify-path
fi
rustup toolchain install stable --profile minimal
rustup default stable
rustup target add wasm32-unknown-unknown
rustc --version
cargo --version

# Match wasm-bindgen CLI to the crate's pinned version when a lockfile exists.
cargo install wasm-bindgen-cli --locked
cargo build --release -p saiga-poc-browser --target wasm32-unknown-unknown
mkdir -p dist/pkg
wasm-bindgen target/wasm32-unknown-unknown/release/saiga_poc_browser.wasm --target web --out-dir dist/pkg
if [[ -n "${SAIGA_POC_PUBLISH_URL:-}" && -n "${SAIGA_POC_PUBLISH_TOKEN:-}" ]]; then
  curl --fail --silent --show-error --retry 3 \
    -H "Authorization: Bearer $SAIGA_POC_PUBLISH_TOKEN" \
    "$SAIGA_POC_PUBLISH_URL" -o content-published.json
else
  cp content.json content-published.json
fi
cargo run --release -p saiga-poc-generator -- content-published.json dist
test -s dist/index.html
test -s dist/destinations/index.html
test -s dist/pkg/saiga_poc_browser_bg.wasm
