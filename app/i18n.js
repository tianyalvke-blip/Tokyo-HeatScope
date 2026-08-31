/**
 * i18n.js — static UI chrome + preset welcome/example strings (EN / JA / ZH).
 *
 * Switches the visible interface: the main title, input placeholder, send
 * button, document title, and the preset welcome message + example prompts.
 * The agent's conversational replies are produced by the LLM and are not
 * re-translated here.
 */

export const LANGS = ['en', 'ja', 'zh'];

const STRINGS = {
    en: {
        brandTitle: 'Urban HeatScope',
        docTitle: 'Urban HeatScope · Urban Heat GeoAgent',
        placeholder: 'Ask about Tokyo LST…',
        sendBtn: 'Send',
        showChat: 'Show chat',
        welcome: [
            'Talk to the Map. Understand Urban Heat.',
            '',
            'A natural language\u2013driven platform for urban heat analysis and planning. Explore daytime and nighttime land surface temperature (LST) across Urban\u2019s 23 wards on a 200 m grid, supported by spatial analysis tools, an urban morphology\u2013LST Random Forest (RF) model, and a planning policy RAG knowledge base. The platform supports heat pattern detection, spatial statistics, causal interpretation, area comparison, scenario simulation, and planning recommendations.',
            '',
            'Try asking:',
        ].join('\n'),
        examples: [
            'Where are the major heat clusters in Tokyo?',
            'Compare the thermal environments of Shinjuku and Marunouchi.',
            'Calculate the day\u2013night LST difference across Tokyo.',
            'Run Local Moran\u2019s I on nighttime LST.',
            'According to the RF model, why is Sakuradai so hot?',
            'How much could LST decrease if Ikebukuro had more green space?',
            'According to the RF model, which urban morphology indicators should Bancho prioritize?',
            'Based on Tokyo\u2019s planning policies and design guidelines, which cooling strategies should Bancho prioritize?',
        ],
    },
    ja: {
        brandTitle: '都市ヒートスコープ',
        docTitle: '都市ヒートスコープ · 都市暑熱ジオエージェント',
        placeholder: '東京のLSTについて質問…',
        sendBtn: '送信',
        showChat: 'チャットを表示',
        welcome: [
            '地図と対話し、都市の暑熱環境を読み解く',
            '',
            '自然言語で操作できる都市暑熱環境分析・計画支援プラットフォームです。200 m グリッドを基盤として、都市23区の昼間・夜間の地表面温度（LST）を分析し、空間分析ツール、都市形態―LST ランダムフォレスト（RF）モデル、および都市計画・政策文書の RAG ナレッジベースを組み合わせて分析を行います。暑熱分布の把握、空間統計、要因分析、地域比較、シナリオシミュレーション、計画施策の提案に対応します。',
            '',
            '例えば、次のように質問できます：',
        ].join('\n'),
        examples: [
            '東京の暑熱クラスターはどこにありますか？',
            '新宿と丸の内の暑熱環境を比較してください。',
            '東京の昼夜LST差を計算してください。',
            '夜間LSTについてローカル・モラン統計量（Local Moran\u2019s I）を計算してください。',
            'RFモデルによると、なぜ桜台は暑いのですか？',
            '池袋の緑地を増やすと、LSTはどの程度低下しますか？',
            'RFモデルによると、番町ではどの都市形態指標を優先的に改善すべきですか？',
            '東京の都市計画政策や設計ガイドラインに基づき、番町ではどのような暑熱緩和策を優先すべきですか？',
        ],
    },
    zh: {
        brandTitle: '城市热洞察',
        docTitle: '城市热洞察 · 城市暑热地理智能体',
        placeholder: '询问东京地表温度…',
        sendBtn: '发送',
        showChat: '显示聊天',
        welcome: [
            '与地图对话，读懂城市热环境',
            '',
            '自然语言驱动的城市热环境规划智能平台。基于 200 m 网格探索城市 23 区昼夜地表温度（LST），结合空间分析工具、城市形态—LST 随机森林（RF）模型与规划政策 RAG 知识库，支持热环境识别、空间统计、成因诊断、区域比较、情景模拟与规划决策。',
            '',
            '你可以试着问：',
        ].join('\n'),
        examples: [
            '东京的热聚集区在哪里？',
            '比较新宿和丸之内的热环境',
            '计算东京各区域的昼夜 LST 温差',
            '计算夜间 LST 的局部莫兰指数（Local Moran\u2019s I）',
            '根据 RF 模型，为什么樱台这么热？',
            '如果池袋增加更多绿地，会降温多少？',
            '根据 RF 模型，番町最值得优化哪些城市形态指标？',
            '结合东京现有规划政策与设计指南，番町应优先采取哪些降温策略？',
        ],
    },
};

let current = 'en';

export function setLang(lang) {
    if (Object.prototype.hasOwnProperty.call(STRINGS, lang)) current = lang;
    return current;
}

export function getLang() {
    return current;
}

export function getStrings() {
    return STRINGS[current];
}

export const LANG_OPTIONS = [
    { code: 'en', label: 'EN' },
    { code: 'ja', label: '日本語' },
    { code: 'zh', label: '中文' },
];
