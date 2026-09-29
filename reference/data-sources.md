# [已废弃] 本文件已被 JSON 规则库替代

> **状态：DEPRECATED（2026-08）**——内容已迁移至 `reference/library/`（methods.json / sources.json，带画像谓词可程序化推导）。本文件仅作历史审计保留，**新任务不得引用**。接口细节（URL/字段/限制）仍可作实现参考。

# 数据源目录（股票分析 skill 专用）

历史项目（D:\project\nianhua 2026-08 清理前）已验证的数据源与确切接口。优先顺序：**东方财富 > 腾讯 > 官方指数（CSIndex/CNIndex/恒指公司）> 乐咕 > 其他**。

## 1. 东方财富（主源，免费无需登录）

| 用途 | 接口 | 说明 |
|---|---|---|
| 批量行情快照 | `https://push2delay.eastmoney.com/api/qt/ulist.np/get` | params: `secids=1.000300,0.000001…`, `fields=f12,f14,f2,f3,f5,f6,f8,f9,f20,f21,f23,f62`；f9=PE(TTM) f20=总市值 f23=PB。**一次最多约 100 个** |
| 板块/行业列表 | `https://push2delay.eastmoney.com/api/qt/clist/get` | 板块代码形如 `90.BK0475`（行业） |
| 个股/指数行情 | `https://push2delay.eastmoney.com/api/qt/stock/get` | secid 格式 `1.600754`（沪）/`0.000001`（深/指数） |
| K线 | `https://push2his.eastmoney.com/api/qt/stock/kline/get` | params: `secid, klt(101日/102周/103月), fqt(0/1/2), beg, end, lmt`；fields2 `f51…f61`：日期/开/收/高/低/量/额/振幅/涨跌幅/涨跌额/换手。**注**：`em_kline` 内置三级容错：push2his → push2delay（部分网络仅返回空 klines）→ 腾讯 fqkline（字段对齐，amount/amplitude 为 None、pct 计算）；腾讯回退仅支持日/周/月且 count≤800 |
| F10 财务（datacenter） | `https://datacenter-web.eastmoney.com/api/data/v1/get` | params: `reportName, columns, filter=(SECUCODE="600754.SH"), pageNumber, pageSize, sortTypes=-1, sortColumns=REPORT_DATE, source=HSF10, client=PC` |

**datacenter 常用 reportName 与关键字段**：
- `RPT_F10_FINANCE_GBALANCE`（资产负债表）：`GOODWILL`(商誉), `INTANGIBLE_ASSET`, `TOTAL_ASSETS`, `TOTAL_LIABILITIES`, `TOTAL_PARENT_EQUITY`, `MONETARYFUNDS`
- `RPT_F10_FINANCE_GINCOME`（利润表）：`TOTAL_OPERATE_INCOME`, `OPERATE_COST`, `PARENT_NETPROFIT`, `DEDUCT_PARENT_NETPROFIT`, `TOTAL_PROFIT`, `ASSET_IMPAIRMENT_LOSS`, `CREDIT_IMPAIRMENT_LOSS`, `FINANCE_EXPENSE`, `INVEST_INCOME`, `ASSET_DISPOSAL_INCOME`
- `RPT_F10_FINANCE_GCASHFLOW`（现金流量表）：`NETCASH_OPERATE`, `NETCASH_INVEST`, `NETCASH_FINANCE`, `FA_IR_DEPR`(折旧), `IA_AMORTIZE`, `USERIGHT_ASSET_AMORTIZE`(使用权资产摊销)
- `RPT_F10_FINANCE_MAINFINADATA`（主要指标）：`EPSJB`, `EPSKCJB`, `TOTALOPERATEREVE`, `ROEJQ`, `ROEKCJQ`, `XSMLL`(毛利率), `XSJLL`(净利率), `PARENTNETPROFIT`

旧版 F10（备用）：`https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/zcfzbAjaxNew`（资产负债表）、`lrbAjaxNew`（利润表）。

基金（东财）：`https://fund.eastmoney.com/js/fundcode_search.js`（全量基金代码表）、`https://fund.eastmoney.com/pingzhongdata/{code}.js`（经理/净值数据）、`http://fundf10.eastmoney.com/jbgk_`、`http://api.fund.eastmoney.com/f10/lsjz`（历史净值）。

## 2. 腾讯（行情备用/交叉验证）

