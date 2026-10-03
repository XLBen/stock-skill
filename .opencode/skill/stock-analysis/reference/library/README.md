# 规则库说明（reference/library/）

股票分析 skill 的核心是"**按资产属性推导，而非按资产类型查表**"。本目录存放全部推导规则（JSON 数据驱动），新增方法/源/蓝图 = 加一条带谓词的 JSON 条目，**无需改代码**。

## 文件

| 文件 | 内容 | 谓词字段 |
|---|---|---|
| `profiles.json` | 预设资产档案（快捷方式，非禁区） | 属性值（非谓词） |
| `methods.json` | 分析方法库（含参数锚与注意事项） | `applies` |
| `sources.json` | 数据源库（含接口要点与 TTL） | `applies` |
| `blueprints.json` | 报告蓝图（章节元素规格 + 专属 QA） | `applies`（按 type+画像选） |
| `backtest.json` | 回测规则集（网格/定投） | `applies` |
| `dispute.json` | 方法分歧/正反论证判定阈值 | —（配置） |

## 画像字段与谓词语法

画像（profile）字段：`cf`(现金流 有/租金型/无)、`disc`(披露 有/无)、`supply`(供给 无限/稀缺/限量)、`hold_cost`(0~2)、`liq`(高/中/低)、`beh`(价格行为 均值回归/趋势/周期)、`tplus`(bool)、`short`(bool)、`min_unit`(int)、`data`(数组: kline/chain/listing/trade/index/research)、`inv`(投资/收藏/消费)。

谓词示例：`cf=有 & disc=有`、`cf=无 & (supply=限量 | supply=稀缺)`、`data=kline & tplus=true`、`hold_cost>=1`、`true`（恒真）。

## 新增条目流程

1. 加 JSON 条目（`applies` 谓词必须能由 profile 求值，可先本地 `eval_pred` 验证）
2. `python scripts/selftest.py --offline` 确认推导用例不回归
3. 条目写回后旧文档不得再被引用

## 手办分析全流程示例（画外对象推导）

目标：分析某限定手办的二级市场价值（画像推导而非枚举）。

### 1. 画像（8 问 → profile）
```
cf=无（无现金流）  disc=无（无财务披露）  supply=限量（限定发售）
hold_cost=1（仓储）  liq=低（二级成交稀疏）  beh=趋势
tplus=false  short=false  min_unit=0
data=listing,trade（二手成交记录可得）  inv=收藏
```

### 2. 推导（derive）
- **方法集**：`replacement_cost`（再版/替代价）、`price_index`（成交价指数化，类比 CCPI）、`scarcity_premium`（限量溢价）、`stats_baseline`（统计兜底）
- **蓝图**：`asset_research`（无财务章；含供给/稀缺性、成交与价格特征、估值锚、情景与建议）
- **源**：成交/挂牌数据（无东财行情 → em_quotes 因 data=trade 匹配但实际不可用，报告须注明数据源为社区/平台成交记录）
- **回测**：无（流动性低、无 T+1 K 线 → 禁止网格/日频回测）

### 3. 报告结构（按蓝图 v2：asset_research）
封面 → 摘要（区间/中枢+供需速览）→ 资产概况与稀缺性 → 需求与持有者结构 → **供需平衡表（心脏：历史平衡+预测假设带标签）** → 成交与价格特征 → 估值锚 → 情景与建议 → 风险提示（独立成章）→ 反方论点（质询驱动）+ 强制章节 + 附录（溯源/质询统计/数据截止表）

蓝图还有 `flow` 字段控制流程分级：`full`=全流程（单次审计+PUA P9+强制技法）/`standard`=单次审计+PUA P7/`minimal`=仅 QA；`update_report`（更新报告）类型复用档案可继承资产做增量复核。v3.0：报告按编号存档于项目根 `reports/{编号}_{主题}/`（brief+FACTS+会话+草稿+历史word）与 `reports/所有报告/{编号}_{报告名}.docx`；旧 data/ 目录只读保留。

### 4. 取证与质检
- 无研报覆盖（`data=research` 不匹配）→ **取证降级**：报告标注"无业界惯例，方法为统计性描述"
- `dispute_analysis`：价格指数法与稀缺溢价法分歧 >20% → 插入正反论证章节
- `cache_status` / `check_delivery` 常规执行

## 反例（谓词如何防止逻辑套用）

| 对象 | 禁止 | 原因（谓词不匹配） |
|---|---|---|
| 房价 | PE/PB 分位、DCF | cf=租金型 而非 有（pe_quantile applies cf=有）|
| 比特币 | DCF、PE、股息率 | cf=无 且 data=chain 匹配 nvt_mvrv 而非现金流方法 |
| 手办 | 网格回测 | tplus=false / data 无 kline |
| 医疗险/社保决策 | 全部估值方法 | 属"决策测算"蓝图（decision_report），不推导估值方法 |
