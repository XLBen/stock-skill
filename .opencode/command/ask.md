---
description: self-grill 零人工路线（零子代理）：主上下文单轮自推导需求 brief 并自动批准，直接跑 full 级流水线产出 docx 报告。
---

加载 stock-analysis skill（.opencode/skill/stock-analysis/SKILL.md），执行 self-grill 路线（**不派子代理**）。

用户问题：$ARGUMENTS（为空则问用户"想问什么"——本命令唯一例外交互）。

1. **建工作区**：`workspace_lib.init_workspace(问题主题)`；`brief_lib.new_brief(主题, report_no=编号, mode='self')`。
2. **单轮自推导**（主上下文直接完成，1 轮；不派 Task）：从问题与常识出发推断全部必填字段——report_type/reader/purpose/key_concerns（≥3）/failure_criteria/time_range/length_pref/language/flow_level；每字段给一句依据并标 `[代理推断·强/中/弱]`；推断不了的进盲区（禁编造用户私有信息）。
3. **落盘与批准**：`brief_lib.record_wave(brief, questions=自问清单, answers, decisions, actor='self')` → `validate_brief` 通过则 `brief_lib.self_approve(brief)` + `save_brief(..., workspace_lib.brief_path(编号))` + `set_status(编号,'draft',brief_approved=True,flow_level='full')`；仍缺必填 → 按务实偏好兜底（标弱推断）再批，禁 blocked 悬停。
4. **进流水线**：与 /report 相同的 6 步全自治执行（锁 full；全程主上下文）；封面 meta 与首页脚注标注"⚠ 本报告需求由 self-grill 代理推导，未经用户确认"。
5. **完成摘要**：比 /report 多一段 Top3 关键 [代理推断]（含强度）+ 免责 + 提示 `/drill 编号` 修正（模式 A → `/report resume 编号`）。
