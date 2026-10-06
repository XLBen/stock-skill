---
description: self-grill 零人工路线：一个子代理拷问、一个子代理应答（各 1 轮），推导 brief 自动批准后直接跑 full 级流水线产出 docx 报告。
---

加载 stock-analysis skill（.opencode/skill/stock-analysis/SKILL.md），执行 self-grill 路线。

用户问题：$ARGUMENTS（为空则问用户"想问什么"——本命令唯一例外交互）。

1. **建工作区**：`workspace_lib.init_workspace(问题主题)`；`brief_lib.new_brief(主题, report_no=编号, mode='self')`。
2. **对谈 1 轮**（默认；仅当产出 brief 校验不过再补 1 轮，上限 2 轮）：
   - Task 子代理 A（`reference/templates/self_grill_interviewer.md`）：输入=原始问题 → 输出 5~6 个问题 JSON（一问即覆盖 report_type/reader/purpose/key_concerns/failure_criteria/time_range 等必填字段）。
   - Task 子代理 B（`reference/templates/self_grill_responder.md`）：输入=原始问题+A 的问题 → 输出答案 JSON（每答标 [代理推断·强/中/弱] 或 中性·不确定；禁编造用户私有信息，缺依据进盲区）。
   - 主上下文 `brief_lib.record_wave(brief, questions, answers, decisions, actor='self')`。
3. **自动批准**：`validate_brief` 通过则 `brief_lib.self_approve(brief)` + `save_brief(..., workspace_lib.brief_path(编号))` + `set_status(编号,'draft',brief_approved=True,flow_level='full')`；仍缺必填 → 编排器按务实偏好兜底（标弱推断）再批，禁止 blocked 悬停。
4. **进流水线**：与 /report 相同的 6 步全自治执行（flow_level 锁 full）；封面 meta 与首页脚注标注"⚠ 本报告需求由 self-grill 代理推导，未经用户确认"。
5. **完成摘要**：比 /report 多一段 Top3 关键 [代理推断]（含强度）+ 免责 + 提示 `/drill 编号` 修正（模式 A → `/report resume 编号`）。
