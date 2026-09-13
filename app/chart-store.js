/**
 * ChartStore — trusted, serialisable chart state for HeatScope chat charts.
 *
 * The LLM supplies intent and small edit operations, never arbitrary ECharts
 * options or raw numeric points. Scenario data is accepted only after the
 * matching MCP tool has returned a successful `simulate_feature_curve` result.
 */

const clone = (value) => JSON.parse(JSON.stringify(value));

function newId(prefix) {
    const suffix = globalThis.crypto?.randomUUID?.().replaceAll('-', '').slice(0, 12)
        || `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`;
    return `${prefix}_${suffix}`;
}

function parseJson(value) {
    if (typeof value !== 'string') return value;
    try { return JSON.parse(value); } catch { return null; }
}

function featureTitle(curve) {
    return `Predicted LST response to ${curve.feature_label || curve.feature}`;
}

function contextLabel(source = {}) {
    if (source.context_label) return source.context_label;
    if (source.context_mode === 'area' && source.area_id) {
        // `ikebukuro_800m` → `Ikebukuro 800m`; a readable fallback when the
        // caller has not provided a display label.
        return String(source.area_id).replace(/[_-]+/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    }
    if (source.context_mode === 'grid') return `Grid ${source.grid_id}`;
    if (source.context_mode === 'pdp') return 'Tokyo-wide PDP';
    return 'Scenario';
}

export class ChartStore {
    constructor() {
        this.charts = new Map();
        this.originals = new Map();
        this.curves = new Map();
        this.activeChartId = null;
        this.listeners = new Set();
    }

    subscribe(listener) {
        this.listeners.add(listener);
        return () => this.listeners.delete(listener);
    }

    _emit(type, chart) {
        for (const listener of this.listeners) {
            try { listener({ type, chart: clone(chart), activeChartId: this.activeChartId }); }
            catch (err) { console.warn('[ChartStore] listener failed:', err); }
        }
    }

    /** Cache only a successful MCP-produced curve. */
    ingestToolResults(results) {
        for (const result of results || []) {
            if (!result?.success || result.name !== 'simulate_feature_curve') continue;
            const payload = parseJson(result.result);
            if (payload?.success && payload.curve_id && Array.isArray(payload.series)) {
                this.curves.set(payload.curve_id, clone(payload));
            }
        }
    }

    _curve(curveId) {
        const curve = this.curves.get(curveId);
        if (!curve) throw new Error(`Unknown curve_id '${curveId}'. Run simulate_feature_curve before creating or adding a chart series.`);
        return clone(curve);
    }

    _series(curve) {
        const place = contextLabel(curve.source);
        return curve.series.map((series) => ({
            // The curve ID prevents collisions if a later scenario also has a
            // daytime series. `short_id` lets natural-language edits say "day".
            id: `${series.id}__${curve.curve_id}`,
            short_id: series.id,
            name: `${place} · ${series.name}`,
            values: [...series.values],
            absolute_values: [...series.values],
            baseline: series.baseline,
            visible: true,
            source_curve_id: curve.curve_id,
            context_label: place,
        }));
    }

    _applyYMode(spec) {
        const delta = spec.y.mode === 'delta_from_baseline';
        spec.y.label = delta ? 'Predicted LST change relative to baseline' : 'Predicted LST';
        spec.y.unit = delta ? '°C change' : '°C';
        for (const series of spec.series) {
            series.values = delta
                ? series.absolute_values.map(v => Number((v - series.baseline).toFixed(4)))
                : [...series.absolute_values];
        }
    }

    createChart({ curve_id, title } = {}) {
        const curve = this._curve(curve_id);
        const chart = {
            chart_id: newId('chart'),
            type: 'line',
            title: String(title || featureTitle(curve)).slice(0, 160),
            x: {
                field: curve.feature,
                label: curve.feature_label || curve.feature,
                unit: curve.x_unit || '',
                values: [...curve.x_values],
                range: null,
            },
            y: { label: 'Predicted LST', unit: curve.y_unit || '°C', mode: 'absolute' },
            series: this._series(curve),
            data_mode: curve.data_mode || 'scenario',
            editable: true,
            source: { ...curve.source, tool: 'simulate_feature_curve', curve_ids: [curve.curve_id] },
            method_note: curve.method_note || '',
            caveat: curve.caveat || null,
        };
        this.charts.set(chart.chart_id, chart);
        this.originals.set(chart.chart_id, clone(chart));
        this.activeChartId = chart.chart_id;
        this._emit('created', chart);
        return clone(chart);
    }

    updateChart({ chart_id, action, curve_id, title, min, max, series_id, visible, y_mode, x_display } = {}) {
        const id = chart_id || this.activeChartId;
        const chart = this.charts.get(id);
        if (!chart) throw new Error('No active chart. Create a chart from a simulated curve first.');
        const op = action || 'set_title';

        if (op === 'add_curve') {
            const curve = this._curve(curve_id);
            if (JSON.stringify(curve.x_values) !== JSON.stringify(chart.x.values)) {
                throw new Error('The new curve uses different x values. Create a separate chart or use the same scenario values.');
            }
            const existing = new Set(chart.series.map(s => s.id));
            const additions = this._series(curve).filter(s => !existing.has(s.id));
            if (!additions.length) throw new Error('This curve is already displayed in the active chart.');
            chart.series.push(...additions);
            chart.source.curve_ids.push(curve.curve_id);
        } else if (op === 'set_title') {
            if (!String(title || '').trim()) throw new Error('A non-empty chart title is required.');
            chart.title = String(title).trim().slice(0, 160);
        } else if (op === 'set_x_range') {
            const low = Number(min);
            const high = Number(max);
            if (!Number.isFinite(low) || !Number.isFinite(high) || low >= high) throw new Error('x range needs numeric min and max, with min < max.');
            const values = chart.x.values;
            if (low < Math.min(...values) || high > Math.max(...values)) throw new Error('x range must stay within the computed curve values.');
            chart.x.range = [low, high];
        } else if (op === 'set_visibility') {
            const candidates = chart.series.filter(s => s.id === series_id || s.short_id === series_id || s.name.toLowerCase().includes(String(series_id || '').toLowerCase()));
            if (!candidates.length) throw new Error(`Series '${series_id}' was not found.`);
            // A natural-language “hide daytime” should hide every daytime
            // line in a comparison, while UI controls pass the unique full ID
            // to toggle one location only.
            candidates.forEach(series => { series.visible = Boolean(visible); });
        } else if (op === 'set_y_mode') {
            if (!['absolute', 'delta_from_baseline'].includes(y_mode)) throw new Error("y_mode must be 'absolute' or 'delta_from_baseline'.");
            chart.y.mode = y_mode;
            this._applyYMode(chart);
        } else if (op === 'set_x_display') {
            if (x_display !== 'ndvi') throw new Error("x_display currently supports only 'ndvi'.");
            if (String(chart.x.field).toLowerCase() !== 'ndvi') throw new Error('NDVI axis display can only be used for an NDVI chart.');
            // Earlier previews represented NDVI×100 as "%". This changes
            // presentation only: the trusted RF y values and series stay put.
            if (chart.x.unit === '%') {
                chart.x.values = chart.x.values.map(v => Number((v / 100).toFixed(6)));
                if (chart.x.range) chart.x.range = chart.x.range.map(v => Number((v / 100).toFixed(6)));
            }
            chart.x.label = 'Vegetation index (NDVI)';
            chart.x.unit = 'NDVI';
        } else if (op === 'reset') {
            const original = this.originals.get(id);
            if (!original) throw new Error('No original state is available for this chart.');
            this.charts.set(id, clone(original));
            this.activeChartId = id;
            this._emit('updated', original);
            return clone(original);
        } else {
            throw new Error(`Unsupported chart action '${op}'.`);
        }
        this.activeChartId = id;
        this._emit('updated', chart);
        return clone(chart);
    }

    get(chartId = this.activeChartId) {
        const chart = this.charts.get(chartId);
        return chart ? clone(chart) : null;
    }
}

/** Local tools intentionally accept IDs and edit operations, never data arrays. */
export function createChartTools(chartStore) {
    return [
        {
            name: 'create_chart',
            description: 'Create one editable HeatScope line chart from a successful simulate_feature_curve result. Use its curve_id; never invent data values or ECharts options.',
            inputSchema: {
                type: 'object', properties: {
                    curve_id: { type: 'string', description: 'curve_id returned by simulate_feature_curve in this conversation.' },
                    title: { type: 'string', description: 'Optional concise chart title.' },
                }, required: ['curve_id'],
            },
            execute: (args) => ({ success: true, chart: chartStore.createChart(args) }),
        },
        {
            name: 'update_chart',
            description: 'Edit the active HeatScope chart by a constrained operation. Use add_curve only with a fresh trusted curve_id. Do not create a replacement chart unless the user asks for a separate chart.',
            inputSchema: {
                type: 'object', properties: {
                    chart_id: { type: 'string', description: 'Optional chart ID; omit to edit the active chart.' },
                    action: { type: 'string', enum: ['add_curve', 'set_title', 'set_x_range', 'set_visibility', 'set_y_mode', 'set_x_display', 'reset'] },
                    curve_id: { type: 'string', description: 'Required for add_curve; returned by simulate_feature_curve.' },
                    title: { type: 'string', description: 'Required for set_title.' },
                    min: { type: 'number', description: 'Required lower x value for set_x_range.' },
                    max: { type: 'number', description: 'Required upper x value for set_x_range.' },
                    series_id: { type: 'string', description: 'Required for set_visibility; use day_lst or night_lst when unambiguous.' },
                    visible: { type: 'boolean', description: 'Required for set_visibility.' },
                    y_mode: { type: 'string', enum: ['absolute', 'delta_from_baseline'], description: 'Required for set_y_mode.' },
                    x_display: { type: 'string', enum: ['ndvi'], description: "Use 'ndvi' with set_x_display to show existing NDVI x values as 0.05, 0.10, … rather than legacy percent notation." },
                }, required: ['action'],
            },
            execute: (args) => ({ success: true, chart: chartStore.updateChart(args) }),
        },
    ];
}
