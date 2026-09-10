const origin = location.protocol === 'file:' ? 'http://127.0.0.1:8200' : location.origin;
const nav = document.querySelector('.topnav');
if(nav)addEventListener('scroll',()=>nav.classList.toggle('is-scrolled',scrollY>12),{passive:true});

// Lightweight bilingual presentation layer. It only changes copy; existing links,
// query handling, map navigation, and viewer behavior remain unchanged.
const translations={
  en:{
    nav:['Capabilities','Analyze','Evidence','Ask'],open:'Open map',
    heroInput:'Ask HeatScope about Tokyo’s urban heat environment…',heroButton:'Start analysis →',
    heroIntro:'Explore, explain, and simulate urban heat through real Tokyo data, spatial analysis, and machine learning.',
    heroFlow:'Real spatial data <b>→</b> Spatial statistics <b>→</b> RF model <b>→</b> Planning knowledge',
    exploreTitle:'One city,<br><em>more than one heat map.</em>',
    exploreCopy:'Start with daytime and nighttime LST, then move through green and water, urban form, and population activity. Each layer can become a real spatial input for the Agent.',
    exploreDl:['Thermal environment','Daytime LST · Nighttime LST · Day–night gap','Natural environment','NDVI · Water ratio · Distance to coast / river · Elevation','Urban morphology','Building height · Building coverage · Road length · SVF','Social context','Total population · Population density · Age structure'],
    exploreButton:'Explore real layers →',exploreCaption:'Conceptual guide',
    capabilitiesTitle:'From observation to action,<br><em>in one connected workflow.</em>',capabilitiesCopy:'HeatScope is a product guide: natural language calls real data, spatial tools, models, and official knowledge—not just generated text.',
    cards:[['01 / EXPLORE','Explore city data','View daytime and nighttime LST, the day–night gap, NDVI, water, urban form, and population context; compare areas directly.','VIEW EXPLANATION ↓'],['02 / ANALYZE','Analyze spatial patterns','Use spatial analysis to identify significant clusters, spatial structure, and local anomalies.','VIEW EXPLANATION ↓'],['03 / EXPLAIN','Explain the heat environment','Use the RF model and urban climate mechanisms to understand why a place is hotter.','VIEW EXPLANATION ↓'],['04 / PLAN','Test planning scenarios','Adjust green space, building coverage, building height, or water and compare model-based scenarios.','VIEW EXPLANATION ↓'],['05 / POLICY','Interpret planning policy','Search official heat-environment and planning guidance so recommendations return to traceable policy evidence.','VIEW EXPLANATION ↓']],
    analyzeTitle:'From temperature patterns,<br><em>to spatial structure.</em>',analyzeCopy:'HeatScope turns natural-language questions into spatial analysis and produces interactive, traceable map evidence.',workflowTitle:'FROM QUESTION TO SPATIAL EVIDENCE',workflowCopy:'The AI Agent selects and calls data, statistics, models, and knowledge sources.',steps:[['01','User question','Ask a question about the urban heat environment in natural language.'],['02','Spatial data and tools','Read grids, layers, and area context.'],['03','Analysis and models','Run spatial statistics or RF prediction and explanation.'],['04','Map and evidence','Deliver visible, verifiable results.']],
    planTitle:'Different conditions,<br><em>temperature simulation.<br>Reject guesswork.</em>',planCopy:'Buildings, roads, green space, and water affect LST through radiation, heat storage, ventilation, and heat release. Model interpretation makes these relationships discussable.',pipeline:['Ikebukuro · Current urban form','Adjust green space / building coverage / height / water','Call the real RF model to calculate LST change','Generate a verifiable planning scenario'],pipelineNote:'Model values appear only after a real run in the workspace.',liveTitle:'Live urban form demo / Grid 7191',liveHeading:'3D planning scenario model',liveNote:['LIVE VIEWER','Height + Footprint loop'],
    policyTitle:'Let planning recommendations,<br><em>return to official evidence.</em>',policyCopy:'Model interpretation explains form changes; policy knowledge identifies strategies that can be prioritized in urban planning. Together they form an evidence chain in the workspace.',policyButton:'View policy guidance →',policyCard:['OFFICIAL GUIDELINE / 2019','Summer Heat Countermeasures Guide','Issuing body','Tokyo Metropolitan Government','Coverage','Tokyo / 23 wards','Topics','Urban heat island · Heat adaptation · Thermal comfort'],
    finalTitle:'Start with a question.',finalInput:'Ask HeatScope about Tokyo’s urban heat environment…',finalButton:'Open HeatScope →',footer:'Tokyo Urban Heat / Spatial AI',footerMap:'Open map →'
  },
  zh:null
};
translations.zh={nav:['能力','分析','证据','提问'],open:'打开地图',heroInput:'问问 HeatScope 关于东京城市热环境的问题……',heroButton:'开始分析 →',heroIntro:'通过东京真实城市数据、空间分析与机器学习模型，探索、解释并模拟城市热环境。',heroFlow:'真实空间数据 <b>→</b> 空间统计 <b>→</b> RF 模型 <b>→</b> 规划知识',exploreTitle:'一座城市，<br><em>不止一张热力图。</em>',exploreCopy:'从昼夜 LST 出发，逐层进入绿地与水体、城市形态和人口活动背景。每一层都可以作为 Agent 的真实空间分析输入。',exploreDl:['热环境','昼间 LST · 夜间 LST · 昼夜温差','自然环境','NDVI · 水体比例 · 距海岸 / 河流距离 · 高程','城市形态','建筑高度 · 建筑覆盖率 · 道路长度 · SVF','社会背景','人口总数 · 人口密度 · 年龄结构'],exploreButton:'探索真实图层 →',exploreCaption:'概念导览图',capabilitiesTitle:'从观察到行动，<br><em>在一个工作流中完成。</em>',capabilitiesCopy:'这是 HeatScope 的产品目录：自然语言会调用真实数据、空间工具、模型与官方知识，而不只是生成文字。',cards:[['01 / EXPLORE','探索城市数据','查看昼夜 LST、昼夜温差，以及 NDVI、水体、建筑形态与人口背景；也可直接比较区域。','查看说明 ↓'],['02 / ANALYZE','分析空间格局','通过空间分析识别显著聚集、空间结构与局部异常。','查看说明 ↓'],['03 / EXPLAIN','解释热环境机制','以 RF 模型和城市气候机制回答地点为何更热。','查看说明 ↓'],['04 / PLAN','测试规划情景','调整绿地、建筑覆盖率、建筑高度或水体，比较有模型依据的情景。','查看说明 ↓'],['05 / POLICY','解读规划政策','检索官方热环境与规划指南，让建议回到可追溯的政策依据。','查看说明 ↓']],analyzeTitle:'从温度分布，<br><em>到空间结构。</em>',analyzeCopy:'HeatScope 将自然语言问题转化为空间分析，生成可交互、可追溯的地图证据。',workflowTitle:'FROM QUESTION TO SPATIAL EVIDENCE',workflowCopy:'AI Agent 选择并调用数据、统计、模型与知识来源。',steps:[['01','用户问题','用自然语言提出热环境问题。'],['02','空间数据与工具','读取网格、图层和区域语境。'],['03','分析与模型','运行统计或 RF 预测与解释。'],['04','地图与证据','交付可见、可核验的结果。']],planTitle:'不同条件，<br><em>温度模拟。<br>拒绝经验主义。</em>',planCopy:'建筑、道路、绿地与水体通过辐射、蓄热、通风与散热等过程影响 LST。模型解释让这种关系可以被定位和讨论。',pipeline:['池袋 · 当前城市形态','调整绿地 / 建筑覆盖率 / 高度 / 水体','调用真实 RF 模型计算 LST 变化','生成可核验的规划情景'],pipelineNote:'模型数值仅在工作台真实运行后显示',liveTitle:'LIVE URBAN FORM DEMO / GRID 7191',liveHeading:'规划情景的三维形态模型',liveNote:['LIVE VIEWER','Height + Footprint loop'],policyTitle:'让策略建议，<br><em>回到官方依据。</em>',policyCopy:'模型解释的是形态变化；政策知识回答的是城市规划中可以优先采用什么策略。两者在工作台中共同构成建议的证据链。',policyButton:'查看政策建议 →',policyCard:['OFFICIAL GUIDELINE / 2019','夏の暑さ対策の手引','发布机构','东京都环境局','覆盖范围','东京 / 东京 23 区','主题','城市热岛、热适应、热舒适'],finalTitle:'从一个问题开始。',finalInput:'问问 HeatScope 关于东京城市热环境的问题……',finalButton:'打开 HeatScope →',footer:'Tokyo Urban Heat / Spatial AI',footerMap:'打开地图 →'};

