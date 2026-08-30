// Generate an offline, local-first basemap style for the Tokyo OSM PMTiles.
//
// The Protomaps basemap schema (@protomaps/basemaps) turns the
// tokyo-osm-*.pmtiles into MapLibre style layers. Symbol (label) layers are
// dropped so no online glyph server is needed at runtime.
//
// Output: public/basemap/tokyo_basemap_style.json
//   (a plain style JSON the frontend loads statically - no esm.sh, no CDN)

import { readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = resolve(__dirname, "..");

// Resolve @protomaps/basemaps from this repo's node_modules if present,
// otherwise from a sibling checkout (F:\TokyoLSTAgent\app-ai-cn).
let basemapsPkg = null;
for (const cand of [
    resolve(REPO, "node_modules/@protomaps/basemaps"),
    "F:\\TokyoLSTAgent\\app-ai-cn\\node_modules\\@protomaps\\basemaps",
]) {
    try {
        basemapsPkg = require(cand);
        console.log("[basemap] using package at", cand);
        break;
    } catch {
        /* try next */
    }
}
if (!basemapsPkg) {
    console.error("[basemap] @protomaps/basemaps not found; run `npm install` first.");
    process.exit(1);
}

const { layers, namedFlavor } = basemapsPkg;

// Keep only non-symbol layers -> no glyph/font dependency, fully offline.
const styleLayers = layers("protomaps", namedFlavor("grayscale"), { lang: "en" })
    .filter((l) => l.type !== "symbol");

const style = {
    version: 8,
    name: "Tokyo OSM (local PMTiles, z15)",
    sources: {
        tokyo: {
            type: "vector",
            url: "pmtiles:///basemap/tokyo-osm-20260824-z15.pmtiles",
            attribution: "© OpenStreetMap contributors, Protomaps",
        },
    },
    glyphs: undefined,
    layers: styleLayers,
};

const out = resolve(REPO, "public", "basemap", "tokyo_basemap_style.json");
writeFileSync(out, JSON.stringify(style, null, 0));
console.log(`[basemap] wrote ${out} (${styleLayers.length} layers)`);
