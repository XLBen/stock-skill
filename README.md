# stock-skill · 泛金融报告分析全自治流水线（v3.4-lite · 省 token 版）

> 一个 [opencode](https://opencode.ai) skill：从"一句话提问"到"带审计的 Word 研报"，全程无人值守。
> 适合 A股/港美股/基金/利率/地产/加密/收藏品等**任意资产对象**——按资产属性推导方法，而非套模板。

```
/ask "XX股份现在能买吗"
  └─ self-grill 单轮推导需求（零人工）
      → 8 维画像推导方法集 → 数据侦察(FACTS 冻结) → 预测/估值(数字由代码算)
      → 单写手分章写作 + 总监审问一次 → 单次审计(R1) → QA → 编号归档 docx
```

## 核心特性

| 特性 | 说明 |
|---|---|
| **省 token 设计** | 需求 1 波问清；子代理 ≤3（侦察/写手/审计各 1）；PUA 全稿只审 1 次；审计 R1 定案；篇幅按蓝图降档（full 8000 / standard 6000 / minimal 4000 / update 3000 字符） |
| **grill 需求拷问** | 一批 5~6 问覆盖全部必填字段，模糊答案才追问（上限 2 波），产出 brief.json 并批准（唯一人工门） |
| **self-grill 零人工** | `/ask` 一句话：拷问者×应答者各 1 轮推导需求，自动批准直接出报告 |
| **8 维画像推导** | 现金流/披露/供给/流动性/价格行为等属性 → JSON 规则库谓词匹配出方法集/数据源/报告蓝图；地产禁 PE、手办禁 DCF |
| **技法注册表** | 20 项分析技法按需激活，每个挂点 ≤3 且必填理由；无合适技法按证据门槛自动扩充 |
| **数字由代码算** | 预测/估值只出自 `forecast_lib`/`valuation_lib` 算子，LLM 手算即违规；假设必带证据链与基础比率锚 |
| **PUA 总监审问** | 全稿写完后一次：先自攻验证（SELF_ATTACK 三问），再 ≤3 专业问 + ≤1 通俗问，驳回自动重写 ≤1 次 |
| **单次审计·四道闸** | R1 攻防定案（full ≥4 条含 ≥1 替代解读/隐含前提；standard ≥3）；火力/覆盖/门禁三闸全过才许终稿 |
| **编号存档与追问复盘** | 每报告一编号一工作区，docx 双写交付；`/drill 编号` 回溯拷问，第 N 份站在第 N-1 份肩上 |

## 安装

依赖 [opencode](https://opencode.ai) 与 Python 3.10+：

```bash
# 1. 把本仓库放进你的项目，得到：
#    your-project/.opencode/skill/stock-analysis/
#    your-project/.opencode/command/{grill,report,drill,ask}.md
git clone https://github.com/XLBen/stock-skill.git
cp -r stock-skill/.opencode/ your-project/.opencode/

# 2. 安装 Python 依赖
pip install -r stock-skill/.opencode/skill/stock-analysis/requirements.txt

# 3. 重启 opencode（命令与 skill 在启动时加载）
```

可选：渲染目检需 LibreOffice（缺失自动跳过）。

## 命令

| 命令 | 用途 |
|---|---|
| `/ask 一句话问题` | **零人工**：self-grill 单轮 → full 级流水线 → docx |
| `/grill [主题\|编号]` | 需求拷问 1 波 → 批准 brief（**唯一人工门**） |
| `/report [编号\|主题\|resume 编号]` | 执行全自治流水线至交付；`resume` 从 blocked 态恢复 |
| `/drill [编号]` | 追问：draft→需求变更重审；delivered→回溯拷问+复盘落档 |

PUA 总监审问**没有命令**——它在全稿完成后由主上下文自动执行一次。

## 流水线（6 步，brief 批准后无人值守）

1. brief：grill / self-grill → `brief.json`（1~2 波，唯一人工门）
2. 画像推导 + 技法候选（`profile_lib.derive` + `technique_lib.recommend`）
3. 数据侦察兵子代理 ×1（缓存优先）+ `FACTS.md` 中性事实清单**冻结**
4. 预测建模 + 估值（`forecast_lib`/`valuation_lib`，数字由代码算；premortem/base_rate 强制）
5. 论点树 → 单写手顺序写全稿 → PUA 全稿审问 1 次（`manager_log`）
6. 单次审计（`socratic_lib` mode='single_audit'，R1）→ QA（0 错误）→ 编号归档（`70_delivered/` + `reports/所有报告/{编号}_{名}.docx`）+ 完成摘要

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
    ├── SKILL.md                # 主协议（v3.4-lite 流水线 6 步与省 token 原则）
    ├── CHANGELOG.md
    ├── requirements.txt
    ├── scripts/                # 20 个 Python 库（工作区/brief/技法/抓数/预测/估值/审计/PUA/QA）
    └── reference/
        ├── library/            # JSON 规则库（方法/源/蓝图/回测/分歧/技法）
        ├── templates/          # grill·self-grill×2·desk_chief·single_auditor·drill
        ├── subagent-protocol.md    # 子代理防火墙与输入包规范
        └── data-sources.md / docx-conventions.md / analysis-methods.md / analysis-techniques.md
```

运行期产物（不入库，`.gitignore` 已排除）：`reports/{编号}_{主题}/` 九区工作区、`reports/所有报告/` docx 汇集、`档案/` 复盘 dossier。

## 自测

```bash
cd .opencode/skill/stock-analysis
python scripts/selftest.py --offline   # 全套用例 PASS、退出码 0
```

## 方法论来源（三级优先级：机构 > 教材·论文 > GitHub）

- **机构**：CIA《Structured Analytic Techniques》（premortem/ACH/KAC）、FINRA 3110 单一终审签发、NATO Admiralty 信源分级、Morningstar 护城河、Shell 情景规划
- **教材·论文**：Kahneman《思考，快与慢》外部视角、Flyvbjerg 参考类预测、Heuer《情报分析心理学》、Damodaran《Investment Valuation》、Piotroski 2000 / Beneish 1999 / Altman 1968
- **GitHub 原型**：RobMitt/grill-me-skill（多选拷问协议）、tanweai/pua（自我怀疑式审问）、TauricResearch/TradingAgents（扁平专家+单一终审门）