Object.assign(translations.en,{steps:[['01','User Question','Ask a question about the urban heat environment in natural language.'],['02','LLM Planning','The LLM understands the question and selects appropriate data, tools, and an analysis path.'],['03','Tool Execution','Call real data, spatial-analysis, visualization, or map tools.'],['04','Result Validation','Check whether results meet the question requirements; if not, step back to replan or call other tools.'],['05','Visualization Presentation','Present verifiable analysis results through maps, charts, and interactive views.']]});
Object.assign(translations.zh,{steps:[['01','用户问题','用自然语言提出城市热环境问题。'],['02','LLM 规划','LLM 理解问题，选择合适的数据、工具和分析路径。'],['03','工具调用','调用真实数据、空间分析工具、可视化工具或地图工具。'],['04','结果判断','检查结果是否满足问题要求；如果不理想，则回退并重新规划或调用其他工具。'],['05','可视化呈现','通过地图、图表和交互界面呈现可验证的分析结果。']]});
Object.assign(translations.en,{analyzeTitle:'From question to validation,<br><em>build heat evidence.</em>'});
Object.assign(translations.zh,{analyzeTitle:'从提问到验证，<br><em>形成热环境证据。</em>'});
Object.assign(translations.en,{planTitle:'<em>Temperature simulation.<br>Reject guesswork.</em>',pipeline:['Current urban form','Adjust green space / building coverage / height / water','Call the real RF model to calculate LST change','Generate a verifiable planning scenario'],capabilitiesCopy:'HeatScope turns natural-language questions into actions with real data, spatial tools, models, and official knowledge—not just generated text.'});
Object.assign(translations.zh,{planTitle:'<em>温度模拟。<br>拒绝经验主义。</em>',pipeline:['当前城市形态','调整绿地 / 建筑覆盖率 / 高度 / 水体','调用真实 RF 模型计算 LST 变化','生成可核验的规划情景'],capabilitiesCopy:'HeatScope 将自然语言问题转化为行动，调用真实数据、空间工具、模型与官方知识，而不只是生成文字。'});
translations.en.exploreCopy='Start with daytime and nighttime LST, then move through green and water, urban morphology, and population activity. Each layer can become a real spatial input for the Agent.';
translations.en.cards[0][2]='View daytime and nighttime LST, the day–night gap, NDVI, water, urban morphology, and population context; compare areas directly.';
translations.en.planCopy='Buildings, roads, green space, and water affect LST through radiation, heat storage, ventilation, and heat release. Morphology-aware model interpretation makes these relationships discussable.';
translations.en.cards[3][1]='Model cooling interventions';
translations.en.cards[4][1]='Plan with evidence';
translations.zh.cards[3][1]='模拟降温干预';
translations.zh.cards[4][1]='以证据支持规划决策';
translations.en.nav=['EXPLORE','ANALYZE','EXPLAIN','SIMULATE','GUIDE'];
translations.zh.nav=['探索','分析','解释','模拟','指南'];
translations.en.policyTitle='Ground planning recommendations<br><em>in planning guidance.</em>';
translations.zh.policyTitle='让策略建议，<br><em>回到规划指南。</em>';

