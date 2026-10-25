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

# Fail fast on source/type errors before optimized release compilation.
echo "== Checking browser WASM =="
cargo check -p saiga-poc-browser --target wasm32-unknown-unknown
echo "== Checking static page generator =="
cargo check -p saiga-poc-generator

# Match wasm-bindgen CLI to the crate's pinned version when a lockfile exists.
# Download the version-matched prebuilt CLI instead of compiling it for 2–3 minutes.
# The binary comes from the official wasm-bindgen release assets.
WASM_BINDGEN_VERSION=0.2.129
WASM_BINDGEN_ARCH=x86_64-unknown-linux-musl
WASM_BINDGEN_ARCHIVE="wasm-bindgen-${WASM_BINDGEN_VERSION}-${WASM_BINDGEN_ARCH}.tar.gz"
if curl --fail --location --silent --show-error --retry 3 \
  "https://github.com/wasm-bindgen/wasm-bindgen/releases/download/${WASM_BINDGEN_VERSION}/${WASM_BINDGEN_ARCHIVE}" \
  -o /tmp/saiga-wasm-bindgen.tar.gz; then
  mkdir -p /tmp/saiga-wasm-bindgen
  tar -xzf /tmp/saiga-wasm-bindgen.tar.gz -C /tmp/saiga-wasm-bindgen
  install -m 0755 "/tmp/saiga-wasm-bindgen/wasm-bindgen-${WASM_BINDGEN_VERSION}-${WASM_BINDGEN_ARCH}/wasm-bindgen" "${CARGO_HOME}/bin/wasm-bindgen"
else
  echo "Prebuilt wasm-bindgen binary unavailable; compiling fallback" >&2
  cargo install wasm-bindgen-cli --version "${WASM_BINDGEN_VERSION}" --locked
fi
wasm-bindgen --version
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
