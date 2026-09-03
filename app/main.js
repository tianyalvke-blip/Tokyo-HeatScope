/**
 * main.js – Application bootstrap
 *
 * Wires all modules together:
 *   config → catalog → map → tools → agent → UI
 */

import { MCPClient } from './mcp-client.js';
import { DatasetCatalog } from './dataset-catalog.js';
import { MapManager } from './map-manager.js';
import { ToolRegistry } from './tool-registry.js';
import { createMapTools } from './map-tools.js';
import { createGeocoder } from './geocoder.js';
import { Agent } from './agent.js';
import { ChatUI } from './chat-ui.js';
import { buildLayout, sidebarHooks } from './layout-manager.js';
import { ResultLayerManager } from './result-layer-manager.js';
import { setLang, getLang, getStrings } from './i18n.js';

async function main() {
    console.log('[main] Starting app…');

    /* ── 1. Load config files ─────────────────────────────────────────── */
    // layers-input.json: static config (catalog URL, collections, view)
    // config.json: deploy-time config with secrets (LLM models, API keys)
    const [appConfig, runtimeConfig] = await Promise.all([
        fetchJson('layers-input.json'),
        fetchJson('config.json').catch(() => null),  // optional — not present in local dev
    ]);

    // Merge: runtime config (secrets) overrides static config
    if (runtimeConfig) {
        if (runtimeConfig.llm_models) appConfig.llm_models = runtimeConfig.llm_models;
        if (runtimeConfig.llm_model) appConfig.llm_model = runtimeConfig.llm_model;
        if (runtimeConfig.transcription_model) appConfig.transcription_model = runtimeConfig.transcription_model;
        if (runtimeConfig.mcp_server_url) appConfig.mcp_url = runtimeConfig.mcp_server_url;
        if (runtimeConfig.mcp_auth_token) appConfig.mcp_auth_token = runtimeConfig.mcp_auth_token;
        if (runtimeConfig.catalog_token) appConfig.catalog_token = runtimeConfig.catalog_token;
        if (runtimeConfig.draw_enabled != null) appConfig.draw_enabled = runtimeConfig.draw_enabled;
        if (runtimeConfig.geolocate != null) appConfig.geolocate = runtimeConfig.geolocate;
        // != null (not truthiness) so 0 — which disables the checkpoint — survives.
        if (runtimeConfig.max_tool_calls != null) appConfig.max_tool_calls = runtimeConfig.max_tool_calls;
        if (runtimeConfig.max_tool_calls_manual != null) appConfig.max_tool_calls_manual = runtimeConfig.max_tool_calls_manual;
    }

    // If no server-provided LLM config, check for user-provided key mode
    if (!appConfig.llm_models && appConfig.llm?.user_provided) {
        const saved = loadUserLLMConfig(appConfig.llm);
        if (saved) {
            appConfig.llm_models = saved.llm_models;
            appConfig.llm_model = saved.llm_models[0]?.value;
            if (saved.transcription_model) appConfig.transcription_model = saved.transcription_model;
        }
        // Flag for ChatUI to show settings button
        appConfig._userProvidedMode = true;
    }
    // Server-side LLM proxy mode: no client key needed — the operator's key
    // lives on the server (/api/llm). Build a minimal model list so the agent
    // has a model to select even without any user-provided or config.json key.
    if (appConfig.llm?.proxy && !appConfig.llm_models) {
        const ep = appConfig.llm.default_endpoint || 'https://api.deepseek.com';
        appConfig.llm_models = (appConfig.llm.models || []).map(m => ({
            value: m.value,
            label: m.label || m.value,
            endpoint: ep,
            api_key: 'server-proxy',
            temperature: m.temperature ?? 0,
        }));
        appConfig.llm_model = appConfig.llm_models[0]?.value || appConfig.llm_model;
    }
    // Always expose the local API settings panel. When a key is entered,
    // ChatUI switches this browser session to direct provider access.
    appConfig._userProvidedMode = true;
    console.log('[main] Config loaded');

    /* ── 1b. Build UI chrome (layout-manager owns floating vs sidebar) ─── */
    const layoutRefs = buildLayout(appConfig);

    /* ── 1c. Kick off independent network I/O so it overlaps ──────────────
     * MCP cold-start, the STAC catalog walk, the map style, and the static
     * system-prompt fetch are mutually independent. Fire the slow ones now and
     * await them together below, instead of serializing each round trip. */
    let mcpUrl = appConfig.mcp_url || 'https://duckdb-mcp.nrp-nautilus.io/mcp';
    // Self-hosted deployment: layers-input.json ships with 127.0.0.1 (dev
    // default) but when the page is served over the LAN/public internet the
    // browser must reach the MCP server on the SAME host it loaded the page
    // from — pointing at loopback would hit the visitor's own machine and be
    // blocked as a private-network request. Rewrite localhost hosts to the
    // page origin's host automatically so the same config works everywhere.
    try {
        const mcpU = new URL(mcpUrl);
        const pageU = new URL(window.location.href);
        if ((mcpU.hostname === '127.0.0.1' || mcpU.hostname === 'localhost')
            && pageU.hostname !== '127.0.0.1' && pageU.hostname !== 'localhost') {
            mcpU.hostname = pageU.hostname;
            // When the page is served over HTTPS (reverse-proxied by Caddy /
            // nginx), the MCP endpoint is reachable on the same origin at
            // /mcp — forcing the bare port would create a mixed-content
            // request the browser blocks. Only fall back to a port override
            // for plain-HTTP LAN deployments.
            if (pageU.protocol === 'https:') {
                mcpU.protocol = 'https:';
                mcpU.port = '';
                mcpU.pathname = '/mcp';
            } else {
                mcpU.port = mcpU.port || pageU.port || (pageU.protocol === 'https:' ? '443' : '80');
            }
            mcpUrl = mcpU.toString();
        }
    } catch { /* keep configured URL on parse failure */ }
    const mcpHeaders = {};
    if (appConfig.mcp_auth_token) {
        mcpHeaders['Authorization'] = `Bearer ${appConfig.mcp_auth_token}`;
    }
    console.log('[main] MCP URL:', mcpUrl, 'auth token present:', !!appConfig.mcp_auth_token);
    const mcp = new MCPClient(mcpUrl, mcpHeaders);
    // Connect eagerly but don't block boot — overlaps catalog + map load below.
    mcp.connect().catch(err => console.warn('[main] Initial MCP connect failed (will retry):', err.message));
    // Static system-prompt fetch (awaited at step 6) — independent of everything.
    const basePromptP = fetchText('system-prompt.md');

    /* ── 2+3. Build dataset catalog + map, loaded in parallel ──────────── */
    const catalog = new DatasetCatalog();
    const mapManager = new MapManager('map', {
        center: appConfig.view?.center || [-119.4, 36.8],
        zoom: appConfig.view?.zoom || 6,
        pitch: appConfig.view?.pitch ?? 0,
        bearing: appConfig.view?.bearing ?? 0,
        globe: appConfig.view?.globe ?? false,
        titilerUrl: appConfig.titiler_url || 'https://titiler.nrp-nautilus.io',
        maptilerKey: runtimeConfig?.maptiler_key || '',
        defaultBasemap: appConfig.default_basemap || 'natgeo',
        customBasemap: appConfig.custom_basemap || null,
        basemapFlavor: appConfig.basemap_flavor || 'light',
    });
    // STAC walk and map-style load run concurrently (the MapManager constructor
    // already kicked off the style fetch); wait for both before wiring layers.
    await Promise.all([catalog.load(appConfig), mapManager.ready]);
    console.log(`[main] Catalog loaded: ${catalog.datasets.size} collections`);
    // Sidebar resize: reflow the MapLibre canvas during drag (rAF-gated by
    // layout-manager) and one final time on drag-end / window-resize.
    sidebarHooks.onResizeTick = () => mapManager.map.resize();
    sidebarHooks.onResizeEnd = () => mapManager.map.resize();
    mapManager.generateMenu(layoutRefs.menuMountId);
    mapManager.addLayersFromCatalog(catalog.getMapLayerConfigs());
    mapManager.generateControls('layer-controls-container');

    /* ── 3a. Analysis Result Layer System ─────────────────────────────── */
    const resultLayerManager = new ResultLayerManager({
        mapManager,
        gridGeojsonUrl: 'data/tokyo_lst_grid.geojson',
        layerControlsId: 'layer-controls-container',
        mcpClient: mcp,
    });
    // Pre-populate the result registry from the server store (best effort,
    // non-blocking) so the agent can create_result_layer() for earlier results.
    resultLayerManager.refreshRegistry().catch(err =>
        console.warn('[main] Result registry refresh failed:', err.message));

    /* ── 3b. Map padding for the chat panel ─────────────────────────────
     * Desktop (floating): the chat docks to the left, so pad the map on the
     * left. Mobile (<700px): the chat becomes a bottom drawer, so pad the map
     * at the bottom instead. Collapsing resets the padding to 0. */
    const chatEl = document.getElementById('chat-container');
    const isMobileLayout = () => window.innerWidth < 700;
    const syncMapPadding = () => {
        if (!chatEl) return 0;
        const w = chatEl.classList.contains('collapsed') ? 0 : (chatEl.offsetWidth || 0);
        if (isMobileLayout()) {
            const h = chatEl.classList.contains('collapsed') ? 0 : (chatEl.offsetHeight || 0);
            mapManager.map.setPadding({ top: 0, bottom: h, left: 0, right: 0 }, { duration: 300 });
        } else {
            mapManager.map.setPadding({ top: 0, bottom: 0, left: w, right: 0 }, { duration: 300 });
        }
        // Drive the zoom control's offset so it clears the chat panel and
        // follows it during resize/collapse.
        document.documentElement.style.setProperty('--chat-width', w + 'px');
        return w;
    };
    const chatWidth = syncMapPadding();
    new MutationObserver(syncMapPadding).observe(
        chatEl,
        { attributes: true, attributeFilter: ['class'] },
    );
    // Horizontal drag-resize of the chat also changes its width — follow it.
    new ResizeObserver(syncMapPadding).observe(chatEl);

    // Optional boot fit-bounds: [[west, south], [east, north]] — derived from
    // the dataset's real bounding box (never a hardcoded guess). Pass explicit
    // padding that clears the left chat panel so the grid centers in the
    // visible map area (fitBounds would otherwise ignore setPadding).
    if (appConfig.view?.fit_bounds) {
        mapManager.map.fitBounds(appConfig.view.fit_bounds, {
            padding: { top: 40, bottom: 40, left: (chatWidth || 0) + 40, right: 40 },
            duration: 800,
        });
    }
    console.log('[main] Map ready');

    /* ── 3c. Polygon draw tool (optional — requires draw_enabled) ───── */
    let mapDraw = null;
    if (appConfig.draw_enabled) {
        try {
            const { MapDraw } = await import('./map-draw.js');
            mapDraw = new MapDraw(mapManager.map);
            await mapDraw.init();
            console.log('[main] Draw tool ready');
        } catch (err) {
            console.warn('[main] Failed to load draw module:', err.message);
        }
    }

    /* ── 3d. Geolocation (optional — "where am I?") ──────────────────── */
    // Two independently opt-in surfaces, both off by default:
    //   • locate-me button (UI)        — geolocate.button
    //   • get_user_location agent tool — geolocate.agent_tool (reaches device
    //     GPS, so off by default even though it's invisible — see map-tools.js)
    // `geolocate: true` is back-compat shorthand for { button: true }.
    const geoLocCfg = appConfig.geolocate === true
        ? { button: true }
        : (appConfig.geolocate && typeof appConfig.geolocate === 'object')
            ? appConfig.geolocate
            : {};
    // GeolocateControl ships with MapLibre GL JS, so there's nothing to pin.
    if (geoLocCfg.button) {
        try {
            mapManager.map.addControl(
                new maplibregl.GeolocateControl({
                    positionOptions: { enableHighAccuracy: true },
                    trackUserLocation: true,
                    showUserLocation: true,
                }),
                'top-left',
            );
            console.log('[main] Geolocate control ready');
        } catch (err) {
            console.warn('[main] Failed to add geolocate control:', err.message);
        }
    }

    /* ── 5. Build tool registry ───────────────────────────────────────── */
    const toolRegistry = new ToolRegistry();

    // Geocoder backend, shared by two independently-toggled surfaces:
    //   • the `geocode` agent tool — ON by default (opt-out: geocoder.enabled=false)
    //   • the on-map search box — OFF by default (opt-in: geocoder.search_box=true)
    // The backend is built when either surface needs it. The MapTiler key, when
    // present, falls back to the basemap key.
    const geoCfg = appConfig.geocoder || {};
    const geocodeToolEnabled = geoCfg.enabled !== false;
    let geocoder = null;
    if (geocodeToolEnabled || geoCfg.search_box) {
        try {
            const isLocal = ['localhost', '127.0.0.1'].includes(window.location.hostname);
            geocoder = createGeocoder({
                ...geoCfg,
                // Self-hosted: route Nominatim through our server proxy so
                // geocoding works even where OSM is blocked. Local dev keeps
                // direct access.
                ...(!isLocal ? { proxy: '/api/geocode' } : {}),
                maptiler_key: geoCfg.maptiler_key || runtimeConfig?.maptiler_key,
            });
        } catch (err) {
            console.warn('[main] Geocoder disabled — invalid config:', err.message);
        }
    }

    // Optional on-map search box, sharing the same geocoder backend.
    if (geocoder && geoCfg.search_box) {
        try {
            const { addSearchBox } = await import('./map-geocoder.js');
            await addSearchBox(mapManager.map, geocoder, {
                position: geoCfg.search_box_position,
                placeholder: geoCfg.search_box_placeholder,
            });
            console.log('[main] Search box ready');
        } catch (err) {
            console.warn('[main] Failed to load search box:', err.message);
        }
    }

    // Register local map tools. The geocode tool is gated on geocodeToolEnabled
    // (not merely on the backend existing), so search_box can run without it.
    // get_user_location is gated separately on the opt-in geolocate.agent_tool.
    for (const tool of createMapTools(mapManager, catalog, mcp, geocodeToolEnabled ? geocoder : null, {
        geolocateTool: !!geoLocCfg.agent_tool,
        resultLayerManager,
    })) {
        toolRegistry.registerLocal(tool);
    }

    // Register draw tool (if draw is enabled and loaded)
    if (mapDraw) {
        toolRegistry.registerLocal({
            name: 'get_drawn_region',
            description:
                'Get the polygon region the user drew on the map, as WKT. ' +
                'Returns the WKT geometry and a suggested H3 resolution based on the region size. ' +
                'To use in SQL: UNNEST(h3_polygon_wkt_to_cells(wkt, resolution)) produces H3 cells ' +
                'that can be JOINed against a dataset\'s H3 index column. Use the resolution ' +
                'closest to (but not exceeding) the suggested resolution. ' +
                'Returns null if no region is drawn. Call this when the user says ' +
                '"this area", "here", "my selection", "the drawn region", or similar.',
            inputSchema: {
                type: 'object',
                properties: {},
            },
            execute: () => {
                const wkt = mapDraw.getRegionWKT();
                if (!wkt) {
                    return JSON.stringify({
                        success: false,
                        error: 'No region drawn. Ask the user to draw a polygon on the map first.',
                    });
                }
                return JSON.stringify({
                    success: true,
                    wkt,
                    suggested_h3_resolution: mapDraw.getSuggestedH3Resolution(),
                    hint: 'To filter by this region, UNNEST h3_polygon_wkt_to_cells(wkt, resolution) and JOIN on the dataset H3 column. ' +
                          'Example: FROM UNNEST(h3_polygon_wkt_to_cells(\'<wkt>\', <res>)) AS t(cell) JOIN data ON data.h3_col = t.cell. ' +
                          'suggested_h3_resolution is a ceiling — pick the dataset H3 column closest to but not exceeding it.',
                });
            },
        });
    }

    // Inline cached STAC content on LLM-issued direct calls to in-app data,
    // mirroring what the local get_schema delegate does (see #192). Skips an
    // upstream fetch on the MCP side. Foreign-catalog calls pass through.
    const injectInlineStac = (toolName, args) => {
        if (!args) return args;
        if (args.catalog_url && args.catalog_url !== catalog.catalogUrl) return args;
        let id = null;
        if (toolName === 'get_stac_details') id = args.dataset_id;
        else if (toolName === 'get_collection') id = args.collection_id;
        if (!id) return args;
        const collection = catalog.toStacDict(id);
        if (!collection) return args;
        return { ...args, collection };
    };

    // Register remote MCP tools. The initial listTools() can time out when
    // the MCP pod is cold-starting; retry a few times before falling back to
    // a minimal hardcoded `query` tool. If the fallback fires, the
    // onReconnect hook below will refresh the registry once the transport
    // finally connects.
    const listMcpToolsWithRetry = async (attempts = 3) => {
        let lastErr;
        for (let i = 0; i < attempts; i++) {
            try {
                // connect() dedupes with the eager connect fired at boot and
                // caches the tool list internally, so getTools() avoids the
                // extra listTools() round trip the old path incurred.
                await mcp.connect();
                const tools = mcp.getTools();
                // An empty list here means the connect resolved before its tool
                // cache was populated — treat it as a failure so we retry, and
                // fall back to the hardcoded `query` tool rather than silently
                // registering zero MCP tools for the life of the session.
                if (!tools.length) throw new Error('MCP connected but returned an empty tool list');
                return tools;
            } catch (err) {
                lastErr = err;
                const delay = Math.min(2000 * Math.pow(2, i), 8000);
                console.warn(`[main] MCP connect attempt ${i + 1}/${attempts} failed: ${err.message}`);
                if (i < attempts - 1) await new Promise(r => setTimeout(r, delay));
            }
        }
        throw lastErr;
    };

    mcp.setOnReconnect((tools) => {
        toolRegistry.clearRemote();
        toolRegistry.registerRemote(tools, mcp, injectInlineStac);
        console.log(`[main] Refreshed MCP tools after reconnect: ${tools.length} tools`);
    });

    try {
        const mcpTools = await listMcpToolsWithRetry();
        toolRegistry.registerRemote(mcpTools, mcp, injectInlineStac);
        console.log(`[main] ${mcpTools.length} MCP tools registered`);
    } catch (err) {
        console.warn('[main] Could not list MCP tools after retries (will refresh on reconnect):', err.message);
        // Hardcoded fallback so the LLM always has at least the query tool.
        // The onReconnect hook replaces this entry once the transport connects.
        toolRegistry.registerRemote([{
            name: 'query',
            description: 'Execute a read-only SQL query against a DuckDB database that is pre-loaded with H3 geospatial extensions, spatial functions, and httpfs for accessing remote parquet data. The database supports partitioned hive-style parquet files on S3.',
            inputSchema: {
                type: 'object',
                properties: {
                    sql_query: {
                        type: 'string',
                        description: 'The SQL query to execute. Must be a read-only SELECT statement.'
                    }
                },
                required: ['sql_query']
            }
        }], mcp, injectInlineStac);
    }

    /* ── 6. Build system prompt ────────────────────────────────────────── */
    const basePrompt = await basePromptP;   // fetch was kicked off at step 1c
    const catalogText = catalog.generatePromptCatalog();
    const baseSystemPrompt = basePrompt + '\n\n' + catalogText;

    /* ── 7. Create agent + UI early (non-blocking welcome) ───────────────
     * Create the agent and chat UI *before* the slower MCP prompt fetch so
     * the welcome message renders immediately. The MCP system prompt is
     * applied via setSystemPrompt() once it arrives below. */
    const agent = new Agent(appConfig, toolRegistry);
    agent.setSystemPrompt(baseSystemPrompt);
    const ui = new ChatUI(agent, appConfig, layoutRefs.chatMount);
    console.log('[main] Agent + UI ready (welcome rendered, prompt pending)');

    // Read server-provided prompt (if any) and update the agent's prompt.
    try {
        const prompts = await mcp.listPrompts();
        const analyst = prompts?.find(p => p.name === 'geospatial-analyst');
        if (analyst) {
            const content = await mcp.getPrompt(analyst.name);
            if (content) {
                agent.setSystemPrompt(baseSystemPrompt + '\n\n' + content);
                console.log('[main] Loaded MCP geospatial-analyst prompt');
            }
        }
    } catch (e) {
        console.warn('[main] No MCP prompts available:', e.message);
    }

    /* ── 3f. UI language switcher (EN / JA / ZH) ─────────────────────────
     * Switches only the static chrome: branding, placeholder, buttons, tab
     * title. Preset welcome text and the agent's replies are left as-is. */
    const applyLanguage = (lang) => {
        setLang(lang);
        const s = getStrings();
        layoutRefs.chatMount.branding.title.textContent = s.brandTitle;
        document.title = s.docTitle;
        for (const btn of layoutRefs.chatMount.langButtons) {
            btn.classList.toggle('active', btn.dataset.lang === lang);
        }
        ui.setLanguage(lang);
    };
    for (const btn of layoutRefs.chatMount.langButtons) {
        btn.addEventListener('click', () => applyLanguage(btn.dataset.lang));
    }
    // Render the default (English) branding on boot.
    applyLanguage(getLang());

    // Draw event → chat notifications.
    // Replace (not append) synthetic draw messages so repeated draw/clear
    // cycles don't bloat the agent's conversation history.
    if (mapDraw) {
        const DRAW_PREFIX = '[The user has drawn a region';
        const CLEAR_PREFIX = '[The user has cleared the drawn region';
        function replaceDrawMessage(content) {
            for (let i = agent.messages.length - 1; i >= 0; i--) {
                const c = agent.messages[i].content;
                if (agent.messages[i].role === 'user' &&
                    (c.startsWith(DRAW_PREFIX) || c.startsWith(CLEAR_PREFIX))) {
                    agent.messages.splice(i, 1);
                }
            }
            agent.messages.push({ role: 'user', content });
        }

        window.addEventListener('region-drawn', () => {
            ui.addMessage('system', 'Region drawn on map. Ask me anything about this area.');
            replaceDrawMessage(
                '[The user has drawn a region of interest on the map. ' +
                'Use the get_drawn_region tool to retrieve the polygon when answering spatial queries about this area.]',
            );
        });
        window.addEventListener('region-cleared', () => {
            ui.addMessage('system', 'Region cleared.');
            replaceDrawMessage(
                '[The user has cleared the drawn region from the map.]',
            );
        });
    }

    console.log('[main] UI ready – app fully loaded');

    // Evaluation entry point: the v2 dashboard can open the real Agent with
    // one prompt preloaded. This keeps the interaction on the production UI
    // and uses the endpoint configured in app/config.json.
    const evalPrompt = new URLSearchParams(window.location.search).get('eval_prompt');
    if (evalPrompt) {
        setTimeout(() => {
            ui.inputEl.value = evalPrompt;
            ui.handleSend();
        }, 350);
    }

    // Debug/test handle — lets automated tests drive the app from the console.
    window.__glen = { mapManager, catalog, toolRegistry, agent, mcp, resultLayerManager };
}