function applyLanguage(lang){const t=translations[lang];if(!t)return;const extra=lang==='en'?{heroTitle:'Talk to the map.<br><em>Understand urban heat.</em>',chips:['Where are Tokyo’s heat hotspots?','Why is Sakuradai so hot?','What if Ikebukuro had more green space?'],evidenceTitle:'How urban form<br><em>shapes surface temperature.</em>',evidenceCopy:'Buildings, roads, green space, and water affect LST through radiation, heat storage, ventilation, and heat release. Model interpretation makes these relationships discussable.',evidenceLink:'Explain Sakuradai with the real model →',figCaption:'EXPLORE THE CITY AS LAYERS',exploreAlt:'Layered exploration diagram showing Tokyo basemap, urban form, green and water cover, activity context, and daytime LST'}:{heroTitle:'与地图对话。<br><em>读懂城市热环境。</em>',chips:['东京的热聚集区在哪里？','为什么樱台这么热？','如果池袋增加更多绿地，会怎样？'],evidenceTitle:'城市形态如何<br><em>塑造地表温度？</em>',evidenceCopy:'建筑、道路、绿地与水体通过辐射、蓄热、通风与散热等过程影响 LST。模型解释让这种关系可以被定位和讨论。',evidenceLink:'用真实模型解释樱台 →',figCaption:'EXPLORE THE CITY AS LAYERS',exploreAlt:'由底图、城市形态、绿地水体、活动背景和东京昼间 LST 组成的城市图层探索示意'};document.documentElement.lang=lang==='en'?'en':'zh-CN';document.title=lang==='en'?'HeatScope | Urban Heat Spatial AI':'HeatScope｜城市热环境 Spatial AI';
  const navLinks=document.querySelectorAll('.nav nav a');t.nav.forEach((v,i)=>{if(navLinks[i])navLinks[i].textContent=v});
  const navButton=document.querySelector('.nav .button.small');if(navButton)navButton.innerHTML=`${t.open} <b>→</b>`;
  const hero=document.querySelector('#heroInput');if(hero)hero.placeholder=t.heroInput;const heroButton=document.querySelector('#heroQuery button');if(heroButton)heroButton.textContent=t.heroButton;const heroTitle=document.querySelector('.hero h1');if(heroTitle)heroTitle.innerHTML=extra.heroTitle;document.querySelectorAll('.chips [data-prompt]').forEach((el,i)=>{if(extra.chips[i])el.textContent=extra.chips[i]});
  const ctx=document.querySelector('.ask-context');if(ctx){ctx.children[0].textContent=t.heroIntro;ctx.children[1].innerHTML=t.heroFlow}
  const explore=document.querySelector('#explore');if(explore){explore.querySelector('h2').innerHTML=t.exploreTitle;explore.querySelector('.explore-copy>p:nth-of-type(2)').textContent=t.exploreCopy;const d=explore.querySelectorAll('dl>*');t.exploreDl.forEach((v,i)=>{if(d[i])d[i].textContent=v});explore.querySelector('.button').textContent=t.exploreButton;const image=explore.querySelector('img');if(image)image.alt=extra.exploreAlt;const caption=explore.querySelector('figcaption');if(caption){caption.childNodes[0].textContent=extra.figCaption+' ';caption.querySelector('span').textContent=t.exploreCaption}}
  const cap=document.querySelector('#capabilities');if(cap){cap.querySelector('h2').innerHTML=t.capabilitiesTitle;cap.querySelector('.section-head>p').textContent=t.capabilitiesCopy;cap.querySelectorAll('.feature').forEach((el,i)=>{const c=t.cards[i];if(!c)return;el.querySelector('h3').textContent=c[1];el.querySelector('p').textContent=c[2];el.querySelector('b').textContent=c[3]})}
  const analyze=document.querySelector('#analyze');if(analyze){analyze.querySelector('h2').innerHTML=t.analyzeTitle;analyze.querySelector('.analysis-lead>p').textContent=t.analyzeCopy;analyze.querySelector('.analysis-workflow-head .eyebrow').textContent=t.workflowTitle;analyze.querySelector('.analysis-workflow-head>p:last-child').textContent=t.workflowCopy;analyze.querySelectorAll('.steps>div').forEach((el,i)=>{const s=t.steps[i];if(s){el.querySelector('h3').textContent=s[1];el.querySelector('p').textContent=s[2]}})}
  const evidence=document.querySelector('#evidence');if(evidence){evidence.querySelector('h2').innerHTML=extra.evidenceTitle;evidence.querySelector('.intelligence-grid>div:first-child>p:not(.eyebrow)').textContent=extra.evidenceCopy;evidence.querySelector('.text-link').textContent=extra.evidenceLink}
  const plan=document.querySelector('#plan');if(plan){plan.querySelector('h2').innerHTML=t.planTitle;plan.querySelector('.intelligence-grid>div:first-child>p:not(.eyebrow)').textContent=t.planCopy;plan.querySelectorAll('.pipeline>div').forEach((el,i)=>{if(t.pipeline[i])el.textContent=t.pipeline[i]});plan.querySelector('.pipeline small').textContent=t.pipelineNote}
  const live=document.querySelector('.live-scenario');if(live){live.querySelector('.scenario-model-title .eyebrow').textContent=t.liveTitle;live.querySelector('h3').textContent=t.liveHeading;live.querySelectorAll('.viewer-note span').forEach((el,i)=>{if(t.liveNote[i])el.textContent=t.liveNote[i]})}
  const policy=document.querySelector('#policy');if(policy){policy.querySelector('h2').innerHTML=t.policyTitle;policy.querySelector('.section>div>p:not(.eyebrow)').textContent=t.policyCopy;policy.querySelector('.button').textContent=t.policyButton;const article=policy.querySelector('article');if(article){article.querySelector('span').textContent=t.policyCard[0];article.querySelector('h3').textContent=t.policyCard[1];article.querySelector('p').textContent=lang==='en'?'Official heat and planning guidance':'Guide to Summer Heat Countermeasures';const dl=article.querySelectorAll('dl>*');[t.policyCard[2],t.policyCard[3],t.policyCard[4],t.policyCard[5],t.policyCard[6],t.policyCard[7]].forEach((v,i)=>{if(dl[i])dl[i].textContent=v})}}
  const final=document.querySelector('#finalQuery');if(final){final.querySelector('input').placeholder=t.finalInput;final.querySelector('button').textContent=t.finalButton}const foot=document.querySelector('footer');if(foot){foot.children[1].textContent=t.footer;foot.children[2].textContent=t.footerMap}
  const toggle=document.querySelector('#languageToggle');if(toggle){toggle.textContent=lang==='en'?'中':'EN';toggle.setAttribute('aria-label',lang==='en'?'切换到中文':'Switch to English')}try{localStorage.setItem('heatscope-language',lang)}catch{}
}
const baseApplyLanguage=applyLanguage;
applyLanguage=function(lang){
  baseApplyLanguage(lang);
  const navMenu=document.querySelector('.nav nav');
  const navTargets=['#explore','#analyze','#evidence','#plan','#policy'];
  if(navMenu){
    while(navMenu.children.length<navTargets.length)navMenu.appendChild(document.createElement('a'));
    [...navMenu.children].slice(0,navTargets.length).forEach((link,index)=>{
      link.href=navTargets[index];
      link.textContent=translations[lang].nav[index];
    });
  }
  const featureLabels=document.querySelectorAll('#capabilities .feature > span');
  if(featureLabels[3])featureLabels[3].textContent='04 / SIMULATE';
  if(featureLabels[4])featureLabels[4].textContent='05 / GUIDE';
  if(lang==='en'){
    const evidenceTitle=document.querySelector('#evidence h2');
    if(evidenceTitle)evidenceTitle.innerHTML='How urban morphology<br><em>shapes surface temperature.</em>';
    const exploreImage=document.querySelector('#explore img');
    if(exploreImage)exploreImage.alt='Layered exploration diagram showing Tokyo basemap, urban morphology, green and water cover, activity context, and daytime LST';
  }
};
const savedLanguage=(()=>{try{return localStorage.getItem('heatscope-language')}catch{return null}})();
const languageToggle=document.querySelector('#languageToggle');if(languageToggle)languageToggle.addEventListener('click',()=>applyLanguage((document.documentElement.lang||'en').startsWith('en')?'zh':'en'));applyLanguage(savedLanguage||'en');
const mapUrl = (query, extra = {}) => `${origin}/?${new URLSearchParams({mode:'map', q: query, ...extra})}`;
const previewCases = [
  {match:/热聚集|hotspot|cluster/i,title:'识别东京的热聚集区',text:'读取昼间 LST 网格并运行 Local Moran’s I，识别显著 HH / LL / HL / LH 格局。',steps:['读取昼间 LST','计算空间格局','生成 LISA 结果层'],extra:{view:'analysis',tool:'local_moran'}},
  {match:/池袋|丸之内|ikebukuro|marunouchi/i,title:'比较池袋与丸之内',text:'汇总两个区域的热环境与可用城市形态指标，进入地图查看真实对比。',steps:['定位比较区域','汇总 LST 与城市字段','生成对比解释'],extra:{view:'compare'}},
  {match:/樱台|sakuradai/i,title:'诊断樱台的高温原因',text:'调用城市形态—LST 随机森林模型，查看预测与局地解释。',steps:['读取网格特征','运行 RF 诊断','生成模型解释'],extra:{view:'diagnose'}},
  {match:/绿地|green space/i,title:'模拟增加绿地的情景',text:'以当前城市形态为基线，在工作台调用模型计算情景下的温度变化。',steps:['读取基线','调整情景参数','比较模型预测'],extra:{view:'simulate'}}
];
const capabilities=document.querySelector('#capabilities');
const exploreZone=document.querySelector('.explore-zone');
if(capabilities&&exploreZone)exploreZone.before(capabilities);
function startAnalysis(query){const item=previewCases.find(x=>x.match.test(query))||{extra:{}};location.href=mapUrl(query,item.extra);}
document.querySelector('#heroQuery').addEventListener('submit',e=>{e.preventDefault();const q=document.querySelector('#heroInput').value.trim();if(q)startAnalysis(q)});
document.querySelectorAll('.chips [data-prompt]').forEach(button=>button.addEventListener('click',()=>{const input=document.querySelector('#heroInput');input.value=button.dataset.prompt;input.focus()}));
document.querySelector('#finalQuery').addEventListener('submit',e=>{e.preventDefault();const input=e.currentTarget.querySelector('input');if(input.value.trim())location.href=mapUrl(input.value.trim())});
document.querySelectorAll('a[href^="/?mode=map"]').forEach(a=>a.addEventListener('click',e=>{if(location.protocol==='file:'){e.preventDefault();location.href=origin+a.getAttribute('href')}}));
document.querySelectorAll('.layer-tabs button').forEach(button=>button.addEventListener('click',()=>{document.querySelectorAll('.layer-tabs button').forEach(x=>x.classList.remove('active'));button.classList.add('active');document.querySelector('.map-state').textContent=`● ${button.dataset.layer}`}));
const observer=new IntersectionObserver(entries=>entries.forEach(entry=>{if(entry.isIntersecting){entry.target.animate([{opacity:0,transform:'translateY(20px)'},{opacity:1,transform:'translateY(0)'}],{duration:600,easing:'ease-out',fill:'both'});observer.unobserve(entry.target)}}),{threshold:.12});document.querySelectorAll('.task,.official,.spatial-ai,.credibility,.questions').forEach(el=>observer.observe(el));
