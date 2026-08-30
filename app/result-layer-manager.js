/**
 * result-layer-manager.js — Analysis Result Layer System.
 *
 * Turns any registered analysis result (Local Moran, SQL grid selection,
 * run_python output, and future RF/SHAP/scenario outputs) into an independent
 * MapLibre layer without touching the raw Day/Night LST data layers.
 *
 * Core contract:
 *   Analysis → Result Store → analysis_id → create_result_layer(analysis_id)
 *
 * The manager:
 *   1. resolves result metadata (visualization, tooltip, data URL)
 *   2. fetches the per-grid result records (grid_id + derived fields)
 *   3. joins grid_id onto the shared Tokyo 200 m grid geometry (never recomputes
 *      polygons)
 *   4. builds a GeoJSON FeatureCollection with source properties merged in
 *   5. registers a normal vector layer through MapManager, so show/hide /
 *      filter / restyle / tooltip / legend all reuse the existing machinery.
 *
 * Visualization types: categorical | continuous | binary | diverging.
 */

export class ResultLayerManager {
    constructor({ mapManager, gridGeojsonUrl, layerControlsId, mcpClient }) {
        this.mapManager = mapManager;
        this.gridGeojsonUrl = gridGeojsonUrl || 'data/tokyo_lst_grid.geojson';
        this.layerControlsId = layerControlsId || 'layer-controls-container';
        this.mcpClient = mcpClient || null;
        /** @type {Map<string, Object>} analysis_id → result metadata */
        this.results = new Map();
        /** @type {Map<number, Object>} grid_id → source feature */
        this._gridIndex = null;
    }

    /** Populate the local registry from the MCP result store (best effort). */
    async refreshRegistry() {
        if (!this.mcpClient) return;
        try {
            const raw = await this.mcpClient.callTool('list_analysis_results', {});
            const parsed = JSON.parse(raw);
            if (parsed?.success && Array.isArray(parsed.results)) {
                for (const meta of parsed.results) this.results.set(meta.analysis_id, meta);
            }
        } catch (err) {
            console.warn('[ResultLayer] registry refresh failed:', err.message);
        }
    }

    async getMetadata(analysisId) {
        if (this.results.has(analysisId)) return this.results.get(analysisId);
        if (this.mcpClient) {
            try {
                const raw = await this.mcpClient.callTool('get_analysis_result', { analysis_id: analysisId });
                const parsed = JSON.parse(raw);
                if (parsed?.success && parsed.result) {
                    this.results.set(analysisId, parsed.result);
                    return parsed.result;
                }
            } catch (err) {
                console.warn('[ResultLayer] metadata fetch failed:', err.message);
            }
        }
        return null;
    }

    async _getGridIndex() {
        if (this._gridIndex) return this._gridIndex;
        const res = await fetch(this.gridGeojsonUrl);
        const fc = await res.json();
        const idx = new Map();
        for (const f of fc.features || []) {
            idx.set(f.properties.grid_id, f);
        }
        this._gridIndex = idx;
        return idx;
    }

    /** Build the merged FeatureCollection (result fields ⊕ grid properties). */
    async _buildFeatureCollection(meta, records) {
        const gridIdx = await this._getGridIndex();
        const features = [];
        for (const rec of records) {
            const g = gridIdx.get(rec.grid_id);
            if (!g) continue;
            features.push({
                type: 'Feature',
                geometry: g.geometry,
                properties: { ...(g.properties || {}), ...rec },
            });
        }
        return { type: 'FeatureCollection', features };
    }

    _range(records, field, viz) {
        if (typeof viz.min === 'number' && typeof viz.max === 'number') {
            return [viz.min, viz.max];
        }
        let lo = Infinity, hi = -Infinity;
        for (const r of records) {
            const v = Number(r[field]);
            if (Number.isFinite(v)) { if (v < lo) lo = v; if (v > hi) hi = v; }
        }
        return [lo, hi];
    }