- 实时行情：`https://qt.gtimg.cn/q=sh600754,sz000001`（GBK 编码，`~` 分隔）。字段索引：1现价 2昨收 3今开 4成交量(手) 5外盘 6内盘 30时间 31涨跌 32涨跌% 33最高 34最低 38换手率 39PE 43振幅 45流通市值 46总市值 47PB 48涨停 49跌停
- 复权K线：`https://web.ifzq.gtimg.cn/appstock/app/fqkline/get`，params: `param=sh600754,week,2016-01-01,2026-08-13,600,qfq`；返回 JSON `data.{symbol}.qfqweek/qfqday/qfqmonth`，行格式 `[date, open, close, high, low, volume, …]`。period: `day/week/month`；fqt: `qfq`(前复权) / `hfq`(后复权) / 空。**count 上限 800**，过大（如 5000）会导致接口返回异常

## 3. 官方指数

- CSIndex（中证）：`https://www.csindex.com.cn/csindex-home/index-value/index-value`（指数行情）、`perf/index-perf`（表现）；估值 xls 下载：`https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/file/autofile/indicator/{code}indicator.xls`（如 000300indicator.xls，含 PE/PB/股息率）
- CNIndex（国证）：`http://hq.cnindex.com.cn/market/market/getIndexDailyDataWithFormat`、`market/getIndexMonthData`
- 恒指公司（港股指数）：`https://www.hsi.com.hk/api/wsit-hsil-hiip-ea-public-proxy/v1/dataretrieval/e/{constituents,dailyClose,performance}/v1`；Factsheet PDF：`https://www.hsi.com.hk/static/uploads/contents/.../factsheets/{code}.pdf`

## 4. 乐咕乐股（指数估值历史分位，需反爬）

- `https://legulegu.com/api/stockdata/index-basic-pe`（params: `ts=时间戳, stockCode=000300, lang=zh-CN`）、`index-basic-pb`、`index-valuation-history`、`industry-pe`、`industry-pe-ttm`、`sw-industry-2021`
- 反爬：首次请求返回含 token 的 JS 挑战，需用 **py_mini_racer**（包名 `mini-racer`）执行 akshare 的 `get_cookie_csrf`/`hash_code` 逻辑；最简单做法：`import akshare as ak; ak.stock_market_pe_lg()` 或 `ak.stock_index_pe_lg(symbol="沪深300")`。历史项目用 `py_mini_racer` 直接解过（见旧脚本 step2d_legulegu.py 方案）

## 5. 新浪（列表/分红）

- A/B 股列表：`https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData`
- 分红历史：`https://money.finance.sina.com.cn/corp/go.php/vISSUE_ShareBonus/stockid/{code}.phtml`（GBK）
- 港股K线：`https://quotes.sina.cn/hk/api/jsonp_v2.php/.../CN_MarketDataService.getKLineData`

## 6. 公告与年报

- 巨潮资讯 CNINFO：`http://www.cninfo.com.cn/new/hisAnnouncement/query`（公告列表 POST）、PDF 文件域 `http://static.cninfo.com.cn/`（历史项目抓取锦江 2014—2025 年报 PDF，再 pypdf 提取文本）

## 7. 海外/宏观

- Yahoo Finance：`https://query1.finance.yahoo.com/v8/finance/chart/{symbol}`（600754.SS、美股、港股）
- FRED：`https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}`（US10Y、US2Y、FEDFUNDS）
- Stooq：`https://stooq.com/q/d/l/?s=^spx`（美股指数历史）
- 网易：`https://img1.money.126.net/data/hk/kline/day/his/{code}.json`（港股K线备用）

## 8. akshare 封装对照（优先用 akshare，失败再手写）

`stock_market_pe_lg` / `stock_zh_index_value_csindex` / `stock_zh_index_daily(_tx)` / `bond_china_yield` / `macro_china_lpr` / `stock_margin_sse` / `fund_scale_change_em` / `fund_etf_fund_daily_em` / `stock_board_industry_hist_ths` / `index_hist_sw` / `stock_fhps_detail_em` / `currency_boc_sina` / `index_zh_a_hist` / `macro_china_cpi_monthly` / `macro_china_ppi_monthly`

## 数据落地规范

- 原始数据按主题存 `data/` 或 `{主题}_data/` 目录，统一 `save_json`/`to_csv(encoding='utf-8-sig')`
- 每个分析任务生成 2~3 个可复用结果 JSON（`results_*.json`），避免重复抓取
- 数据抓取脚本与报告生成脚本分离：`fetch_*.py` → `*_analysis.py` → `*_charts.py` → `*_report.py`
- 抓取必须带 `User-Agent`；批量抓取加 `time.sleep(0.3)` 限速；失败重试 3 次
