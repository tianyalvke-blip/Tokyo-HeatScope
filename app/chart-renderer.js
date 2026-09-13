/** ChartRenderer — DOM + ECharts projection of the neutral ChartSpec. */

export class ChartRenderer {
    constructor(chartStore, messagesEl, onScroll = () => {}) {
        this.store = chartStore;
        this.messagesEl = messagesEl;
        this.onScroll = onScroll;
        this.cards = new Map();
        this.instances = new Map();
        this.unsubscribe = chartStore.subscribe(({ type, chart }) => this.render(chart, type));
    }

    render(chart, eventType = 'updated') {
        let card = this.cards.get(chart.chart_id);
        if (!card) {
            card = this._createCard(chart.chart_id);
            this.cards.set(chart.chart_id, card);
            this.messagesEl.appendChild(card);
        }
        card.querySelector('.chart-card-title').textContent = chart.title;
        const note = card.querySelector('.chart-card-note');
        note.textContent = [chart.method_note, chart.caveat].filter(Boolean).join(' ');
        note.hidden = !note.textContent;
        this._renderECharts(card.querySelector('.chart-canvas'), chart);
        // Editing an existing chart must not pull the user away from the
        // message they are reading. Only a newly-created card scrolls in.
        if (eventType === 'created') this.onScroll();
    }

    _createCard(chartId) {
        const card = document.createElement('section');
        card.className = 'chat-message assistant chart-message';
        card.dataset.chartId = chartId;
        card.innerHTML = `
            <div class="chart-card-head">
                <div><div class="chart-card-kicker">Scenario chart</div><h3 class="chart-card-title"></h3></div>
                <div class="chart-card-actions">
                    <label class="chart-y-axis">Y axis
                        <select data-y-mode><option value="absolute">Predicted LST</option><option value="delta_from_baseline">Change from baseline</option></select>
                    </label>
                    <button type="button" data-action="reset">Reset</button>
                    <button type="button" data-action="download">Download</button>
                </div>
            </div>
            <div class="chart-canvas" role="img" aria-label="Interactive line chart"></div>
            <p class="chart-card-note" hidden></p>`;
        card.querySelector('[data-y-mode]').addEventListener('change', (event) => {
            try {
                this.store.updateChart({ chart_id: chartId, action: 'set_y_mode', y_mode: event.target.value });
            } catch (err) {
                console.warn('[ChartRenderer] y-axis update failed:', err);
            }
        });
        card.querySelector('[data-action="reset"]').addEventListener('click', () => {
            try { this.store.updateChart({ chart_id: chartId, action: 'reset' }); }
            catch (err) { console.warn('[ChartRenderer] reset failed:', err); }
        });
        card.querySelector('[data-action="download"]').addEventListener('click', () => this._download(chartId));
        return card;
    }

    _renderECharts(el, chart) {
        if (typeof echarts === 'undefined') {
            el.textContent = 'Chart library is unavailable. Reload after checking the ECharts script.';
            return;
        }
        const old = this.instances.get(chart.chart_id);
        const instance = old || echarts.init(el, null, { renderer: 'canvas' });
        if (!old) {
            this.instances.set(chart.chart_id, instance);
            new ResizeObserver(() => instance.resize()).observe(el);
        }
        const ySelect = el.closest('.chart-message')?.querySelector('[data-y-mode]');
        if (ySelect) ySelect.value = chart.y.mode;
        const values = chart.x.values;
        const range = chart.x.range;
        const indexes = values.map((v, i) => ({ v, i })).filter(({ v }) => !range || (v >= range[0] && v <= range[1]));
        const places = [...new Set(chart.series.map(s => s.context_label || s.source_curve_id))];
        const palette = ['#1677ff', '#e68a00', '#7a52cc', '#159f75', '#d84a6e', '#6b7b3d'];
        instance.setOption({
            animationDuration: 250,
            // Reserve a deliberately generous footer: x labels, the axis name,
            // then a full blank line before the range slider. ECharts measures
            // names using the rendered font, so a fixed large grid bottom is
            // more reliable than relying on nameGap alone.
            grid: { left: 58, right: 22, top: 36, bottom: 132 },
            tooltip: { trigger: 'axis', valueFormatter: v => `${Number(v).toFixed(2)} ${chart.y.unit}` },
            legend: { bottom: 28, type: 'scroll' },
            xAxis: { type: 'category', name: `${chart.x.label}${chart.x.unit ? ` (${chart.x.unit})` : ''}`, nameLocation: 'middle', nameGap: 50, data: indexes.map(({ v }) => v) },
            yAxis: { type: 'value', name: chart.y.unit, scale: true },
            dataZoom: [{ type: 'inside', xAxisIndex: 0 }, { type: 'slider', xAxisIndex: 0, bottom: 8, height: 17 }],
            series: chart.series.filter(s => s.visible).map(s => {
                const color = palette[places.indexOf(s.context_label || s.source_curve_id) % palette.length];
                const night = s.short_id === 'night_lst';
                return {
                id: s.id, name: s.name, type: 'line', smooth: false, showSymbol: true,
                lineStyle: { color, type: night ? 'dashed' : 'solid', width: 2.5 },
                itemStyle: { color },
                // A model-predicted baseline is a reference, not another
                // observed series. It is visible by default as a quiet
                // horizontal line; in relative mode it correctly sits at 0.
                markLine: {
                    symbol: 'none', silent: true,
                    lineStyle: { color, type: 'dotted', width: 1, opacity: 0.65 },
                    label: { show: true, position: 'insideEndTop', color, fontSize: 10,
                        formatter: chart.y.mode === 'delta_from_baseline' ? 'Baseline 0 °C' : `Baseline ${Number(s.baseline).toFixed(2)} °C` },
                    data: [{ yAxis: chart.y.mode === 'delta_from_baseline' ? 0 : s.baseline }],
                },
                data: indexes.map(({ i }) => s.values[i]),
                };
            }),
        }, true);
    }

    _download(chartId) {
        const chart = this.instances.get(chartId);
        if (!chart) return;
        const link = document.createElement('a');
        link.href = chart.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: '#ffffff' });
        link.download = `${chartId}.png`;
        link.click();
    }

}
