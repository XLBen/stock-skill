# 规则库（reference/library/）

核心: 按资产属性推导而非按类型查表; JSON 驱动, 新增=加谓词条目, 无需改代码。

| 文件 | 内容 | 谓词 |
|---|---|---|
| profiles.json | 资产档案(快捷) | 属性值 |
| methods.json | 方法库 | `applies` |
| sources.json | 数据源库(接口+TTL) | `applies` |
| blueprints.json | 报告蓝图(章节+QA+layout_rules) | `applies` |
| backtest.json | 回测规则(网格/定投) | `applies` |
| dispute.json | 分歧/正反论证阈值 | 配置 |

画像字段: cf(有/租金型/无) disc(有/无) supply(无限/稀缺/限量) hold_cost(0~2) liq(高/中/低) beh(均值回归/趋势/周期) tplus short min_unit data(kline/chain/listing/trade/index/research) inv(投资/收藏/消费)。
谓词例: `cf=有 & disc=有`、`cf=无 & (supply=限量 | supply=稀缺)`、`data=kline & tplus=true`、`hold_cost>=1`、`true`。

新增: ① 加 JSON(`applies` 可由 profile 求值, 先 `eval_pred` 验证)→ ② `selftest.py --offline` 不回归→ ③ 旧文档不得再引用。

流程分级(`flow`): full=审计+PUA P9+强制技法/standard=审计+PUA P7/minimal=仅 QA; `update_report` 复用档案增量复核。归档 `reports/{编号}_{主题}/`+`reports/所有报告/{编号}_{名}.docx`。

反例(谓词防套用): 房价禁 PE/PB 分位、DCF(cf=租金型); 比特币禁 DCF/PE/股息率(cf=无, 匹配 `nvt_mvrv`); 手办禁网格(tplus=false/无 kline); 医疗险/社保决策不推导估值(decision_report)。