/* ── Helpers ────────────────────────────────────────────────────────────── */

const STORAGE_KEY_API = 'geo-agent-api-key';
const STORAGE_KEY_ENDPOINT = 'geo-agent-endpoint';

/**
 * Build llm_models array (and optionally transcription_model) from
 * localStorage + app llm config. Returns null if no saved API key.
 */
function loadUserLLMConfig(llmConfig) {
    const apiKey = localStorage.getItem(STORAGE_KEY_API);
    if (!apiKey) return null;

    const endpoint = localStorage.getItem(STORAGE_KEY_ENDPOINT)
        || llmConfig.default_endpoint
        || 'https://openrouter.ai/api/v1';

    const models = (llmConfig.models || []).map(m => ({
        ...m,
        endpoint,
        api_key: apiKey,
    }));

    // If no models configured, create a generic one
    if (models.length === 0) {
        models.push({
            value: 'auto',
            label: 'Auto',
            endpoint,
            api_key: apiKey,
        });
    }

    const result = { llm_models: models };

    // Transcription model for voice input — inherits the user's key and
    // (by default) the same endpoint. Either can be overridden per entry.
    if (llmConfig.transcription_model?.value) {
        result.transcription_model = {
            ...llmConfig.transcription_model,
            endpoint: llmConfig.transcription_model.endpoint || endpoint,
            api_key: llmConfig.transcription_model.api_key || apiKey,
        };
    }

    return result;
}

async function fetchJson(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Failed to fetch ${url}: ${res.status}`);
    return res.json();
}

async function fetchText(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Failed to fetch ${url}: ${res.status}`);
    return res.text();
}

/* ── Boot ───────────────────────────────────────────────────────────────── */

main().catch(err => {
    console.error('[main] Fatal boot error:', err);
    const msg = document.getElementById('chat-messages');
    if (msg) {
        msg.innerHTML = `<div class="chat-message error">Failed to start: ${err.message}</div>`;
    }
});
