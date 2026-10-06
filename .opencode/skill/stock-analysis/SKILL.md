---
name: stock-analysis
description: 泛金融报告流水线（lite 省 token 版·零子代理）。用户要求写/改任何报告（投资研究/个股深度/资产研究/估值/财报解读/回测/策略/科普，股票/基金/利率/地产/加密/收藏品等任意对象）或抓行情/财务/研报数据、做 Word（.docx）报告时使用。流程：grill 一批问清需求（唯一人工门）→ 画像推导方法与蓝图 → 抓数冻结 FACTS → 代码算预测估值 → 主上下文顺序写作 + 总监自审一次 → 自我对抗审计 → QA → 编号归档；全程不派子代理；/ask 为零人工路线。
---

# stock-analysis v3.5 · 零子代理省 token 流水线

北极星：**一份可用 docx 报告**。用户只在 grill 批准时在场一次；之后无人值守直到交付。LLM 只做编排与叙事，预测/估值数字一律出自 `forecast_lib`/`valuation_lib` 算子。

## 省 token 原则（硬约束）

1. **需求一轮问清**：默认 1 波 ≤6 问；仅出现模糊词/关键字段缺失才加 1 波，上限 2 波。
2. **零子代理**：不派 Task；抓数、写作、PUA 审问、对抗审计全部由主上下文完成——省去每个子代理的模板+输入包+启动开销。防自证靠纪律（见铁律），不靠独立上下文。
3. **篇幅降档**：按蓝图 `min_words`（full 8000 / standard 6000 / minimal 4000 / update 3000 字符）。不得注水；不够只补新论点+新数据源。
4. **按需读文件**：导航只读 `_registry.json` 与 `WORKSPACE.md`；写作与审计只消费已登记文件，禁全库扫描。
5. **审计 1 轮**：R1 定案；仅当出现 `revise` 击穿假设才 H1 回流重跑预测估值，full 级加 R2 只核修正处。
6. **PUA 只审全稿 1 次**：≤3 专业问 + ≤1 通俗问；驳回自动重写 ≤1 次（须换论述角度），二次直接转审计。

## 命令（项目级 .opencode/command/）

| 命令 | 说明 |
|---|---|
| `/ask 一句话问题` | 零人工：主上下文单轮自推导 brief（字段标 [代理推断]）→ self_approve → full 流水线 |
| `/grill [主题\|编号]` | 需求拷问 1 波 → brief.json → 用户批准（唯一人工门）。已有 brief/已交付 → 提示改用 /drill |
| `/report [编号\|主题\|resume 编号]` | 有已批准 brief → 全自治流水线至交付；无 brief 先 /grill |
| `/drill [编号]` | 追问：draft → 需求变更重审（须重过人工门）；delivered → 回溯拷问 + 复盘落档 |

## 流水线（brief 批准后无人值守，异常走归宿表绝不悬停）

1. **brief**：`workspace_lib.init_workspace(主题)` → `brief_lib.new_brief/record_wave/validate_brief/approve`（self 用 `self_approve`）→ `save_brief`；`set_status(no,'draft',brief_approved=True,flow_level=…)`。
2. **推导**：`profile_lib.derive(画像, brief.report_type)` → 方法集/源集/蓝图/QA；`profile_lib.profile_from_answers` 可得画像。各挂点 `technique_lib.recommend(profile, stage, …)` 自主激活 ≤3 条（full 强制 `premortem`、standard/full 强制 `base_rate`；新增走 `propose_auto`）。`flow_log.FlowLog(scope=no)` 记录。同资产先 `review_lib.load_dossier()` 取 `inherited`。
3. **数据抓取（主上下文）**：按推导源集用 `fetch_lib`（缓存优先，`save_json` 带 _meta）落 `00_cache/`；产 `10_facts/FACTS.md`（指标|数值|口径|asof|来源，禁解读）后**冻结**——先抓数后立论，抓完不再边写边抓（补数须重新登记）。
4. **算数字**：`forecast_lib.Assumption(value,basis,tag,probability,base_rate_ref)` + `build_equity_forecast/build_rental_forecast/build_supply_demand_balance`；`valuation_lib.run_derived` + `weighted_synthesis` + `crosscheck` + `flip_point`。增长类 [推断] 缺 base_rate_ref 自动降级。LLM 禁手算。
5. **写作 + PUA ×1（均主上下文）**：`thesis_lib.build_thesis`（结论→3~5 承重柱→证据映射）落 `40_thesis/`；按蓝图 sections 严格顺序写全稿落 `60_draft/`，每章头写 SELF_ATTACK 三问（空头一击/最心虚数字/动机自检）；承重段挂 `plain_note`、每章 ≥1 `so_what`、全报告 ≥1 `faq_box`、技法/估值首现挂 `method_card`、表前 `table_intro`、图注带 source。随后按 PUA 清单自审全稿一次：第一问自攻验证 → ≤3 专业问（数字出处/So-what/承重）+ ≤1 通俗问，`ManagerLog.checkpoint('全稿', …)` 落盘；驳回重写 ≤1 次（换角度）。
6. **自审 → QA → 归档**：`dump_doc_text` 全文，**只看 dump 不靠记忆**；扮空头通读重建论点树 → R1 质询（full ≥4 条含 ≥1 替代解读/隐含前提；standard ≥3；每根承重柱 ≥1 条或 `exempt_pillar`）→ `socratic_lib` `submit_challenges`/`defend`（自答 data/revise/unknown，data 必须落盘证据文件）→ 三闸 `audit_readiness`/`audit_coverage`/`audit_gate` 全过才许终稿；`revise` 带 `assumption_ref` → H1 回流重跑 forecast→valuation（full 级 R2 核修正处）。QA：`check_report_depth --type <蓝图id> --trace-dir <工作区>`、`check_delivery`、`cache_status --strict`、`render_check`（可选）。交付：`docx_helpers.save_stage(doc, 名, subject, review, report_no=no)` 双写归档 + `flow_log.save(workspace_lib.flow_log_path(no))`；输出摘要（编号/评级区间/审计与 PUA 统计/新技法/`/drill no` 提示）。预算或轮次超限 → `workspace_lib.blocked(no, 卡点, '/report resume no')`。

