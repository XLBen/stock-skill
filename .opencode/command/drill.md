---
description: 追问旧报告：draft 做需求变更重审（须重过人工门）；delivered 做回溯拷问（承重柱检验+命中/失误判定+五问归因）。
---

加载 stock-analysis skill（.opencode/skill/stock-analysis/SKILL.md），按 `reference/templates/drill_interrogator.md` 执行**追问**（禁止用 grill 口吻）。

目标：$ARGUMENTS（报告编号；旧报告首次被 drill 时先 `workspace_lib.assign_legacy(路径)` 懒分配编号）。

1. **定位**：`workspace_lib.locate('$ARGUMENTS')`；不存在 → 报错并列出 `list_reports()`。
2. **状态分流**：
   - draft/blocked → **模式 A 需求变更重审**：子代理按模板 A 节逐字段过堂 brief（waves 问答史、vague_hits、新变量）→ 变更清单 → 主上下文更新 brief 并**重新请求用户批准**（变更必须重过唯一人工门）。
   - delivered/archived → **模式 B 回溯拷问**：子代理按模板 B 节双人格审问（逐章"你都写了啥"+空头对承重柱检验，可自主抓数落盘 drill_r*.json，每轮 ≤3 次）；`review_lib.suggest_judgment` 判定命中/失误/待定；失误结论 five_whys 归因到方法层。
3. **落档**：写 `80_reflection/drill_{日期}.json` 并 `register_file(kind='reflection')`；`review_lib.update_judgment` 逐条落档。
4. **收尾**：健康检查表（claim × 判定 × 证据 × asof）+ 失误归因 + 改进项；结论需重写时提示 `/report resume 编号`。
