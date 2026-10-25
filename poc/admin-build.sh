#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export RUSTUP_HOME="${RUSTUP_HOME:-$HOME/.rustup}"
export CARGO_HOME="${CARGO_HOME:-$HOME/.cargo}"
export PATH="$CARGO_HOME/bin:$PATH"
if ! command -v rustup >/dev/null 2>&1; then
  curl --fail --location --silent --show-error --proto '=https' --tlsv1.2 https://sh.rustup.rs -o /tmp/saiga-rustup-init.sh
  sh /tmp/saiga-rustup-init.sh -y --profile minimal --default-toolchain stable --no-modify-path
fi
rustup toolchain install stable --profile minimal
rustup default stable
rustup target add wasm32-unknown-unknown
cargo check -p saiga-poc-admin --target wasm32-unknown-unknown
cargo install worker-build --locked
cd admin
worker-build --release
test -s build/worker/shim.mjs
