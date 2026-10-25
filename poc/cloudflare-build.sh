#!/usr/bin/env bash
set -euo pipefail
# Runs on Cloudflare Workers Builds, never GitHub Actions or a personal device.
cd "$(dirname "$0")"
rustup target add wasm32-unknown-unknown
cargo install wasm-bindgen-cli --locked
cargo build --release -p saiga-poc-browser --target wasm32-unknown-unknown
mkdir -p dist/pkg
wasm-bindgen ../target/wasm32-unknown-unknown/release/saiga_poc_browser.wasm --target web --out-dir dist/pkg
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
