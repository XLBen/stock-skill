# 数据源

优先级 东财>腾讯>官方指数>乐咕>其他。入口 `fetch_lib`: `em_quotes` `em_kline` `em_f10` `tx_quote` `tx_kline` `lg_index_pe` `cninfo_notices` `spot_price` `macro_industry` `pdf_text` `cache_meta_table`。通用: User-Agent, 限速 0.3s, 重试 3, `save_json`/`load_json` 缓存 TTL+幂等覆盖, 源失败/None 须明示。

东财(主源): 批量 `push2delay.eastmoney.com/api/qt/ulist.np/get`(**≤100 只**; `fields`, f9=PE(TTM)/f20=总市值/f23=PB), 板块 `.../api/qt/clist/get`(`90.BK0475`), 个股/指数 `.../api/qt/stock/get`(`1.600754`/`0.000001`), K线 `push2his.eastmoney.com/api/qt/stock/kline/get`(`secid,klt,fqt,beg,end,lmt`; `em_kline` 容错 push2his→push2delay→腾讯), F10 `datacenter-web.eastmoney.com/api/data/v1/get`(`reportName,columns,filter,pageNumber,pageSize,sortColumns,source=HSF10`; `RPT_F10_FINANCE_GBALANCE/GINCOME/GCASHFLOW/MAINFINADATA`), 旧F10 `emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/zcfzbAjaxNew`,`lrbAjaxNew`, 基金 `fund.eastmoney.com/js/fundcode_search.js`,`fund.eastmoney.com/pingzhongdata/{code}.js`,`api.fund.eastmoney.com/f10/lsjz`

腾讯: `qt.gtimg.cn/q=sh600754,sz000001`, `web.ifzq.gtimg.cn/appstock/app/fqkline/get`(**count≤800**)

官方指数: 中证 `csindex.com.cn/csindex-home/index-value/index-value`,`.../perf/index-perf`,`oss-ch.csindex.com.cn/static/html/csindex/public/uploads/file/autofile/indicator/{code}indicator.xls`; 国证 `hq.cnindex.com.cn/market/market/getIndexDailyDataWithFormat`,`.../getIndexMonthData`; 恒指 `hsi.com.hk/api/wsit-hsil-hiip-ea-public-proxy/v1/dataretrieval/e/{constituents,dailyClose,performance}/v1`,`hsi.com.hk/static/uploads/contents/.../factsheets/{code}.pdf`

乐咕(反爬): `legulegu.com/api/stockdata/index-basic-pe`,`index-basic-pb`,`index-valuation-history`,`industry-pe`,`industry-pe-ttm`,`sw-industry-2021`; py_mini_racer/akshare 解反爬

其他: 新浪列表 `vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData`, 分红 `money.finance.sina.com.cn/corp/go.php/vISSUE_ShareBonus/stockid/{code}.phtml`, 港股K `quotes.sina.cn/hk/api/jsonp_v2.php/.../CN_MarketDataService.getKLineData`; 巨潮 `cninfo.com.cn/new/hisAnnouncement/query`,`static.cninfo.com.cn/`(`pdf_text`); 海外 Yahoo `query1.finance.yahoo.com/v8/finance/chart/{symbol}`, FRED `fred.stlouisfed.org/graph/fredgraph.csv?id={series}`, Stooq `stooq.com/q/d/l/?s=^spx`, 网易 `img1.money.126.net/data/hk/kline/day/his/{code}.json`
