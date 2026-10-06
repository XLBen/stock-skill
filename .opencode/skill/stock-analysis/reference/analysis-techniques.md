# 分析技法手册

注册表 `techniques.json`。挂点 `technique_lib.recommend(profile,stage,blueprint_id,flow_level)`, 激活 ≤3/挂点并 `activate(flow_log,id,reason)`; always_on: full `premortem`, standard/full `base_rate`。无合适方法论→`propose_auto()`: tier 机构方法论>教材·论文>GitHub·业界实践(≥100⭐), 非空 cite, 落 auto 区(≤20), 标"新引入技法"。标签: [实证]=文件字段出处, [推断]=带 `base_rate_ref`, [观点]=主观缺链拦截; 假设=标签+依据+概率。

| id | 协议 |
|---|---|
| premortem | full 强制; 12 月打脸列 3~5 死因→风险章 |
| moat_scoring | 五源评无/窄/宽, 各≥1 证据数字, 无证据禁入树 |
| base_rate_outside_view | full/standard 强制; 增长 [推断] 锚参考类, 缺 `base_rate_ref` 降 [观点] |
| key_assumptions_check | 假设>8/依赖链: 显隐枚举, 敏感性×不确定性排序 |
| delphi_estimate | ≥3 背靠背独立估计取中位, 分歧>20% 标记高不确定性 |
| ach_matrix | `ach_matrix()` 证据×假设矩阵, 最少不一致排序 |
| scenario_2x2 | 两强相关驱动为轴→四象限 |
| tornado_sensitivity | 参数>5 逐个±档重跑, Top2 进 `flip_point` |
| piotroski_fscore | 9 二元判据对照行业, 低分查现金流 |
| beneish_mscore | 8 指数, M>-1.78 预警→风险章 |
| altman_zscore | Z/Z' 灰区, Z<1.8 高危→降档 |
| indicators_signposts | 每核心假设 2~3 先兆 进 review_triggers |
| inversion | 列"保证失败"清单→反推规避 |
| reverse_stress_test | 找杀死结论最小变动; 概率>10% 降置信 |
| second_order_effects | 一阶→二阶反馈, 高杠杆进风险 |
| event_study | data=kline: T-5~T+20 超额统计 |
| kelly_position | data=kline: f*=(bp-q)/b 折半, 仓位上限 |
| factor_attribution | 收益=β+风格+残差α, 失误进 error_patterns |
| five_whys | 5 Why 到方法层根因→80_reflection |
| admiralty_grading | 信源 A~F×1~6, 低级降标签/盲区 |
