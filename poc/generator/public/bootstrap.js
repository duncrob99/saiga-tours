// Minimal loader only. Navigation, measurement and interactive islands run in Rust/WASM.
import init, { start } from '/pkg/saiga_poc_browser.js';
init().then(start).catch(error => console.error('Browser WASM failed to initialise', error));
