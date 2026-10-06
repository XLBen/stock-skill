---
description: 报告需求拷问（询问模式·1 波）：一批 5~6 问覆盖全部必填字段，产出 brief.json 并请求批准——流水线唯一人工门。
---

加载 stock-analysis skill（.opencode/skill/stock-analysis/SKILL.md），执行需求拷问（询问模式，主上下文直接执行，不派子代理）。

目标：$ARGUMENTS（为空则先问用户要分析什么）。

1. **状态判定**：`workspace_lib.locate('$ARGUMENTS')`。无 brief 的新主题 → `init_workspace(主题)` 分配编号；已有 brief 或已交付 → 停止，提示改用 `/drill 编号`（禁止混用口吻）。
2. **1 波提问**：question 工具**一次调用**提 5~6 问（每问 2~4 选项），覆盖必填字段：报告类型/读者/用途/关键关切（≥3）/失败标准/时间范围/篇幅/语言；针对本轮答案里的模糊词（深度/差不多/尽量…）或新变量，最多再追问 1 波（上限 2 波）。
3. **落盘**：每波 `brief_lib.record_wave(brief, questions, answers, decisions)`；随后 `termination_check` 与 `validate_brief`。
4. **收束**：输出 `brief_lib.summary(brief)` 决策摘要 + 盲区，请用户批准（唯一人工门）；批准后 `brief_lib.approve` + `save_brief(brief, workspace_lib.brief_path(编号))` + `workspace_lib.set_status(编号,'draft',brief_approved=True)`。
5. 告知用户：`/report 编号` 启动全自治流水线，全程无需在场。
