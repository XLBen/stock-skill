# stock-analysis — 泛金融报告分析全流程 Skill

一个面向 AI 编程 Agent（opencode / Claude Code 等）的 skill：只要用户要求**写/出/修改任何报告**（投资研究、个股深度、资产研究、估值分析、财报解读、回测、总结报告，股票/基金/利率/地产/加密/收藏品等任意对象）即触发。亦覆盖行情/财务/研报数据抓取、网格/定投回测、板块筛选、商誉减值、指增/红利/AH 溢价研究与 Word（.docx）报告生成。

当前版本：**v2.5**（见 [CHANGELOG.md](CHANGELOG.md)）

## 核心理念

- **北极星是一份可用的报告**：任何对象先做 8 维画像，规则库（`reference/library/`，JSON 数据驱动）推导方法集/数据源/报告蓝图
- **预测与估值数字由代码算，叙事由 LLM 写**：禁止手算，每项假设必须带 `[实证]/[推断]/[观点]` 标签与依据
- **苏格拉底质询**：报告假设经受对抗审查（以数据立状、不到底不停止、背反则记录）
- **复盘闭环**：结论自动落档校准，第 N 份报告站在第 N-1 份肩上

## 目录结构

```
├── SKILL.md              # skill 主文档（触发条件 / 11 步流水线 / 脚本用法）
├── reference/
│   ├── analysis-methods.md    # 分析方法总纲
│   ├── data-sources.md        # 数据源手册（akshare/yfinance/一手公告…）
│   ├── docx-conventions.md    # Word 报告排版规范
│   ├── library/               # 规则库（blueprints/methods/profiles/sources/backtest/dispute）
│   ├── signals/               # 方法信号（Damodaran 锚等）缓存
│   └── templates/             # 苏格拉底质询 / 对抗审稿人 子代理模板
└── scripts/              # 全部算子与工具（fetch/forecast/valuation/socratic/review/thesis/QA…）
```

## 安装

Python 3.10（与历史项目环境保持一致）：

```bash
pip install -r requirements.txt
```

## 使用

将本目录放入 agent 的 skill 搜索路径（如 opencode 的 `.opencode/skill/stock-analysis`），用户提到"报告"即自动加载 SKILL.md 并按 11 步流水线执行（full / standard / minimal 三级流程分级，拒绝过度流程）。

报告产出（草稿、数据缓存、质询记录）落在**使用方项目**的暂存区，不属于本仓库。
