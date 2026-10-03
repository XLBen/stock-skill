---
description: 报告需求拷问（询问模式）：多波次批量刨根问清要什么报告，产出 brief.json 并请求批准——全流水线唯一人工门。
---

加载 stock-analysis skill（.opencode/skill/stock-analysis/SKILL.md），按下述执行需求拷问（询问模式）。

目标：$ARGUMENTS（主题、标的、或报告编号；为空则先问用户要分析什么）。

协议（严格遵循 reference/templates/grill_interviewer.md）：

1. 状态判定：`python -c "import sys; sys.path.insert(0, r'.opencode/skill/stock-analysis/scripts'); import workspace_lib; e = workspace_lib.locate('$ARGUMENTS') if '$ARGUMENTS' else None; print(e)"` ——
   - 无 brief 的新主题 → 询问模式（本命令）：`workspace_lib.init_workspace(主题)` 分配编号建工作区
   - 已有 brief 或已交付报告 → 停止，提示用户改用 `/drill 编号`（追问 prompt 不同，禁止混用）
2. 询问：用 question 工具按**批量波次**提问（每波一次调用 5~8 问、每问 2~4 选项、首波 ≥5 问；波次序：需求根因→标的范围→深度方法→交付形态→约束禁写→验证复述）
3. 钻取：上波答案含模糊词（深度/差不多/尽量…）/新决策变量/自定义输入 → 下波对每点派生 ≥2 追问
4. 落盘：每波答案固化 `brief_lib.record_wave(brief, questions, answers, decisions)`；工作目录切到 skill scripts 目录运行 python
5. 终止：`brief_lib.termination_check(brief)` 任一条件命中即停（连续两波无新决策变量/用户"够了"/完整性校验通过；上限 6 波）
6. 收束：输出 `brief_lib.summary(brief)` 决策摘要 + 仍未查明点（写入盲区），请用户**批准**（唯一人工门）；批准后 `brief_lib.approve` + `save_brief(brief, workspace_lib.brief_path(编号))` + `workspace_lib.set_status(编号, 'draft', brief_approved=True)`
7. 告知用户：批准后可用 `/report 编号` 启动全自治流水线，全程无需在场
