---
description: 需求拷问（唯一人工门）：1 波 5~6 问问清需求，批准后自动跑完抓数/算数/写作/QA/归档产出 docx——无需再执行其他命令。
---

加载 stock-analysis skill（.opencode/skill/stock-analysis/SKILL.md），执行「需求拷问 + 自动流水线」（主上下文执行，不派子代理）。

目标：$ARGUMENTS（为空则先问用户要分析什么）。

1. **状态判定**（`workspace_lib.locate`）：
   - 无 brief → 询问模式：`init_workspace(主题)` 分配编号；`new_brief`
   - 有未批准 brief → 输出摘要请用户就地批准（单波协议，不再补问）
   - 已批准未交付（draft/blocked）→ 跳过提问，直接恢复执行流水线
   - 已交付 → 按更新报告处理：新编号 + 复用 `review_lib` dossier 的 `inherited` 增量复核（不重复展开旧内容）
2. **1 波提问**：question 工具一次提 5~6 问（每问 2~4 选项），覆盖必填字段：report_type/reader/purpose/key_concerns（≥3）/failure_criteria/time_range/length_pref/language；模糊/缺失答案由编排器按务实偏好兜底并写入盲区（单波协议，不再追问）。
3. **落盘与批准**：`brief_lib.record_wave(brief, questions, answers, decisions)`（单波，第二波会报错）→ `termination_check`/`validate_brief` → 输出 `summary(brief)` 摘要与盲区，请用户批准（唯一人工门）；批准后 `approve` + `save_brief(brief, workspace_lib.brief_path(编号))` + `set_status(编号,'draft',brief_approved=True,flow_level=…)`。
4. **批准后立即自动执行流水线**（不停顿、无需其他命令）：`profile_lib.derive` 推导 → 抓数 + `FACTS.md` 冻结 → `forecast_lib`/`valuation_lib` 算全部数字 → `thesis_lib` 建树并顺序写全稿（通俗件 + tone 文风 + 每图 `fig_intro` + 独立反方论点小节）→ 脚本 QA（`check_report_depth --type <蓝图id> --trace-dir <工作区>` / `check_delivery` / `cache_status --strict`）0 错误 → `save_stage` 双写归档 → 输出完成摘要（编号/评级区间/成本/文件路径）。
5. 若中途数据缺失：降级标注进盲点清单，不悬停；确实无法继续时 `workspace_lib.blocked(编号, 卡点)` 并输出卡点，重新运行 `/grill 主题` 即从卡点恢复。
