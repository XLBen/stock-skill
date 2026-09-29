---
name: stock-analysis
description: 泛金融报告分析全流程 skill。凡用户要求写/出/修改任何报告（投资研究/个股深度/资产研究/估值分析/财报解读/回测/总结报告，股票/基金/利率/地产/加密/收藏品等任意对象）即使用本 skill；亦覆盖行情/财务/研报数据抓取、网格/定投回测、板块筛选、商誉减值、指增/红利/AH 溢价研究与 Word（.docx）报告生成。核心：8 维画像推导方法集与报告蓝图、盈利预测与估值确定性算子（数字由代码算）、苏格拉底质询（数据说话的对抗审查）、复盘闭环（结论落档校准）。
---

# 股票分析（Stock Analysis）

泛金融报告 skill：**北极星是一份可用的报告**。任何对象（A股/房价/比特币/手办）先做 8 维画像，规则库（reference/library/，JSON 数据驱动）推导方法集/数据源/报告蓝图；**预测与估值数字由算子库计算，叙事由 LLM 写**；报告假设经受苏格拉底质询（以数据立状、不到底不停止、背反则记录）；结论自动落档复盘，第 N 份报告站在第 N-1 份肩上。

## 使用时机（提到报告即触发）

- **用户提到"报告"**（写/出/改/复盘任何投资研究、个股深度、资产研究、估值、财报、回测、总结报告）→ 必走本 skill
- **用户要求更新/复查某资产**（"锦江现在怎么样了""复查XX"）→ 走**更新报告**类型（增量复核，复用档案）
- 用户要求抓取行情/财务/估值/研报/公告/现货价/宏观数据
- 用户要求分析任意资产对象（非预设档案时走 8 问画像）

## 流程分级（按蓝图 flow 字段，拒绝过度流程）

| 级别 | 蓝图 | 流程 |
|---|---|---|
| full 全流程 | equity_deep_8ch / asset_research / rental_asset | 11 步全走：两会话质询（第7步假设+第10步校对） |
| standard 标准 | theme_quant / update_report | 跳过第 7 步（无盈利预测假设），仅第 10 步校对会话 |
| minimal 最小 | strategy_manual / educational / decision_report | 跳过第 7、10 步（无质询），仅基础分析→报告→QA |

## 标准流水线（11 步，full 级全走；standard/minimal 按上表跳过）