    _buildStyle(viz, records) {
        const type = viz?.type || 'binary';
        const field = viz?.field || 'grid_id';
        const opacity = 0.78;
        if (type === 'categorical') {
            const cats = viz.categories || {};
            const stops = [];
            for (const [k, c] of Object.entries(cats)) stops.push(k, c);
            return {
                paint: {
                    'fill-color': ['match', ['get', field], ...stops, '#cccccc'],
                    'fill-opacity': opacity,
                },
                stats: { range: null, colors: null },
            };
        }
        if (type === 'diverging') {
            const [lo, hi] = this._range(records, field, viz);
            const center = typeof viz.center === 'number' ? viz.center : (lo + hi) / 2;
            const colors = [viz.low || '#2166ac', viz.neutral || '#f7f7f7', viz.high || '#b2182b'];
            return {
                paint: {
                    'fill-color': ['interpolate', ['linear'], ['get', field],
                        lo, colors[0], center, colors[1], hi, colors[2]],
                    'fill-opacity': opacity,
                },
                stats: { range: [lo, hi], colors },
            };
        }
        if (type === 'continuous') {
            const [lo, hi] = this._range(records, field, viz);
            if (!(lo < hi)) lo = hi - 1;
            const colors = viz.gradient || ['#313695', '#fee090', '#d73027'];
            return {
                paint: {
                    'fill-color': ['interpolate', ['linear'], ['get', field],
                        lo, colors[0], (lo + hi) / 2, colors[1], hi, colors[2]],
                    'fill-opacity': opacity,
                },
                stats: { range: [lo, hi], colors },
            };
        }
        // binary
        return {
            paint: { 'fill-color': viz.color || '#E65100', 'fill-opacity': opacity },
            stats: { range: null, colors: null },
        };
    }

    /**
     * Create a MapLibre result layer for an analysis result.
     * @param {string} analysisId
     * @returns {Promise<Object>} { success, layer_id, display_name, ... }
     */
    async createResultLayer(analysisId) {
        const meta = await this.getMetadata(analysisId);
        if (!meta) return { success: false, error: `Unknown analysis_id: ${analysisId}` };

        const existingId = `analysis/${analysisId}`;
        if (this.mapManager.layers.has(existingId)) {
            return { success: true, layer_id: existingId, display_name: meta.display_name, already_exists: true };
        }

        let records;
        try {
            const res = await fetch(meta.data_url);
            records = await res.json();
        } catch (err) {
            return { success: false, error: `Could not load result data (${meta.data_url}): ${err.message}` };
        }

        const fc = await this._buildFeatureCollection(meta, records);
        const viz = meta.visualization || { type: 'binary' };
        const { paint, stats } = this._buildStyle(viz, records);
        const tooltipFields = (meta.tooltip_fields && meta.tooltip_fields.length)
            ? meta.tooltip_fields
            : ['grid_id'];

        const isCategorical = viz.type === 'categorical';
        const isContinuous = viz.type === 'continuous' || viz.type === 'diverging';

        const config = {
            layerId: existingId,
            datasetId: null,
            group: 'RESULTS',
            groupCollapsed: false,
            displayName: meta.display_name,
            type: 'vector',
            source: { type: 'geojson', data: fc },
            paint,
            outlinePaint: { 'line-color': 'rgba(0,0,0,0.25)', 'line-width': 0.4 },
            renderType: null,
            columns: [],
            tooltipFields,
            defaultVisible: true,
            defaultFilter: null,
            colormap: null,
            rescale: null,
            legendLabel: isContinuous ? viz.field : null,
            legendType: isCategorical ? 'categorical' : (isContinuous ? 'continuous' : null),
            legendClasses: isCategorical
                ? Object.entries(viz.categories || {}).map(([k, c]) => ({ name: k, 'color-hint': c }))
                : null,
            legendRange: isContinuous ? stats.range : null,
            legendGradient: isContinuous ? stats.colors : null,
        };

        this.mapManager.registerLayer(config);
        this.mapManager.showLayer(existingId);
        if (this.mapManager.generateControls && this.layerControlsId) {
            this.mapManager.generateControls(this.layerControlsId);
        }
        return {
            success: true,
            layer_id: existingId,
            display_name: meta.display_name,
            analysis_type: meta.analysis_type,
            n: fc.features.length,
        };
    }

    /** Remove a result layer (map layers + source + state + panel entry). */
    removeResultLayer(layerId) {
        const result = this.mapManager.removeLayer(layerId);
        if (result.success && this.mapManager.generateControls && this.layerControlsId) {
            this.mapManager.generateControls(this.layerControlsId);
        }
        return result;
    }

    /** List result layers currently on the map. */
    listResultLayers() {
        const layers = [];
        for (const [id, state] of this.mapManager.layers) {
            if (state.group === 'RESULTS') {
                layers.push({ layer_id: id, display_name: state.displayName, visible: state.visible });
            }
        }
        return { success: true, layers };
    }
}
