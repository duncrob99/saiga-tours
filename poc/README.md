# SAIGA Tours — Cloudflare static + Rust proof of concept

This folder is intentionally isolated from Django production code. No existing application behaviour has been migrated.

## Contents

- `generator/`: Leptos 0.8 server-side static HTML generator. Writes one real `index.html` per route.
- `browser/`: Rust WASM client-side router, delegated interactivity, and timing diagnostics.
- `admin/`: Rust Cloudflare Worker with editable draft articles/map data in R2 and Cloudflare Workers Builds deployment hook.
- `content.json`: seed content and initial published fixture.
- `public.wrangler.toml`: public Cloudflare *Static Assets*, with no Worker entrypoint.
- `.github/workflows/saiga-poc-publish.yml`: versioned static deployment on the prototype branch.

**Status:** architectural source prototype. Cloudflare credentials, protected hostname and deployment have not been configured. Compilation and runtime behaviour must be validated in GitHub Actions before considering this working or production-ready.

## Local build

Install Rust, wasm32 target, wasm-bindgen-cli, Node and Wrangler:

```sh
rustup target add wasm32-unknown-unknown
cargo install wasm-bindgen-cli --locked
cd poc
cargo build --release -p saiga-poc-browser --target wasm32-unknown-unknown
mkdir -p dist/pkg
wasm-bindgen ../target/wasm32-unknown-unknown/release/saiga_poc_browser.wasm --target web --out-dir dist/pkg
cargo run --release -p saiga-poc-generator -- content.json dist
npx wrangler dev -c public.wrangler.toml
```

The public HTML is pre-rendered during build and can be served without running Rust on incoming requests. Client navigation fetches the next HTML file and swaps `<main>`; delegated WASM handlers continue working after swaps.

## Cloudflare-native builds (no GitHub Actions, no laptop)

**Current preferred architecture:** Cloudflare Workers Builds checks out this repository and compiles the Rust/WASM static site on Cloudflare build infrastructure. The admin Worker posts to a Cloudflare Workers Builds Deploy Hook after saving a published snapshot in private R2. The public Worker serves bundled Static Assets directly, with no public-request Worker execution.

Cloudflare Workers Builds documentation: https://developers.cloudflare.com/workers/ci-cd/builds/
Deploy Hooks documentation: https://developers.cloudflare.com/workers/ci-cd/builds/deploy-hooks/

### One-time staging setup

1. In Cloudflare Workers & Pages, create/connect a Worker named `saiga-poc-public` to GitHub repository `duncrob99/saiga-tours`, branch `poc/cloudflare-leptos-static-publishing`. This build runs **on Cloudflare**, not GitHub Actions. Use root directory `poc`.
2. Set the Workers Builds build command to `bash cloudflare-build.sh` and deploy command to `npx wrangler deploy -c public.wrangler.toml`. Enable build dependency caching. The build requires Cargo, rustup, Node and the wasm-bindgen CLI; confirm Cloudflare's selected build image supports those prerequisites.
3. Initially omit content-fetch variables; the static site will use the checked-in seed `content.json`. Test the public Worker at its staging workers.dev hostname. Do not attach `saigatours.com`.
4. Create a private R2 bucket named `saiga-poc-content` and deploy `poc/admin/wrangler.toml` as a **separate** `saiga-poc-admin` Worker. Attach staging hostname `admin-poc.saigatours.com` and protect its administration routes with Cloudflare Access and MFA. The example checks for an Access assertion header but does not cryptographically verify the JWT: protection must be enforced by Cloudflare Access itself.
5. In the public Worker's Settings → Builds → Deploy Hooks, create a hook for the POC branch. Copy it directly into the *admin Worker's encrypted secret* named `CLOUDFLARE_BUILD_HOOK` (e.g. via `wrangler secret put CLOUDFLARE_BUILD_HOOK -c admin/wrangler.toml`). Do not commit the URL.
6. Set admin secret `PUBLISH_TOKEN` to a random high-entropy value. Configure the **Cloudflare Builds environment** with the same value under `SAIGA_POC_PUBLISH_TOKEN` and the published-snapshot endpoint URL under `SAIGA_POC_PUBLISH_URL`. Treat both as sensitive build environment settings.
7. Configure Cloudflare Access to allow only the intended build-to-admin retrieval of `/api/published`, while keeping all editing routes staff-only. The simple prototype's bearer token is separate from Cloudflare Access. If Access protects this endpoint, supply the appropriate Access service-token headers during the build, or implement a separate narrowly scoped machine-only endpoint. **Do not make the draft API or admin UI public to work around Access.**
8. Save an article draft, then select Publish. Verify that R2 holds the new published snapshot, the Deploy Hook causes a Workers Build, the build fetches that snapshot, and Cloudflare deploys the new static assets. Inspect build logs and staging URLs before trusting the pipeline.

**Important:** Cloudflare Deploy Hooks are secrets (any holder can trigger builds), and build quotas/limits still apply on Cloudflare; using Cloudflare avoids consuming GitHub Actions minutes, not build-resource constraints. A successful HTTP response to the hook confirms a build request, not deployment success. Concurrent publications and idempotent version tracking need further implementation.

### Manual build (optional, not infrastructure)

```sh
cd poc
bash cloudflare-build.sh
npx wrangler deploy -c public.wrangler.toml
```

The manual commands are for debugging only; routine builds and publishing are intended to run entirely within Cloudflare.

## Diagnostics / acceptance tests

Open Performance diagnostics on the public site. The browser records:
- Initial WASM start relative to the browser performance clock.
- Link-click → fetched HTML and DOM swap.
- Link-click → interactive island handler availability.
- Number of islands scanned on each route.

Check mobile cold loads, revisits, click latency, browser back/forward, direct URLs and reloads, keyboard operation, history and the selected map marker. Compare with a full reload using Chrome DevTools network throttling.

**Not yet implemented:** a proper Leptos `#[island]` hydration boundary, full map dragging/editing, field-level conflict control, secure multi-admin publication coordination, rollback UI, visual parity with the existing site, and end-to-end production-data migration. These must be verified in subsequent POC iterations.

**Safety:** this is a non-production experiment. Admin content is unsanitized Markdown/HTML for trusted staff only; sanitisation and CSP are required for production. Never route production `saigatours.com` to this prototype.