1. **画像与档案载入**：明确标的、时间范围、报告类型（深度研究/主题量化/资产研究/策略手册/科普/决策测算/**更新报告**）。加载预设档案（`reference/library/profiles.json`）或 8 问画像（`profile_lib.QUESTIONS`）。**同资产先 `review_lib.load_dossier()`**——有档案则载入前次结论生成复盘素材；**更新报告类型**：`derive(画像,'更新报告')` → update_report 蓝图，直接复用 `dossier.inherited` 可继承资产（可比清单/口径/行业线索），禁止重跑全量调研，变化分析只列新旧对比。**建流水线审计 `flow_log.FlowLog(scope)`**（每步 step() 计时，质询/回流/驳回 event() 记录）。
2. **推导**：`profile_lib.derive(profile, report_type)` → 方法集/源集/蓝图/回测规则/QA。只用推导方法集；库外新方法须过证据关（usage_probe）并写回 methods.json。
3. **方法信号刷新**：`python scripts/fetch_method_signals.py`（DCF 类报告用 Damodaran 锚）。
4. **数据抓取**：按推导源集用 `scripts/fetch_lib.py`（缓存优先，`save_json` 带 `_meta`，幂等覆盖）。商誉/减持/业绩预告类必用 `cninfo_notices`（一手公告）；周期股用 `spot_price(keyword)`（现货价，失败必须标注降级）；行业分析用 `macro_industry(indicator)`。
5. **基础分析**：行业（空间/驱动/格局/产业链）、业务量价拆分与护城河证据、财务质量（杜邦分解/三表联动/净利-现金流匹配）。每个论断配可溯源数字。
6. **预测建模**（报告心脏，禁止 LLM 手算）：个股用 `forecast_lib.build_equity_forecast`（分业务量×价→毛利率→费用率→3年净利/EPS/ROE）；租金资产用 `build_rental_forecast`（3年NOI）；另类资产用 `build_supply_demand_balance`（供需平衡表）。**每项假设必须是 `Assumption(value, basis, tag, probability)`**，tag∈[实证]/[推断]/[观点]，裸（估）直接报错。`save_forecast` 落盘。
7. **假设质询（苏格拉底·写作前）**（只攻承重论点：预测假设/估值参数/核心逻辑）：`socratic_lib.new_session(subject, load_bearing_claims)` → 用 `reference/templates/socratic_challenger.md` 模板发起 Task 子代理质询（武装质询者可自主抓数，数据必须落盘 `challenge_r{轮}_{id}.json`）→ `submit_challenges` 规则裁决准入（只打承重墙/以数据立状/一事不再理）→ 立论者 `defend`（data=磁盘证据文件/revise=修正/unknown=留白；**note 必填理由**；替代解读/隐含前提类必填 crux 且只认区分性新证据）→ 循环至 `should_continue` 为 False。**回流协议（H1 铁律）**：`revised_assumption_claims(s)` 非空（revise 带 assumption_ref）时，必须重跑 `forecast_lib` 重建预测、再进第 8 步估值——禁止沿用被击穿的旧数字。会话落盘 `socratic_{资产}_假设.json`（中断可恢复、统计合并有据）。
8. **估值**：`valuation_lib.run_derived(derive结果, ctx, params)`，ctx.data 带 refs（来源文件+字段）。前向锚优先（预测EPS×可比PE、DCF 用预测 FCF、NOI÷cap rate），每个结果带 provenance。**多方法合成用 `weighted_synthesis(results, weights)`（权重给理由，中枢/区间禁止手算）**。`crosscheck()` 多源同指标误差>1% 必须在报告说明取舍；跑 `dispute_analysis`；用 `flip_point` 算翻车点。
9. **图表 + 论点树 + 报告草稿**：`chart_helpers`（先 `setup_cn()`，`figN_主题.png`，每图必须被正文引用，**img 必带 source= 参数**——图注自动追加"资料来源"，QA 检查）。**9a 建树**：`thesis_lib.build_thesis`（核心结论→3~5 承重柱→每柱证据映射到章节/图/数据文件，`validate_thesis` 通过后落盘 thesis.json；柱的来源=预测假设/估值锚/竞争优势/行业驱动）。**9b 写作遵循树**：每柱在正文有落点、证据映射到具体图表/数据；反方章节由质询记录驱动，附录含 `provenance_table()` + `socratic_stats_table()` + `data_asof_table(doc, cache_meta_table(本次全部数据文件))`。草稿先留在内存/暂存，不急于终稿交付。
10. **报告校对=解读对抗（苏格拉底·写作后）**：`dump_doc_text(草稿, 草稿.txt)`（带【H1】【H2】【表】【图注】结构标记）→ 用 `reference/templates/report_reviewer.md` 模板发起**对抗性审稿人** Task 子代理。**两阶段协议：先通读全文重建论点树并列全局问题（架构缺陷/跨章节张力/证据合力配比/联合脆弱），再取致命 2~6 点做 pillar 级质询——禁止逐句扫描**。机械校对（数字一致性/图注编号）归第 11 步 QA，不占审稿火力。**双方武装**：审稿人与立论者都可现抓数据（每轮合计 ≤3 次，`fetch_budget_left()`），落盘 `review_r{轮}_{id}.json` 才具资格。裁决纪律：`register_discriminating_evidence()` 登记区分性证据后 `defend(data)` 才能裁决解读类质询；defend 必填理由；双读法不可通约 → 自动背反记录。审核会话 load_bearing_claims=**承重柱+核心结论**（从 thesis.json 取，不手挑）；会话落盘 `socratic_{资产}_校对.json`。**修正草稿后重新 dump，第 2 轮起增量审（只审修改处+未决问题）**，至收敛 → 按 `thesis_lib.revision_checklist()` 逐项修订（正文/反方章节并集更新+承重柱总览/附录两会话统计重生成/树状态更新）→ 终稿 **`save_stage(doc, 文件名, subject=资产, review=结论entry)`**（自动落档复盘）。区分性新数据反哺正文。
11. **QA 质检**（0 错误才通过）：
    - `python scripts/check_report_depth.py 报告.docx --type 蓝图id --trace-dir 数据目录`（空章节/字数/强制章节/蓝图必备章/**数字溯源**：表格+正文证据句 vs 算子输出池，含估值数字而无 results/forecast 文件直接 FAIL/图表引用/证据标签/数字密度）
    - `python scripts/usage_probe.py`（有研报覆盖的资产必须跑；方法命中率≥30% 视为业界常用）
    - `python scripts/cache_status.py --strict`（stale 数据标注"数据截止日期"）
    - `python scripts/check_delivery.py`；`python scripts/render_check.py 报告.docx`（有 soffice 时渲染目检）
    - **审计收尾**：`flow_log.save()`（每步耗时/质询轮数/回流次数/驳回数落盘 pipeline_log_{scope}.json，summary 记入报告 meta"生成成本"）；多次复盘后可跑 `review_lib.error_patterns()` 看跨档案错误模式（哪类评级总失误——方法自学习入口）
    - 报告先落 `暂存区/`，用户确认后**移动**到 `分类区/{主题}/`

## 脚本使用（scripts/ 与 SKILL.md 同级）

```python
# 1. 画像/推导/档案
from profile_lib import load_profile, derive, dispute_analysis
from review_lib import load_dossier, prior_review_table, calibration
d = derive(load_profile('a_share_stock'), '深度研究')   # 蓝图=equity_deep_8ch

# 2. 盈利预测（心脏）
from forecast_lib import Assumption, build_equity_forecast, save_forecast, scenario_table
a = Assumption(0.12, basis='行业8%+份额提升(市占5→7%)', tag='[推断]', probability=0.6)
fc = build_equity_forecast(years=[2026,2027,2028],
    segments=[{'name':'主业','method':'growth','base':100.0,'assumptions':{'growth':a}}],
    gross_margin=Assumption(0.32, basis='近5年30~34%中枢', tag='[实证]', probability=0.7),
    opex_ratio=Assumption(0.12, basis='费用率稳定', tag='[实证]', probability=0.7),
    tax_rate=Assumption(0.15, basis='高新税率', tag='[实证]', probability=0.9),
    shares=12.5, equity_base=90.0, scenarios={'保守':0.25,'中性':0.5,'乐观':0.25})
save_forecast(fc, 'data/forecast_xx.json', scope='600754')

# 3. 估值算子（数字由代码算）
from valuation_lib import run_derived, crosscheck, provenance_rows, flip_point, weighted_synthesis
ctx = {'data': {'shares':12.5, 'eps_f':fc['central']['eps'], 'peers':[...], 'fcf_f':[...],
                'pe_hist':[...], 'net_debt':20.0},
       'refs': {'eps_f': {'file':'data/forecast_xx.json','field':'central.eps','fetched_at':'...'}}}
results, skipped = run_derived(d, ctx)          # 只跑推导方法集内、数据就绪的算子
syn = weighted_synthesis(results, {'relative_peer':0.4, 'dcf':0.35, 'ddm':0.25})  # 合成中枢禁止手算
crosscheck({'em':131.2,'tx':131.9,'hand':130.5}, metric='mcap')   # >1% 告警须说明取舍
if revised_assumption_claims(s):                # H1 回流：假设被击穿必须重建预测再估值
    fc = build_equity_forecast(...修正后假设...); save_forecast(fc, 'data/forecast_xx.json')

# 4. 假设质询（写作前）+ 报告校对质询（写作后）
from socratic_lib import new_session, submit_challenges, defend, should_continue, export_for_report
s = new_session('XX股份', ['2028年EPS 2.6元', '合理区间10~13元'])   # 承重论点
# → Task 子代理按 socratic_challenger.md 模板质询（可抓数，落盘 challenge_r*.json）
adm = submit_challenges(s, challenges_json)     # 规则裁决：承重墙/数据立状/一事不再理
defend(s, adm[0]['id'], 'data', evidence_file='data/xx_fin.json')  # 或 revise/unknown
# 循环至 should_continue(s)[0]==False；export_for_report(s) 喂反方章节与附录统计
# ……第9步草稿完成后——校对=解读对抗（对抗性审稿人，report_reviewer.md 模板）：
dump_doc_text(doc, 'data/xx_draft.txt')          # 或传 .docx 路径
s2 = new_session('XX股份·校对', load_bearing_claims=从报告提取的关键论断清单)
# → 审稿人子代理读 xx_draft.txt，主攻替代解读/隐含前提/反例（必填 crux），可抓数落盘 review_r*.json
adm2 = submit_challenges(s2, review_json)        # 缺 crux 的解读类质询被自动驳回
# 立论者对抗：区分性证据先登记再裁决；修正走 revise
register_discriminating_evidence(s2, 'data/review_r1_01.json', purpose='杜邦三因子分辨质量vs杠杆')
defend(s2, adm2[0]['id'], 'data', evidence_file='data/review_r1_01.json',
       note='分解显示周转率+毛利率双升、负债率持平，支持质量读法')
defend(s2, adm2[1]['id'], 'revise', revised_claim='修正后的论断', note='并表因素剔除后内生+5%')
# 每轮新抓取 ≤3 次（fetch_budget_left(s2)）；修正草稿后重新 dump 再审
# 收敛后两会话合并：stats 合并喂 socratic_stats_table，幸存质询（含"同一数字两种读法"）并集进反方章节

# 5. 报告
from docx_helpers import *
doc = new_document(); setup_page(doc, 'XX投资研究报告', '2026-08-30')
cover(doc, 'XX股份（600000.SH）投资研究报告', meta=[...], badge='个股深度研究')
provenance_table(doc, results); socratic_stats_table(doc, export_for_report(s)['stats'])
save_stage(doc, 'XX投资研究报告_20260830.docx', subject='XX股份',
           review={'date':'2026-08-30','rating':'增持','range_low':10,'central':12,
                   'range_high':14,'price_now':11,'expiry':'2027-08-30',
                   'review_triggers':['Q3净利低于预期20%'],
                   'assumptions':[{'desc':'2028 EPS 2.6元','probability':0.6,'trigger':'...'}]})
```

## 关键经验（避免踩坑）

- **铁律一：数字由代码算**——预测/估值数字只出自 forecast_lib/valuation_lib，LLM 手算即违规；多方法合成中枢用 weighted_synthesis，最后一步也不许手算；**质询击穿假设必须回流**（revised_assumption_claims 非空 → 重跑预测再估值，禁止沿用旧数字）；QA 溯源：无算子输出文件而报告含估值数字 = FAIL
- **铁律零：先建树再写作**——thesis.json（结论→承重柱→证据映射）贯穿写作与质询；审核员先通读重建树、pillar 级攻击，禁止逐句扫描式审稿
- **铁律二：假设必带证据链**——[实证]/[推断]/[观点] 标签+依据+概率，裸（估）被库直接拦截；**估值参数（WACC/倍数带/目标股息率/cap rate/单位成本/汇率/情景档位）一律按信号锚（method_signals/Damodaran）或当期数据显式给出并写入假设表——算子对缺参直接报错，无任何硬编码默认值可偷懒**
- **铁律三：反注水**——字数不足时补新论点+新数据源（新抓取/新视角/新对比），禁止扩写旧文本；QA 按证据对象清点（数字密度/图表引用率/标签）
- **铁律四：质询以数据说话**——提不出裁决数据的质询无效；settled 一事不再理；无数据双方就留白；背反（各有数据不可通约）记录进报告而非死循环
- **铁律五：开环结论不入档**——save_stage 的 review 必须带有效期与复查触发条件；同资产新报告必须复盘前次结论（命中/失误/待定+校准率）
- 方法必须来自推导：地产禁 PE 分位（用资本化率/重置成本）；比特币/手办禁 DCF/PE（链上/稀缺溢价/价格指数化）；无路可走用 stats_baseline 并标注"统计性描述"
- 分歧对比原则：中枢偏离>20% 或区间不重叠才做正反论证；分歧来自"失真/慎用"方法时不对比
- 东财批量行情一次 ≤100 个（f9=PE(TTM) f20=总市值 f23=PB）；腾讯 K 线 count≤800；乐咕优先 akshare
- 网格回测必须含 T+1、FIFO、免5 佣金、MC 多市况；周期股 PE 失真以 PB/周期均值/重置成本为主
- 报告数字口径：估算标注（估）；图表全中文；免责声明红色；stale 缓存标注"数据截止日期"
- 新数据源失败时（spot_price/macro_industry 返回 None）必须明示降级或进盲点清单，禁止编造
- 抓取限速 `time.sleep(0.3)`、重试 3 次；缓存幂等覆盖，禁止累积副本

## 环境依赖

依赖见 `requirements.txt`（pandas/numpy/scipy/matplotlib/python-docx/requests/akshare/mini-racer/pypdf/PyMuPDF/yfinance）。渲染自查需 LibreOffice（可选，缺失自动跳过）。

## 自测（修改 scripts/ 或规则库后必跑）

```bash
python scripts/selftest.py --offline   # 离线：画像/预测/算子/质询/复盘/QA 全套
python scripts/selftest.py             # 全量（含联网：信号抓取/研报取证）
```

通过输出全部 PASS、退出码 0；任何失败退出码 1 并列出失败项。
