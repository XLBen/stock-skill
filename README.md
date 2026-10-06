# stock-skill · 泛金融报告双命令自动流水线（v3.8 单遍版）

> 一个 [opencode](https://opencode.ai) skill：从"一句话提问"到"带 QA 的 Word 研报"，全程自动。
> 适合 A股/港美股/基金/利率/地产/加密/收藏品等**任意资产对象**——按资产属性推导方法，而非套模板。

```
/ask "XX股份现在能买吗"                       /grill 中药行业
  └─ 主上下文自推导需求（零人工）               └─ 1 波问清需求 → 你批准（唯一人工门）
      → 自动跑完：                                    → 自动跑完：
 画像推导 → 抓数(FACTS 冻结) → 代码算数(预测/估值)
      → 顺序写作(通俗件+tone) → 脚本 QA(0 错误) → 编号归档 docx
```

## 核心特性

| 特性 | 说明 |
|---|---|
| **双命令** | 只有 `/grill`（人工问答）与 `/ask`（零人工）；**批准后自动执行到交付**，不需要第二个命令 |
| **省 token 设计** | 需求单波问清（不再追问）；零子代理（不派 Task）；无审计/PUA/多轮环节；篇幅按蓝图降档（full 8000 / standard 6000 / minimal 4000 / update 3000 字符） |
| **8 维画像推导** | 现金流/披露/供给/流动性/价格行为等属性 → JSON 规则库谓词匹配出方法集/数据源/报告蓝图；地产禁 PE、手办禁 DCF |
| **技法注册表** | 20 项分析技法按需激活，每个挂点 ≤3 且必填理由；full 强制 premortem、standard/full 强制基础比率 |
| **数字由代码算** | 预测/估值只出自 `forecast_lib`/`valuation_lib` 算子，LLM 手算即违规；假设必带证据链与基础比率锚 |
| **报告可读性** | 正文少标签说人话（tone 规则：结论先行/短句/禁 AI 腔），证据标签只进假设表；每图前挂 `fig_intro`"看图先读"说明 |
| **脚本 QA 兜底** | `check_report_depth`（字数/强制章/数字溯源/通俗一致/图片说明）+ `check_delivery` + `cache_status --strict`，0 错误才交付 |
| **编号存档** | 每报告一编号一工作区，docx 双写交付；再跑 `/grill 同主题` 走更新报告增量复核 |

## 安装

依赖 [opencode](https://opencode.ai) 与 Python 3.10+：

```bash
# 1. 把本仓库放进你的项目，得到：
#    your-project/.opencode/skill/stock-analysis/
#    your-project/.opencode/command/{grill,ask}.md
git clone https://github.com/XLBen/stock-skill.git
cp -r stock-skill/.opencode/ your-project/.opencode/

# 2. 安装 Python 依赖
pip install -r stock-skill/.opencode/skill/stock-analysis/requirements.txt

# 3. 重启 opencode（命令与 skill 在启动时加载）
```

可选：渲染目检需 LibreOffice（缺失自动跳过）。

## 命令（只有两个）

| 命令 | 用途 |
|---|---|
| `/grill [主题\|编号]` | 1 波需求拷问 → 你批准（**唯一人工门**）→ 自动跑完流水线。已批准未交付 → 直接恢复执行；已交付 → 更新报告增量重跑 |
| `/ask 一句话问题` | **零人工**：主上下文自推导需求（字段标 [代理推断]）自动批准 → 自动跑完（锁 full） |

## 流水线（批准后自动执行，异常自动归宿）

1. brief：`/grill` 单波问清或 `/ask` 自推导 → `brief.json`（含糊答案兜底进盲区）
2. 画像推导 + 技法候选（`profile_lib.derive` + `technique_lib.recommend`）
3. 主上下文抓数（缓存优先）+ `FACTS.md` 中性事实清单**冻结**
4. 预测建模 + 估值（`forecast_lib`/`valuation_lib`，数字由代码算）+ `thesis_lib` 建树
5. 顺序写全稿（通俗件 + tone + 每图"看图先读" + 独立反方小节）→ 脚本 QA（0 错误）→ 双写归档（`70_delivered/` + `reports/所有报告/{编号}_{名}.docx`）+ 完成摘要

异常**绝不悬停等人**：数据缺失→降级标注进盲点；无法继续→`blocked`（重跑 `/grill 主题` 从卡点恢复）。

### 流程分级

| 级别 | 触发蓝图 | 门禁 |
|---|---|---|
| full | 个股深度/资产研究/租金资产 | premortem/base_rate 强制 + 技法开放 + 通俗全量 |
| standard | 主题量化/更新报告 | base_rate 强制 |
| minimal | 策略手册/科普/决策测算 | 仅脚本 QA |
| /ask | 一律 | 按 full 门禁执行（章节结构仍按报告类型推导） |

## 目录结构

```
.opencode/
├── command/                    # /grill /ask（只有两个）
└── skill/stock-analysis/
    ├── SKILL.md                # 主协议（v3.8 双命令单遍流水线）
    ├── CHANGELOG.md
    ├── requirements.txt
    ├── scripts/                # Python 库（工作区/brief/技法/抓数/预测/估值/QA/图表/排版）
    └── reference/
        ├── library/            # JSON 规则库（方法/源/蓝图/回测/分歧/技法）
        ├── data-sources.md     # 数据源用法
        ├── docx-conventions.md # Word 版式令牌
        ├── analysis-methods.md # 方法口径
        └── analysis-techniques.md  # 20 技法协议
```

运行期产物（不入库，`.gitignore` 已排除）：`reports/{编号}_{主题}/` 工作区、`reports/所有报告/` docx 汇集、`档案/` 复盘 dossier。

## 自测

```bash
cd .opencode/skill/stock-analysis
python scripts/selftest.py --offline   # 全套用例 PASS、退出码 0
```

## 方法论来源（三级优先级：机构 > 教材·论文 > GitHub）

- **机构**：CIA《Structured Analytic Techniques》、FINRA 3110 单一终审签发、NATO Admiralty 信源分级、Morningstar 护城河、Shell 情景规划
- **教材·论文**：Kahneman《思考，快与慢》外部视角、Flyvbjerg 参考类预测、Heuer《情报分析心理学》、Damodaran《Investment Valuation》、Piotroski 2000 / Beneish 1999 / Altman 1968
- **GitHub 原型**：RobMitt/grill-me-skill（多选拷问协议）、TauricResearch/TradingAgents（扁平专家+单一终审门）
