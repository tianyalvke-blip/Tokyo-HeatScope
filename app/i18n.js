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
        brandTitle: 'Tokyo HeatScope',
        docTitle: 'Tokyo HeatScope · Tokyo Urban Heat GeoAgent',
        placeholder: 'Ask about Tokyo LST…',
        sendBtn: 'Send',
        showChat: 'Show chat',
        welcome: [
            'Talk to the Map. Understand the Heat.',
            '',
            'Natural-Language Intelligence for Urban Heat Planning \u2014 explore daytime and nighttime land surface temperature (LST) across Tokyo\u2019s 23 wards on a 200 m grid.',
            '',
            'Try asking:',
        ].join('\n'),
        examples: [
            'Where are Tokyo\u2019s heat hotspots?',
            'Compare Ikebukuro and Marunouchi',
            'Why is Sakuradai so hot?',
            'What if Ikebukuro had more green space?',
            'What should Bancho prioritize?',
        ],
    },
    ja: {
        brandTitle: '東京ヒートスコープ',
        docTitle: '東京ヒートスコープ · 都市暑熱ジオエージェント',
        placeholder: '東京のLSTについて質問…',
        sendBtn: '送信',
        showChat: 'チャットを表示',
        welcome: [
            '地図と対話し、都市の暑熱を読み解く。',
            '',
            '自然言語で操作する都市暑熱計画支援プラットフォーム。200 m グリッドで東京23区の昼間・夜間の地表面温度（LST）を探索できます。',
            '',
            'たとえば：',
        ].join('\n'),
        examples: [
            '東京の暑熱ホットスポットはどこ？',
            '池袋と丸の内を比較',
            'なぜ桜台は暑い？',
            '池袋の緑地を増やすとどうなる？',
            '番町では何を優先すべき？',
        ],
    },
    zh: {
        brandTitle: '东京智能热洞察',
        docTitle: '东京智能热洞察 · 城市暑热地理智能体',
        placeholder: '询问东京地表温度…',
        sendBtn: '发送',
        showChat: '显示聊天',
        welcome: [
            '与地图对话，读懂城市热环境。',
            '',
            '自然语言驱动的城市热环境规划智能平台。基于 200 m 网格，探索东京23区昼间与夜间的地表温度（LST）。',
            '',
            '你可以试着问：',
        ].join('\n'),
        examples: [
            '东京的热热点在哪里？',
            '比较池袋和丸之内',
            '为什么樱台这么热？',
            '如果池袋增加更多绿地会怎样？',
            '番町应优先采取什么措施？',
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
