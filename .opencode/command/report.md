---
description: 写报告全自治流水线入口：无 brief 先 /grill；有已批准 brief 则无人值守跑完 抓数→算数→写作审问→审计→QA→编号归档。
---

加载 stock-analysis skill（.opencode/skill/stock-analysis/SKILL.md），按其"流水线（6 步）"执行。

目标：$ARGUMENTS（编号 | 主题 | resume 编号）。

前置（缺一先补，不悬停）：
1. 无 brief → 停止，提示先 `/grill $ARGUMENTS`；有 brief 未批准 → 停止，提示走批准（唯一人工门）。
2. `resume 编号`：读注册表 blocked 状态，复述卡点后恢复执行。
3. `brief.report_type=更新报告` → 复用 dossier.inherited 增量复核，禁全量重跑。

执行要点（全程无人值守）：
- 建 `FlowLog(scope=编号)`；`profile_lib.derive` + 各挂点 `technique_lib.recommend/activate`（≤3，必填理由）。
- 侦察兵子代理 ×1（fetch_lib 缓存优先 → `00_cache/` + `10_facts/FACTS.md` 冻结）。
- `forecast_lib`/`valuation_lib` 算全部数字；`thesis_lib` 建树。
- 写手子代理 ×1 顺序写全稿（SELF_ATTACK + 通俗外挂件）→ 主上下文 `ManagerLog.checkpoint('全稿')` 一次审问（≤3 专业 + ≤1 通俗；驳回重写 ≤1 次）。
- 审计子代理 ×1（R1；full ≥4 条含 ≥1 替代解读/隐含前提，standard ≥3；每柱覆盖）→ `socratic_lib` 三闸全过；revise → H1 回流重跑预测估值（full 级 R2 核修正处）。
- QA：`check_report_depth --type <蓝图id> --trace-dir <工作区>` / `check_delivery` / `cache_status --strict` / `render_check`（可选）。
- 交付：`save_stage(...)` 双写 + `flow_log.save()`；输出完成摘要（编号/评级区间/审计与 PUA 统计/生成成本/新技法/`/drill 编号`）。
