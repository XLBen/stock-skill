---
description: 追问旧报告（Grill·追问模式）：对已有编号的报告做需求变更重审或回溯拷问（"你都写了啥"+承重柱检验+命中/失误判定），产出健康检查表并落档反思。
---

加载 stock-analysis skill（.opencode/skill/stock-analysis/SKILL.md），按 reference/templates/drill_interrogator.md 执行**追问**（prompt 与询问完全不同，禁止用 grill 口吻）。

目标：$ARGUMENTS（报告编号，如 `7`；或旧报告路径——旧报告首次被 drill 时先 `workspace_lib.assign_legacy(路径)` 懒分配编号）。

流程：
1. 定位：`workspace_lib.locate('$ARGUMENTS')`；不存在 → 报错并列出 `workspace_lib.list_reports()` 供选择
2. 状态分流：
   - 工作区有 brief 无终稿（draft/blocked）→ **模式 A 需求变更重审**：Task 子代理按 drill_interrogator.md A 节逐字段过堂 brief（含 waves 问答史核对、vague_hits 复查、新变量）→ 输出变更清单 → 主上下文更新 brief 并**重新请求用户批准**（变更必须重新过唯一人工门）
   - 已交付（delivered/archived）→ **模式 B 回溯拷问**：Task 子代理（drill_interrogator.md B 节，可自主抓数落盘 drill_r*.json，每轮 ≤3 次）双人格审问：管理员"你都写了啥"逐章核对 + 空头对幸存承重柱检验；`review_lib.suggest_judgment` 量化判定命中/失误/待定；失误结论 five_whys 五问归因到方法层
3. 落档：结果写 `80_reflection/drill_{日期}.json` 并 `workspace_lib.register_file(编号, 路径, kind='reflection')`；`review_lib.update_judgment` 逐条落档；失误样本进 `review_lib.error_patterns()`
4. 收尾输出：健康检查表（claim × 判定 × 证据 × asof）+ 失误归因 + 改进项；结论需重写时提示 `/report resume 编号`
