---
name: stock-analysis
description: 泛金融报告流水线（v3.7 双命令自动版·零子代理）。用户要求写/改任何报告（投资研究/个股深度/资产研究/估值/财报解读/回测/策略/科普，股票/基金/利率/地产/加密/收藏品等任意对象）或抓行情/财务/研报数据、出 Word（.docx）报告时使用。命令只有 /grill 与 /ask：问清需求并批准（唯一人工门）后自动跑完 画像推导→抓数冻结→代码算数→顺序写作→脚本 QA→编号归档；无审计/PUA 环节。
---

# stock-analysis v3.7 · 双命令自动流水线

北极星：**一份可用 docx 报告**。只在 grill/ask 批准时与用户交互一次；批准后自动跑完直到交付。LLM 只做编排与叙事，预测/估值数字一律出自 `forecast_lib`/`valuation_lib` 算子。

## 原则（硬约束）

1. **双命令**：只保留 `/grill`（人工需求拷问）与 `/ask`（零人工自推导）；`/grill` 批准后**自动执行**，无需第二个命令。
2. **需求一轮问清**：默认 1 波 ≤6 问；仅模糊词/关键字段缺失才加 1 波，上限 2 波。
3. **零子代理、无审计/PUA**：不派 Task；不跑质询攻防、不跑管理员审问。质量靠脚本 QA 硬检查（0 错误门槛）。
4. **篇幅降档**：按蓝图 `min_words`（full 8000 / standard 6000 / minimal 4000 / update 3000 字符）；不足只补新论点+新数据源。
5. **按需读文件**：导航只读 `_registry.json` 与 `WORKSPACE.md`；写作只消费已登记文件，禁全库扫描。

## 命令（项目级 .opencode/command/，只有两个）

| 命令 | 说明 |
|---|---|
| `/grill [主题\|编号]` | 1 波需求拷问 → brief → 用户批准（唯一人工门）→ **自动跑完流水线**。已批准未交付 → 跳过提问直接恢复执行；已交付 → 按更新报告增量重跑（复用 dossier.inherited） |
| `/ask 一句话问题` | 零人工：主上下文单轮自推导 brief（字段标 [代理推断·强/中/弱]）→ 自动批准 → 自动跑完（flow_level 锁 full） |

## 流水线（批准后自动执行，异常自动归宿绝不悬停）

1. **brief**：`workspace_lib.init_workspace(主题)` → `brief_lib.new_brief/record_wave/validate_brief/approve`（self 用 `self_approve`）→ `save_brief`；`set_status(no,'draft',brief_approved=True,flow_level=…)`。
2. **推导**：`profile_lib.derive(画像, brief.report_type)` → 方法集/源集/蓝图/QA；`profile_lib.profile_from_answers` 可得画像。各挂点 `technique_lib.recommend(profile, stage, …)` 激活 ≤3 条（full 强制 `premortem`、standard/full 强制 `base_rate`；新增走 `propose_auto`）。`flow_log.FlowLog(scope=no)` 记录。同资产先 `review_lib.load_dossier()` 取 `inherited`。
3. **抓数（主上下文）**：按源集用 `fetch_lib`（缓存优先，`save_json` 带 _meta）落 `00_cache/`；产 `10_facts/FACTS.md`（指标|数值|口径|asof|来源，禁解读）后**冻结**——先抓数后立论，抓完不再边写边抓。
4. **算数字**：`forecast_lib.Assumption(value,basis,tag,probability,base_rate_ref)` + `build_equity_forecast/build_rental_forecast/build_supply_demand_balance`；`valuation_lib.run_derived` + `weighted_synthesis` + `crosscheck` + `flip_point`；`thesis_lib.build_thesis`（结论→3~5 承重柱→证据映射）落 `40_thesis/`。增长类 [推断] 缺 base_rate_ref 自动降级。LLM 禁手算。
5. **写作 → QA → 归档**：按蓝图 sections 顺序写全稿落 `60_draft/`——承重段挂 `plain_note`、每章 ≥1 `so_what`、全报告 ≥1 `faq_box`、技法/估值首现挂 `method_card`、表前 `table_intro`、每图前 `fig_intro`（看图先读）、图注带 source；正文不堆 [实证]/[推断]/[观点] 标签（只进假设表与溯源表），文风按 `layout_rules.tone`（结论先行/短句/主动语态/禁 AI 腔）；**反方论点独立小节，正反两面都写**。QA：`check_report_depth --type <蓝图id> --trace-dir <工作区>`、`check_delivery`、`cache_status --strict`、`render_check`（可选）→ 0 错误后 `docx_helpers.save_stage(doc, 名, subject, review, report_no=no)` 双写归档 + `flow_log.save(workspace_lib.flow_log_path(no))` → 输出摘要（编号/评级区间/新引入技法/文件路径）。异常归宿：数据缺失 → 降级标注进盲点；无法继续 → `workspace_lib.blocked(no, 卡点)`（重跑 `/grill 主题` 即恢复）。

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
                          faq_box, method_card, table_intro, fig_intro, add_table, img,
                          fig_table_list, save_stage, dump_doc_text, provenance_table,
                          data_asof_table, save)
from chart_helpers import line_chart, bar_chart, diagram
doc = new_document()   # speedread_page(doc, 标题, 评级行, reasons=[…], key_numbers=(表头,行), …)

from forecast_lib import Assumption, build_equity_forecast
from valuation_lib import run_derived, weighted_synthesis, crosscheck
from thesis_lib import build_thesis, save_thesis

save_stage(doc, '报告名.docx', subject='主题', review={...}, report_no=no)
```

## 铁律

- **唯一人工门**：grill/ask 批准后无人值守自动跑完；异常自动归宿（降级标注/blocked），悬停等人=违规；blocked 后重跑 `/grill 主题` 恢复。
- **数字由代码算**：报告含预测/估值数字必须有 `forecast_*/results_*` 算子输出，LLM 手算即违规。
- **先建树再写作**：thesis.json 管住承重柱与证据映射；写作不得引入树外论点。
- **假设必带证据链**：[实证]/[推断]/[观点] + 依据 + 概率，只写在假设表/溯源表，正文不堆标签。
- **防自证纪律**：先抓数冻结 FACTS 再立论；写作只消费已登记文件；关键数字给得出出处（文件→字段）。
- **通俗=外挂**：判断权归专业层；比喻带"仅为助记"免责；通俗层数字与专业层不一致 = QA FAIL；每图配"看图先读"说明。
- 方法必须来自推导（地产禁 PE 分位；比特币/手办禁 DCF/PE）；无路可走 `stats_baseline` 并标注"统计性描述"。
- 东财批量 ≤100、腾讯 K 线 count≤800；抓取限速 0.3s、重试 3；缓存幂等覆盖。

## 环境与自测

依赖见 `requirements.txt`；渲染自查需 LibreOffice（可选，缺省跳过）。全程不派子代理（无 Task 调用）。细则按需读：`reference/data-sources.md`（数据源用法）、`reference/docx-conventions.md`（版式令牌）、`reference/analysis-methods.md`（方法口径）、`reference/analysis-techniques.md`（技法协议）、`reference/library/README.md`（规则库）。

```bash
python scripts/selftest.py --offline   # 离线全套：画像/预测/算子/工作区/brief/技法/QA
python scripts/selftest.py             # 全量（含联网）
```

全部 PASS、退出码 0 为通过。
