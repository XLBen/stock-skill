# 分析技法手册（analysis-techniques）

> 技法注册表 `reference/library/techniques.json` 的协议正文。技法**不全部使用**：
> 编排器每到挂点调 `technique_lib.recommend(profile, stage, blueprint_id, flow_level)` 取候选，
> 自主决定激活（每挂点 ≤3，必填理由，`technique_lib.activate(flow_log, id, reason)` 登记）。
> always_on 项（如 full 级 premortem）不可跳过。注册表无合适方法论 →
> `technique_lib.propose_auto()` 按证据门槛自动扩充（来源优先级：机构方法论 > 教材·论文 > GitHub·业界实践，≥100⭐）。

## 预测前

### premortem 事前验尸（full 强制）
假设 12 个月后这份报告的结论被完全打脸。列 3~5 条最可能死因：每条含【失败路径】【受害假设】【可观测先行信号】。产出进：风险章预警信号、assumption_validity 失效信号、review_triggers。
来源：Gary Klein (HBR 2007)；CIA《Structured Analytic Techniques》。

### moat_scoring 五源护城河评级（equity）
网络效应/无形资产/成本优势/转换成本/有效规模逐项评 无/窄/宽，每项 ≥1 可溯源证据数字（毛利对比/费用率/市占趋势）。无证据的护城河柱禁入论点树。
来源：Morningstar 经济护城河方法论（Pat Dorsey）。

## 假设校验

### base_rate_outside_view 基础比率外部视角（full/standard 强制）
增长/改善类 [推断] 假设必须锚参考类：行业历史增速分布/同类公司达成率（指向数据文件）。`forecast_lib.Assumption(base_rate_ref=...)`；缺→自动降级 [观点]（base_rate_downgrades 落盘并在报告标注）。报告 divergent_views 章含基础比率对比表。
来源：Kahneman《Thinking, Fast and Slow》；Flyvbjerg 参考类预测（DfT/丹麦强制）。

### key_assumptions_check 关键假设清单核对
假设 >8 条或有依赖链时：枚举全部显式+隐含假设 → 按 敏感性×不确定性 排序 → 隐含假设显式化进假设表。来源：CIA SAT。

### delphi_estimate 匿名独立估计聚合
关键参数无权威锚且分歧大：≥3 个隔离子代理背靠背独立估计+理由（互不可见）→ 聚合取中位 → 分歧 >20% 的参数移交质询。来源：RAND Delphi。

## 分歧

### ach_matrix 竞争性假设矩阵
dispute_analysis 触发或互斥解读存在时：`profile_lib.ach_matrix(hypotheses, evidence)` 建证据×假设矩阵（每格 一致/不一致/无关），按**最少不一致**排序（证据可与多假设一致，只有"不一致"有区分力）；诊断性证据标注；矩阵表进分歧章节。
来源：Heuer《Psychology of Intelligence Analysis》Ch.8；CIA Tradecraft Primer。

## 情景

### scenario_2x2 双驱动轴情景
联合脆弱质询暴露两个强相关不确定驱动时：取为轴 → 四象限各给【叙事】【估值影响】【先行指标】→ 情景权重进 weighted_synthesis 敏感性；替代线性保守/中性/乐观三档。
来源：Shell 情景规划；Schwartz《The Art of the Long View》。

### tornado_sensitivity 龙卷风敏感性排序
敏感性参数 >5 个：逐参数 ±档位重跑中枢 → 按影响幅度排序 → Top2 进 flip_point 联合分析。来源：Damodaran《Investment Valuation》。

## 财务质量（cf=有 & disc=有）

### piotroski_fscore：9 项二元判据（盈利/杠杆/营运），对照行业分布；低分项联动净利-现金流匹配检查。来源：Piotroski, JAR 2000。
### beneish_mscore：8 指数（DSRI/GMI/AQI/SGI/DEPI/SGAI/LVGI/TATA），M > -1.78 预警 → 风险章+核查审计意见。来源：Beneish, FAJ 1999。
### altman_zscore：Z/Z' 变体计算，灰区标注，Z<1.8 高危 → 风险章+假设降档。来源：Altman, JF 1968。

## 风险

### indicators_signposts 先行指标与路标
每个核心假设配 2~3 个可观测先行指标（频率+数据源+警戒线）→ 投资建议跟踪清单+review_triggers。来源：情景规划 signposts 规程（Shell/GBN）。

### inversion 逆向思维
列"保证这笔投资失败"的行为/条件清单 → 反向推导规避动作 → 与风险章互查缺口。来源：Munger 逆向思维。

### reverse_stress_test 反压力测试
从"结论失效"反推参数组合；找杀死结论的最小参数变动（衔接 flip_point）；情景合理概率 >10% 必须进风险章并下调置信度。来源：ECB/FSA 监管方法论。

## 行业驱动

### second_order_effects 二阶效应
驱动→一阶效应→二阶反馈链（含各方博弈反应）；标注放大/衰减；高杠杆二阶项进风险与情景。来源：Meadows《Thinking in Systems》。

## 催化剂（data=kline）

### event_study 事件研究
同类历史事件定窗口（T-5~T+20）→ 超额收益/波动统计 → 标注样本量与显著性（类比≠预言）。来源：MacKinlay, JEL 1997。

## 仓位（data=kline）

### kelly_position 仓位测算
中枢/区间与置信度推不对称赔率 → f*=(bp-q)/b 折半（半 Kelly 风控惯例）→ 只作仓位提示上限，写明假设。来源：Ed Thorp 实践；Kelly 1956。

## 复盘

### factor_attribution 多因子归因：收益分解（市场β+风格因子+残差α），残差与论点对照，失误归因进 error_patterns。来源：MSCI Barra。
### five_whys 五问归因：失误表象连问 5 Why 到方法层根因 → 映射改进项 → 80_reflection。来源：Toyota。

## 数据质量

### admiralty_grading 信源分级：Admiralty 码（可靠性 A~F × 可信度 1~6）评级；低级信源论断降标签或进盲区；附录数据表带评级列。来源：NATO Admiralty Code。

## 自动扩充协议（propose_auto）

1. 触发：挂点 recommend() 为空/不足且存在真实分析缺口（写明缺口+判据）
2. 提案：{id, name, stage, trigger, protocol, applies, sources[{tier, cite}]}
3. 门槛：≥1 来源，tier ∈ 机构方法论/教材·论文/GitHub·业界实践，cite 非空；谓词须可求值
4. 落盘：techniques.json **auto 区**（core 区仅人工维护），上限 20 条；flow_log 记 technique_auto_added
5. 标注：使用 auto 技法的报告在附录"新引入技法"处标注（technique_lib.techniques_used(flow_log)）