## 脚本速用

```python
import workspace_lib as wl, brief_lib as blf
e = wl.init_workspace('主题'); no = e['no']
b = blf.new_brief('主题', report_no=no)
blf.record_wave(b, questions=[{'id':'q1','q':'报告类型？','options':['深度研究','主题量化']}]*5,
                answers=[{'question_id':'q1','answer':'深度研究'}]*5,
                decisions=[{'field':'report_type','value':'深度研究'}])
blf.validate_brief(b); blf.approve(b); blf.save_brief(b, wl.brief_path(no))

from docx_helpers import (new_document, cover, speedread_page, h1, para, plain_note, so_what,
                          faq_box, method_card, table_intro, add_table, img, fig_table_list,
                          save_stage, dump_doc_text, provenance_table, socratic_stats_table,
                          manager_stats_table, save)
from chart_helpers import line_chart, bar_chart, diagram
doc = new_document()   # speedread_page(doc, 标题, 评级行, reasons=[…], key_numbers=(表头,行), …)

from forecast_lib import Assumption, build_equity_forecast
from valuation_lib import run_derived, weighted_synthesis, crosscheck

from socratic_lib import (new_session, submit_challenges, defend, revised_assumption_claims,
                          exempt_pillar, audit_readiness, audit_coverage, audit_gate, audit_checklist)
s = new_session('%s·%s' % (no, '主题'), load_bearing_claims=承重柱+核心结论, mode='single_audit')
adm = submit_challenges(s, challenges_json)
defend(s, adm[0]['id'], 'data', evidence_file='50_sessions/review_r1_01.json', note='…')
assert audit_readiness(s, 'full')['ok'] and audit_coverage(s, thesis)['ok'] and audit_gate(s)['pass']

from manager_log import ManagerLog
ml = ManagerLog(scope='%s_%s' % (no, '主题'), persona='P9')   # standard 用 P7
ml.checkpoint('全稿', summary='…', questions=[{'q':'…','a':'…','kind':'pro'}], verdict='过关')

save_stage(doc, '报告名.docx', subject='主题', review={...}, report_no=no)
```

## 铁律

- **唯一人工门**：grill 批准后无人值守；异常自动归宿（驳回重写/审计回流/降级标注/超限 blocked），悬停等人=违规。
- **数字由代码算**：报告含预测/估值数字必须有 `forecast_*/results_*` 算子输出；审计 `revise` 必须回流重跑。
- **先建树再写作**：thesis.json 贯穿写作与审计；审计按 pillar 攻击，禁逐句扫描。
- **假设必带证据链**：[实证]/[推断]/[观点] + 依据 + 概率；裸（估）拦截。
- **防自证纪律（零子代理）**：先抓数冻结 FACTS 再立论；写作只消费 FACTS+算子输出；审计以 dump 为准逐柱攻击、禁凭记忆放行；质询/回应全部落 `50_sessions/` 可回查。
- **通俗=外挂**：判断权归专业层；比喻带"仅为助记"免责；通俗层数字与专业层不一致 = QA FAIL。
- 方法必须来自推导（地产禁 PE 分位；比特币/手办禁 DCF/PE）；无路可走 `stats_baseline` 并标注"统计性描述"。
- 东财批量 ≤100、腾讯 K 线 count≤800；抓取限速 0.3s、重试 3；缓存幂等覆盖。

## 环境与自测

依赖见 `requirements.txt`；渲染自查需 LibreOffice（可选，缺省跳过）。全程不派子代理（无 Task 调用）。细则按需读：`reference/data-sources.md`（数据源用法）、`reference/docx-conventions.md`（版式令牌）、`reference/analysis-methods.md`（方法口径）、`reference/analysis-techniques.md`（技法协议）、`reference/library/README.md`（规则库）。

```bash
python scripts/selftest.py --offline   # 离线全套：画像/预测/算子/审计/工作区/brief/技法/PUA/QA
python scripts/selftest.py             # 全量（含联网）
```

全部 PASS、退出码 0 为通过。
