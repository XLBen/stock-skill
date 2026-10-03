# 子代理协议与上下文防火墙（v3.0）

> 防两件事：**上下文污染**（带着前文结论找数据）与**动机性推理**（带着结果找答案）。
> 铁律：主上下文=纯编排器（状态机+文件索引导航+规则执法），**不产出任何分析文本、不转述任何数字**——数字只经算子库与落盘文件流动。

## 输入包规范

每个子代理 = 全新上下文 Task，只收到**显式输入包**：

```
输入包 = 3~8 个已登记文件路径（来自 WORKSPACE.md）+ 任务协议（模板路径）+ 输出槽位（落盘路径）
```

- 禁止目录级投喂（不给整个 data/）；禁止把主上下文对话摘要塞给子代理
- 输出 = 落盘文件 + 结构化 JSON 摘要（不是长篇对话回传）
- 导航唯一入口：`_registry.json`（跨报告）+ 工作区 `WORKSPACE.md`（报告内），禁止全库 glob

## 角色与隔离矩阵

| 角色 | 时机 | 输入包 | 隔离要点 |
|---|---|---|---|
| **grill 主持**（主上下文） | 需求阶段 | question 工具 | 唯一用户在场环节；结果=brief.json |
| **自我拷问者**（/ask 子代理A） | self-grill 波次 | 原始问题+brief状态+dossier+对方上轮答案 | 与应答者互不可见（对话经编排器文件总线）；输出问题 JSON |
| **代理应答者**（/ask 子代理B） | self-grill 波次 | 原始问题+dossier+本轮问题 | 扮演提问者：每答标 [代理推断·强/中/弱] 或 中性·不确定；禁编造私有信息；答案互不矛盾 |
| **数据侦察兵** | 数据抓取步 | brief 字段+推导源集 | **不知任何论点/结论**；只产 00_cache/* + `10_facts/FACTS.md`（纯数字+来源+口径，禁解读） |
| **技法分析师×N** | 各技法挂点 | FACTS+thesis+该技法 protocol（analysis-techniques.md 对应节） | **彼此并行互不可见**（就绪前沿派发）；各写独立输出文件 |
| **章节写手** | 写作步（严格顺序） | 章节spec+thesis+FACTS+该章数据文件 | 顺序写作（风格一致）；**禁自行抓数**（四眼原则：取数与解读分人）；不见他章 PUA 对话 |
| **PUA 管理员** | 每章交付后 | 该章草稿+章摘要+thesis | desk_chief.md；≤3 问；不做深度对抗 |
| **单次审计员** | 终稿前 | 全文 dump+thesis.json+failure_criteria | **唯一看全稿的对抗角色**；全新上下文；承重柱从树机械提取 |
| **QA/追问官** | 交付后 /drill | WORKSPACE.md+产物 | check_* 脚本 + drill_interrogator.md |

## FACTS 冻结协议（防"带着结果找答案"三道闸之一）

1. `10_facts/FACTS.md` 由侦察兵在抓取步产出：中性事实清单（指标|数值|口径|asof|来源文件），**禁止任何解读性文字**
2. 预测建模开始前 FACTS 冻结：此后发现缺数据 → 新开一次侦察任务补条目，**禁止写手/预测者边写边抓**
3. 建模与写作只消费 FACTS + 算子输出文件；侦察兵不知道 brief 的重点关切倾向（防止顺着预期找数）

## 异常自动归宿（无人值守，绝不悬停等人）

| 异常 | 自动路径 |
|---|---|
| PUA 驳回 | 自动重写（同章 ≤1 次）→ 二次驳回转审计未决（manager_log.escalated） |
| 审计 revise 假设 | H1 回流：重跑 forecast_lib → valuation_lib → 更新树 → R2 核验 |
| 数据源失败 | 降级标注/盲点清单（spot_price 等返回 None 必须明示） |
| 技法不足 | technique_lib.propose_auto 按证据门槛自动扩充 |
| 轮次/预算超限 | workspace_lib.blocked(编号, 卡点, `/report resume 编号`) |

来源：TauricResearch/TradingAgents（扁平专家+单一终审门+agent 间仅传结构化报告）· RAND Delphi（匿名独立估计防锚定）· Heuer《Psychology of Intelligence Analysis》（描述与解读分离）· 银行四眼原则 · mattpocock/skills code-review（parallel sub-agents so neither pollutes the other）。
