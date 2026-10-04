# stock-skill · 泛金融报告分析全自治流水线

> 一个 [opencode](https://opencode.ai) skill：从"一句话提问"到"带审计的 Word 研报"，全程无人值守。
> 适合 A股/港美股/基金/利率/地产/加密/收藏品等**任意资产对象**——按资产属性推导方法，而非套模板。

```
/ask "XX股份现在能买吗"
  └─ 两个子代理自我拷问推导需求（self-grill，零人工）
      → 8 维画像推导方法集 → 数据侦察(FACTS 冻结) → 盈利预测/估值(数字由代码算)
      → 逐章写作 × PUA 管理员审问 → 单次审计(四道闸) → QA → 编号归档 docx
```

## 核心特性

| 特性 | 一句话说明 |
|---|---|
| **grill 多波次需求拷问** | 写之前先问清楚：批量波次（首波 ≥5 问），模糊答案必被追问，直到 brief 完整（`/grill`，唯一人工门） |
| **self-grill 零人工路线** | 用户只提一个问题，拷问者×应答者双子代理对谈推导需求，自动批准直接出报告（`/ask`，全程无人） |
| **通俗外挂层（v3.2）** | 面向非专业读者：封面后 30秒速读一页纸 + 承重段逐段【白话解读】+【所以呢】框 + FAQ 小白问答 + 三段式方法卡 + 表前导语 + >10 行长表转图 + 图表编号清单；通俗只是专业深度的外挂，**通俗层数字与专业层不一致 = QA FAIL** |
| **深蓝投行排版（v3.2）** | 高盛/大摩参照的海军蓝版式 + 逻辑示意图新能力（`chart_helpers.diagram`：业务链/竞争格局/方法论图解）；技法注册表全保留，只是呈现更好读 |
| **8 维画像推导** | 现金流/披露/供给/流动性/价格行为等属性 → JSON 规则库谓词匹配出方法集/数据源/报告蓝图；地产禁 PE、手办禁 DCF |
| **技法注册表** | 20 项分析技法（premortem/ACH/2×2 情景/F-Score/Kelly…）按需激活，每挂点 ≤3 且必填理由；无合适技法按证据门槛自动扩充 |
| **数字由代码算** | 预测/估值只出自 `forecast_lib`/`valuation_lib` 算子（19 个估值算子+加权合成），LLM 手算即违规；假设必带证据链与基础比率锚 |
| **PUA 管理员逐章审问** | 每章交付自动触发研究总监"你都写了啥"专业三连问（数字哪来的/So what/删了这章立得住吗）+ 通俗两问（比喻失真检验/扮小白 FAQ），驳回自动重写 |
| **单次审计·严格不降级** | 两会话合一（R1 攻防+R2 核验，上限 2 轮），四道防掉队闸：火力下限/覆盖度量/裁决门禁/自检清单 |
| **子代理上下文防火墙** | 侦察兵不知论点、写手禁抓数、技法分析师并行互不可见、审计员唯一全稿对抗视角——防"带着结果找答案" |
| **编号存档与追问复盘** | 每报告一编号一工作区，docx 双写交付；`/drill 编号` 回溯拷问旧报告（命中/失误/待定+五问归因），第 N 份站在第 N-1 份肩上 |

## 安装

依赖 [opencode](https://opencode.ai) 与 Python 3.10+：

```bash
# 1. 把本仓库放进你的项目（或作为子目录），得到：
#    your-project/.opencode/skill/stock-analysis/
#    your-project/.opencode/command/{grill,report,drill,ask}.md
git clone https://github.com/XLBen/stock-skill.git
cp -r stock-skill/.opencode/ your-project/.opencode/

# 2. 安装 Python 依赖
pip install -r stock-skill/.opencode/skill/stock-analysis/requirements.txt
# pandas numpy scipy matplotlib python-docx requests akshare mini-racer pypdf PyMuPDF yfinance

# 3. 重启 opencode（命令与 skill 在启动时加载）
```

可选：渲染目检需 LibreOffice（缺失自动跳过）。

## 命令

| 命令 | 用途 |
|---|---|
| `/ask 一句话问题` | **零人工**：self-grill 双子代理推导需求 → full 级流水线 → docx |
| `/grill [主题\|编号]` | 需求拷问（用户在场答波次问题）→ 批准 brief（**唯一人工门**） |
| `/report [编号\|主题\|resume 编号]` | 执行全自治流水线至交付；`resume` 从 blocked 态恢复 |
| `/drill [编号]` | 追问：draft→需求变更重审；delivered→回溯拷问+复盘落档 |

PUA 管理员**没有命令**——它在写作循环内自动执行。

## 流水线（10 步，brief 批准后无人值守）

1. grill/self-grill 需求拷问 → `brief.json`
2. 画像/推导/技法候选（`profile_lib.derive` + `technique_lib.recommend`）
3. 数据侦察兵子代理抓数（缓存优先）+ `FACTS.md` 中性事实清单**冻结**
4. 基础分析 + Premortem 事前验尸（full 强制）
5. 预测建模（`forecast_lib`：equity 量价 / rental NOI / 供需平衡；缺基础比率的推断自动降级）
6. 估值（`valuation_lib` + 加权合成；分歧→ACH 竞争性假设矩阵；情景→2×2/龙卷风）
7. 论点树 → 顺序分章写作 → PUA 逐章审问（`manager_log`）
8. 单次审计（`socratic_lib` single_audit：R1 攻防→H1 回流→R2 核验；四道闸全过才许终稿）
9. QA（0 错误：章节深度/数字溯源/缓存新鲜度/交付一致性/渲染目检）
10. 编号归档（`70_delivered/` 历史 + `reports/所有报告/{编号}_{名}.docx` 最新版）+ 完成摘要

异常**绝不悬停等人**：驳回→自动重写、审计修正→自动回流重跑、数据挂→降级标注、超限→`blocked`（附 `/report resume` 恢复点）。

### 流程分级

| 级别 | 触发蓝图 | 门禁 |
|---|---|---|
| full | 个股深度/资产研究/租金资产 | 审计+PUA(P9)+premortem/base_rate 强制+技法开放 |
| standard | 主题量化/更新报告 | 审计+PUA(P7)+base_rate |
| minimal | 策略手册/科普/决策测算 | 仅 QA |
| /ask | 一律 | 按 full 门禁执行（章节结构仍按报告类型推导） |

## 目录结构

```
.opencode/
├── command/                    # /grill /report /drill /ask
└── skill/stock-analysis/
    ├── SKILL.md                # 主协议（全自治流水线 10 步与铁律）
    ├── CHANGELOG.md
    ├── requirements.txt
    ├── scripts/                # 19 个 Python 库
    │   ├── workspace_lib.py    #   编号账本/工作区/双写交付
    │   ├── brief_lib.py        #   多波次 grill / self-grill 需求书
    │   ├── technique_lib.py    #   技法注册表（推荐/激活/自动扩充）
    │   ├── fetch_lib.py        #   东财/腾讯/乐咕/巨潮/现货/宏观 数据源
    │   ├── forecast_lib.py     #   盈利预测（假设证据链+基础比率）
    │   ├── valuation_lib.py    #   估值算子+加权合成+翻车点
    │   ├── socratic_lib.py     #   单次审计引擎+四道闸
    │   ├── manager_log.py      #   PUA 逐章审问记录
    │   ├── thesis_lib.py       #   论点树（结论→承重柱→证据映射）
    │   ├── review_lib.py       #   复盘档案闭环（校准率/失误模式）
    │   └── selftest.py         #   离线自测 51 用例
    └── reference/
        ├── library/            # JSON 规则库（方法/源/蓝图/回测/分歧/技法）
        ├── templates/          # grill·self-grill×2·desk_chief·single_auditor·drill
        ├── subagent-protocol.md    # 子代理防火墙与输入包规范
        └── analysis-techniques.md  # 20 技法协议（含来源标注）
```

运行期产物（不入库，`.gitignore` 已排除）：`reports/{编号}_{主题}/` 九区工作区、`reports/所有报告/` docx 汇集、`档案/` 复盘 dossier。

## 自测

```bash
cd .opencode/skill/stock-analysis
python scripts/selftest.py --offline   # 51 用例全 PASS、退出码 0
```

## 方法论来源（三级优先级：机构 > 教材·论文 > GitHub）

- **机构**：CIA《Structured Analytic Techniques》（premortem/ACH/KAC）、FINRA 3110 单一终审签发、NATO Admiralty 信源分级、MSCI Barra 归因、Morningstar 护城河、Shell 情景规划、ECB/FSA 反压力测试、RAND Delphi
- **教材·论文**：Kahneman《思考，快与慢》外部视角、Flyvbjerg 参考类预测、Heuer《情报分析心理学》、Damodaran《Investment Valuation》、Piotroski 2000 / Beneish 1999 / Altman 1968、MacKinlay 事件研究
- **GitHub 原型**：RobMitt/grill-me-skill（多选拷问协议）、tanweai/pua（分级人设审问）、TauricResearch/TradingAgents（扁平专家+单一终审门+单辩论周期）、mattpocock/skills（grilling 原语/并行隔离评审）

版本历史见 [CHANGELOG](.opencode/skill/stock-analysis/CHANGELOG.md)。
