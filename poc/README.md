# SAIGA Tours — Cloudflare static + Rust proof of concept

This folder is intentionally isolated from Django production code. No existing application behaviour has been migrated.

## Contents

- `generator/`: Leptos 0.8 server-side static HTML generator. Writes one real `index.html` per route.
- `browser/`: Rust WASM client-side router, delegated interactivity, and timing diagnostics.
- `admin/`: Rust Cloudflare Worker with editable draft articles/map data in R2 and GitHub Actions publication dispatch.
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

## Cloudflare setup (staging only)

1. Use an existing Cloudflare-managed zone for `saigatours.com`. **Do not replace production routes yet**.
2. In Cloudflare R2, create a private bucket `saiga-poc-content` (`npx wrangler r2 bucket create saiga-poc-content`). Leave public bucket access disabled.
3. Authenticate Wrangler with `npx wrangler login`. From `poc/admin`, set:
   ```sh
   npx wrangler secret put PUBLISH_TOKEN
   npx wrangler secret put GITHUB_DISPATCH_TOKEN
   ```
   `GITHUB_DISPATCH_TOKEN` is a fine-grained GitHub token scoped to `duncrob99/saiga-tours` with Actions write permission. Do not commit it.
4. Deploy the Rust admin Worker using `npx wrangler deploy -c admin/wrangler.toml` from `poc`, after successful wasm build. Bind a **staging** hostname such as `admin-poc.saigatours.com`. Set `workers_dev = false` and ensure there are no other public/unprotected routes.
5. In Cloudflare Zero Trust → Access → Applications, add a self-hosted application matching `admin-poc.saigatours.com/*`. Restrict access to named administrator identities, require MFA, and verify unauthorised users cannot reach any admin endpoint. Access protection must be at the edge; a JWT header-presence check alone is **not** cryptographic validation.
6. The `/api/published` endpoint is protected by a separate random `PUBLISH_TOKEN`; if Access covers the whole hostname, create a narrow **service-token exception/policy** for this endpoint or provide a separate Worker service binding. Never expose the published snapshot anonymously. Ensure that the bearer-token fetch from GitHub Actions can actually pass your Access configuration.
7. In GitHub repository Settings → Secrets and variables → Actions, add:
   - Secrets: `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, `SAIGA_POC_PUBLISH_TOKEN`.
   - Variables: `SAIGA_POC_PUBLISH_URL=https://admin-poc.saigatours.com/api/published`, `SAIGA_POC_ENABLE_DEPLOY=true`.
   Cloudflare token needs appropriate Workers Scripts edit/deploy permissions for the selected account.
8. In `poc`, run `npx wrangler deploy -c public.wrangler.toml` after generating `dist`, or let the workflow perform that step. This creates `saiga-poc-public.<account>.workers.dev`; test it first. Associate a staging hostname such as `poc.saigatours.com` with the public Worker through Cloudflare Workers → Settings → Domains & Routes only after verification.
9. In the admin app, save a changed article or map and select Publish. Watch the `SAIGA POC build and publish` GitHub Action. On success the newly deployed static files should appear at the staging hostname. The admin and public Workers are independently deployed.

**Cloudflare Access integration blocker:** the sample GitHub Actions HTTP fetch only supplies its publication bearer token. An Access-protected host will ordinarily require an Access service token as well. Configure that separately or adapt the workflow to send the Access client ID/secret headers before using an Access-protected endpoint. This is intentionally documented rather than implying the sample will work without it.

## Diagnostics / acceptance tests

Open Performance diagnostics on the public site. The browser records:
- Initial WASM start relative to the browser performance clock.
- Link-click → fetched HTML and DOM swap.
- Link-click → interactive island handler availability.
- Number of islands scanned on each route.

Check mobile cold loads, revisits, click latency, browser back/forward, direct URLs and reloads, keyboard operation, history and the selected map marker. Compare with a full reload using Chrome DevTools network throttling.

**Not yet implemented:** a proper Leptos `#[island]` hydration boundary, full map dragging/editing, field-level conflict control, secure multi-admin publication coordination, rollback UI, visual parity with the existing site, and end-to-end production-data migration. These must be verified in subsequent POC iterations.

**Safety:** this is a non-production experiment. Admin content is unsanitized Markdown/HTML for trusted staff only; sanitisation and CSP are required for production. Never route production `saigatours.com` to this prototype.
