---
description: 写报告全自治流水线入口：无 brief 先触发 grill；有已批准 brief 则无人值守跑完 抓数→预测→估值→逐章写作(PUA审问)→单次审计→QA→编号归档，用户只在 grill 批准时在场一次。
---

加载 stock-analysis skill（.opencode/skill/stock-analysis/SKILL.md），按其"全自治流水线（10 步）"执行。

目标：$ARGUMENTS（编号 | 主题 | resume 编号）。

前置（缺一先补）：
1. `$ARGUMENTS` 是编号或主题但无 brief → 停止，提示先运行 `/grill $ARGUMENTS`
2. 有 brief 但未批准 → 停止，提示 `/grill 编号` 走批准（唯一人工门）
3. `resume 编号`：读注册表 blocked 状态恢复执行；blocked 时先向用户复述卡点再继续
4. `update` 需求（brief.report_type=更新报告）→ 复用 dossier.inherited 增量复核，禁全量重跑

执行（brief 批准后**全程无人值守**，每异常走 SKILL.md 自动归宿表，绝不悬停提问）：
- 建 `flow_log.FlowLog(scope=编号)`；画像/推导 → 技法注册表各挂点 `technique_lib.recommend()` + `activate()`（每挂点 ≤3，必填理由）
- 数据侦察兵子代理抓数（fetch_lib，缓存优先，落工作区 00_cache/ + 10_facts/FACTS.md 冻结）
- forecast_lib / valuation_lib 算数字（LLM 禁手算）；技法分析师子代理并行产出
- thesis_lib 建树 → 章节写手子代理**严格顺序**逐章写作 → 每章 desk_chief.md PUA 审问（manager_log 落盘；驳回自动重写 ≤1 次，二次转审计）
- 单次审计（single_auditor.md + socratic_lib mode='single_audit'）：R1 攻防→H1 回流→R2 核验；四道闸全过（audit_readiness/audit_coverage/audit_gate/自检清单）才许终稿
- QA 全套（check_report_depth / usage_probe / cache_status --strict / check_delivery / render_check）
- 交付：`save_stage(doc, 报告名, subject, review, report_no=编号)` 双写归档；flow_log.save() 到工作区；`technique_lib.techniques_used(flow_log)` 进附录
- 最后输出完成摘要：编号/评级与区间/审计统计（受理×裁决×背反×三闸）/PUA 统计/生成成本/新引入技法/`/drill 编号` 提示
