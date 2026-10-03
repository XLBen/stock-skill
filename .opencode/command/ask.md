---
description: self-grill 零人工路线：用户只提一个简单问题，两个子代理（拷问者×应答者）自我对谈推导需求出 brief，自动批准后直接走 full 级全自治流水线产出 docx 报告——全程无需用户操作。
---

加载 stock-analysis skill（.opencode/skill/stock-analysis/SKILL.md），执行 self-grill 路线。

用户问题：$ARGUMENTS（一句话；为空则直接问用户"想问什么"——这是本命令唯一的例外交互）。

流程（**全程零用户参与**，两子代理互不可见，对话经文件总线中转）：

1. **建工作区**：`workspace_lib.init_workspace(问题主题)` 分配编号；`brief_lib.new_brief(主题, report_no=编号, mode='self')`
2. **波次对谈**（≤6 波，循环）：
   - Task 子代理 A（`reference/templates/self_grill_interviewer.md`）：输入=原始问题+brief 状态+dossier 摘要+上轮答案 → 输出本轮问题 JSON（每波 5~8 问、首波 ≥5、钻取规则同 grill）
   - Task 子代理 B（`reference/templates/self_grill_responder.md`）：输入=原始问题+dossier+本轮问题 → 输出答案 JSON（每答标 [代理推断·强/中/弱] 或 中性·不确定/私有信息不可推断）
   - 主上下文落盘：`brief_lib.record_wave(brief, questions, answers, decisions, followups, actor='self')`
   - 终止：A 声明 terminal / B 答 enough / `brief_lib.termination_check(brief)` 命中 / 6 波上限
3. **自动批准**：`brief_lib.self_approve(brief)`（完整性校验通过才放行；approval 带 auto=True+免责）→ `save_brief(brief, workspace_lib.brief_path(编号))`；`set_status(编号, 'draft', brief_approved=True, flow_level='full')`
4. **进流水线**：与 /report 相同的 10 步全自治执行，**flow_level 锁定 full**（PUA P9+单次审计四闸+premortem/base_rate 强制+技法注册表；蓝图章节仍按 report_type 推导）；报告封面 meta 与首页脚注必须标注"⚠ 本报告需求由 self-grill 代理推导，未经用户确认"
5. **完成摘要**（比 /report 多一段）：Top3 关键 [代理推断]（含强度）+ 免责声明 + 提示 `/drill 编号`（模式A 修正 brief → `/report resume 编号` 重跑）

若 brief 完整性校验始终不过（波次耗尽仍有必填缺失）：编排器按"务实偏好"兜底填充（标 [代理推断·弱]）后再 self_approve——禁止 blocked 悬停。
