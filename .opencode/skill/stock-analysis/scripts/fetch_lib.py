# -*- coding: utf-8 -*-
"""统一数据抓取库（从项目历史 fetch 脚本提炼）。

覆盖：东方财富（批量行情/日周月K线/F10 财务）、腾讯（行情/复权K线）、
乐咕乐股（指数 PE/PB 估值）、CSIndex 官方指数估值、巨潮公告、产业链现货价、
宏观行业统计、通用工具。

用法：
    from fetch_lib import em_quotes, em_kline, em_f10, tx_kline, tx_quote, save_json
    quotes = em_quotes(['0.000001', '1.600754'], fields='f12,f14,f2,f3,f5,f6,f8,f9,f20,f21,f23,f62')
    kline  = em_kline('1.600754', klt=101, beg='20240101', end='20260813', fqt=1)   # 日K前复权
    fin    = em_f10('RPT_F10_FINANCE_GINCOME', '600754.SH', columns='...')
    bars   = tx_kline('sh600754', period='week', beg='2016-01-01', end='2026-08-13', fqt='qfq')
    quote  = tx_quote('sh600754,sz000001')

字段约定（东方财富行情，f=前缀）：
    f12 代码  f14 名称  f2 现价  f3 涨跌幅  f5 成交量  f6 成交额
    f8 换手率  f9 市盈率TTM  f20 总市值  f21 流通市值  f23 市净率  f62 主力净流入
"""
import json
import os
import time
import requests

H = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://quote.eastmoney.com/'}
EM_QUOTE = 'https://push2delay.eastmoney.com/api/qt/ulist.np/get'
EM_KLINE_HOSTS = ['https://push2his.eastmoney.com',
                  'https://push2delay.eastmoney.com']
EM_KLINE = EM_KLINE_HOSTS[0] + '/api/qt/stock/kline/get'
EM_DATA = 'https://datacenter-web.eastmoney.com/api/data/v1/get'
TX_QUOTE = 'https://qt.gtimg.cn/q='
TX_KLINE = 'https://web.ifzq.gtimg.cn/appstock/app/fqkline/get'
LG_BASE = 'https://legulegu.com/api/stockdata'


def secid(code):
    """裸代码 → 东财 secid：6 开头=沪市(1)，其余=深市(0)。
    注意：指数（如 000300 上证指数）请直接用 normalize_secid('1.000300') 或显式传前缀。"""
    return ('1.' if code.startswith('6') else '0.') + code


def normalize_secid(code_or_secid):
    """接受裸代码或完整 secid，统一为 '市场.代码'。
    '600754' -> '1.600754'；'1.600754' -> '1.600754'；'000001' -> '0.000001'。"""
    s = str(code_or_secid).strip()
    if '.' in s:
        return s
    return secid(s)


def http_get(url, params=None, headers=None, timeout=30, retries=3):
    """带重试的 GET。"""
    for i in range(retries):
        try:
            r = requests.get(url, params=params, headers=headers or H, timeout=timeout)
            r.raise_for_status()
            return r
        except Exception as e:
            if i == retries - 1:
                raise
            time.sleep(1.5 * (i + 1))


def em_quotes(secids, fields='f12,f14,f2,f3,f5,f6,f8,f9,f20,f21,f23,f62'):
    """东财批量行情快照。secids: ['0.000001', '1.600754'] 或裸代码 ['600754']，
    返回 dict[code] -> 行情 dict。"""
    secids = [normalize_secid(s) for s in secids]
    r = http_get(EM_QUOTE, params={'secids': ','.join(secids), 'fields': fields})
    d = r.json()
    out = {}
    for row in (d.get('data') or {}).get('diff') or []:
        out[row['f12']] = row
    return out


def em_kline(symbol, klt=101, beg='20200101', end='20261231', fqt=1,
             lmt=1000000, fields1='f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13'):
    """东财K线。symbol: '600754' 或 '1.600754'；klt: 101日/102周/103月；
    fqt: 0不复权 1前复权 2后复权。
    自动容错：push2his → push2delay → 腾讯K线（返回字段一致）。
    返回 [{date,open,close,high,low,volume,amount,amplitude,pct,chg,turnover}]，
    腾讯回退时 amount/amplitude/chg/turnover 为 None、pct 由收盘价计算。"""
    secid_ = normalize_secid(symbol)
    params = {'secid': secid_, 'klt': klt, 'fqt': fqt, 'beg': beg, 'end': end,
              'lmt': lmt, 'fields1': fields1,
              'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61'}
    last_err = None
    for host in EM_KLINE_HOSTS:
        try:
            r = http_get(host + '/api/qt/stock/kline/get', params=params,
                         timeout=15)
            node = (r.json().get('data') or {}).get('klines') or []
            if node:
                return _parse_em_kline(node)
        except Exception as e:
            last_err = e
    try:
        return _kline_tencent_fallback(secid_, klt, beg, end, fqt)
    except Exception as e:
        last_err = e
    raise IOError('东财/腾讯K线接口均不可用: %s' % last_err)


def _parse_em_kline(node):
    out = []
    for line in node:
        p = line.split(',')
        out.append({'date': p[0], 'open': float(p[1]), 'close': float(p[2]),
                    'high': float(p[3]), 'low': float(p[4]), 'volume': float(p[5]),
                    'amount': float(p[6]), 'amplitude': float(p[7]),
                    'pct': float(p[8]), 'chg': float(p[9]), 'turnover': float(p[10])})
    return out


def _kline_tencent_fallback(secid_, klt, beg, end, fqt):
    """东财K线不可用时转腾讯接口（字段对齐 em_kline）。"""
    mkt, code = secid_.split('.')
    if mkt == '1':
        symbol = 'sh' + code
    elif mkt == '0':
        symbol = 'sz' + code
    elif mkt == '116':
        symbol = 'hk' + code
    else:
        raise ValueError('无法映射腾讯代码: %s' % secid_)
    period = {101: 'day', 102: 'week', 103: 'month'}.get(klt)
    if not period:
        raise ValueError('腾讯回退仅支持 klt 101/102/103，当前 %s' % klt)
    tfqt = {1: 'qfq', 2: 'hfq', 0: ''}[fqt]
    fmt = lambda d: '%s-%s-%s' % (d[:4], d[4:6], d[6:8])
    bars = tx_kline(symbol, period=period, beg=fmt(beg), end=fmt(end),
                    count=800, fqt=tfqt)
    out = []
    prev = None
    for b in bars:
        pct = round((b['close'] / prev - 1) * 100, 2) if prev else None
        out.append({'date': b['date'], 'open': b['open'], 'close': b['close'],
                    'high': b['high'], 'low': b['low'], 'volume': b['volume'],
                    'amount': None, 'amplitude': None, 'pct': pct,
                    'chg': None, 'turnover': None})
        prev = b['close']
    if not out:
        raise IOError('腾讯K线无数据: %s' % symbol)
    return out


def em_f10(report_name, secucode, columns='ALL', pages=6, page_size=50):
    """东财数据中心 F10 财务（分页抓全）。
    常用 report_name：
      RPT_F10_FINANCE_GBALANCE   资产负债表（商誉 GOODWILL / 总资产 / 净资产…）
      RPT_F10_FINANCE_GINCOME    利润表（营收 / 归母净利 / 减值损失…）
      RPT_F10_FINANCE_GCASHFLOW  现金流量表（经营净额 / 折旧摊销…）
      RPT_F10_FINANCE_MAINFINADATA 主要指标（EPS / ROE / 毛利率…）
    返回 [{REPORT_DATE: '2025-12-31 00:00:00', ...}] 按报告期倒序。"""
    out = []
    for p in range(1, pages + 1):
        params = {'reportName': report_name, 'columns': columns,
                  'filter': '(SECUCODE="%s")' % secucode,
                  'pageNumber': p, 'pageSize': page_size,
                  'sortTypes': -1, 'sortColumns': 'REPORT_DATE',
                  'source': 'HSF10', 'client': 'PC'}
        r = http_get(EM_DATA, params=params)
        d = r.json()
        if d.get('result') is None:
            break
        rows = d['result'].get('data') or []
        if not rows:
            break
        out.extend(rows)
        if len(rows) < page_size:
            break
        time.sleep(0.3)
    return out


def tx_quote(symbols):
    """腾讯行情（GBK ~ 分隔字符串）。symbols: 'sh600754,sz000001,…'。
    返回 {symbol: [字段…]}，常用索引：1现价 2昨收 3今开 4成交量 5外盘
    6内盘 30时间 31涨跌 32涨跌% 33最高 34最低 38换手 39PE 43振幅 45流通市值 46总市值 47PB 48涨停 49跌停。"""
    r = http_get(TX_QUOTE + symbols, headers={'User-Agent': 'Mozilla/5.0'})
    r.encoding = 'gbk'
    out = {}
    for line in r.text.strip().split(';'):
        line = line.strip()
        if not line or '=' not in line:
            continue
        sym, payload = line.split('=', 1)
        sym = sym.strip()
        if not sym.startswith('v_'):
            continue
        sym = sym[len('v_'):]
        payload = payload.strip().strip('"')
        if payload[:1].isdigit() and '~' in payload:
            out[sym] = payload.split('~')
    return out


def tx_kline(symbol, period='day', beg='2016-01-01', end='2026-12-31',
             count=800, fqt='qfq'):
    """腾讯复权K线。period: day/week/month；fqt: qfq前复权 hfq后复权 空=不复权。
    返回 [{date, open, close, high, low, volume}]。"""
    params = {'param': '%s,%s,%s,%s,%d,%s' % (symbol, period, beg, end, count, fqt)}
    r = http_get(TX_KLINE, params=params)
    d = r.json()
    node = (d.get('data') or {}).get(symbol) or {}
    key = fqt + period if fqt else period
    rows = node.get(key) or node.get(period) or []
    out = []
    for row in rows:
        if len(row) < 6:
            continue
        out.append({'date': row[0], 'open': float(row[1]), 'close': float(row[2]),
                    'high': float(row[3]), 'low': float(row[4]), 'volume': float(row[5])})
    return out


def lg_index_pe(ts_code, retries=3):
    """乐咕乐股指数 PE-TTM 序列。ts_code: '000300' 等（沪深300）。
    依赖 Session 先取 cookie（可能需 py_mini_racer 解 JS 挑战，见 reference/data-sources.md）。
    返回 [{trade_date, pe, pb}]。"""
    s = requests.Session()
    s.headers.update({'User-Agent': 'Mozilla/5.0',
                      'X-Requested-With': 'XMLHttpRequest',
                      'Referer': 'https://legulegu.com/'})
    for i in range(retries):
        try:
            s.get('https://legulegu.com/', timeout=15)
            r = s.get(LG_BASE + '/index-basic-pe',
                      params={'ts': int(time.time() * 1000), 'stockCode': ts_code,
                              'lang': 'zh-CN'}, timeout=20)
            d = r.json()
            return d.get('data') or d
        except Exception as e:
            if i == retries - 1:
                raise
            time.sleep(2)


def save_json(obj, path, ttl_hours=None, scope=None, source=None):
    """保存 JSON，自动注入缓存元数据 _meta（fetched_at/ttl_hours/scope/source）。

    幂等：同一 path 重复保存即覆盖，不产生堆积。ttl_hours 供 cache_status.py 判断新鲜度。
    已有 dict 且带 _meta 时不覆盖原 _meta（保留最早抓取时间）。
    """
    import datetime
    os.makedirs(os.path.dirname(os.path.abspath(path)) or '.', exist_ok=True)
    if isinstance(obj, dict) and '_meta' not in obj:
        obj = dict(obj)
        obj['_meta'] = {
            'fetched_at': datetime.datetime.now().isoformat(timespec='seconds'),
            'ttl_hours': ttl_hours,
            'scope': scope,
            'source': source,
        }
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False)
    print('saved:', path)


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


# ==================== 新增数据源（2026-08） ====================

CNINFO_QUERY = 'http://www.cninfo.com.cn/new/hisAnnouncement/query'
CNINFO_STOCKS = 'http://www.cninfo.com.cn/new/data/szse_stock.json'
_CNINFO_ORG = {}


def _cninfo_orgids(stock):
    """'600754' → '600754,gssh0600754'（巨潮接口要求 code,orgId）。缺 orgId 时退回裸代码。"""
    out = []
    for code in [c.strip() for c in stock.split(',') if c.strip()]:
        if code in _CNINFO_ORG:
            out.append('%s,%s' % (code, _CNINFO_ORG[code]))
            continue
        try:
            r = http_get(CNINFO_STOCKS, timeout=20)
            for it in (r.json().get('stockList') or []):
                _CNINFO_ORG[it.get('code', '')] = it.get('orgId', '')
        except Exception:
            pass
        org = _CNINFO_ORG.get(code, '')
        out.append('%s,%s' % (code, org) if org else code)
    return ';'.join(out)


def cninfo_notices(stock, searchkey='', category='', pages=3, page_size=30):
    """巨潮公告列表（一手公告源：商誉/减持/业绩预告类报告必用）。

    stock: '600754' 或 '600754,000001'（自动解析 orgId）；searchkey: 关键词（如 '商誉'/'减持'）；
    category: 'category_ndbg_szsh'（年报）等，留空=全部。
    返回 [{announcementTitle, adjunctUrl(相对), announcementTime(秒), secName…}]。
    PDF 全文：static.cninfo.com.cn/ + adjunctUrl，用 pdf_text() 提取。
    """
    out = []
    stock_param = _cninfo_orgids(stock)
    for p in range(1, pages + 1):
        data = {'pageNum': p, 'pageSize': page_size, 'column': 'szse',
                'tabName': 'fulltext', 'stock': stock_param, 'searchkey': searchkey,
                'category': category, 'seDate': '', 'isHLtitle': 'true'}
        try:
            rr = requests.post(CNINFO_QUERY, data=data,
                               headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
            rr.raise_for_status()
            d = rr.json()
        except Exception:
            break
        rows = (d.get('announcements') or [])
        if not rows:
            break
        out.extend(rows)
        if len(rows) < page_size:
            break
        time.sleep(0.3)
    for row in out:
        ts = row.get('announcementTime')
        if isinstance(ts, (int, float)):
            if ts > 1e11:
                ts = ts / 1000.0
            try:
                row['announcementDate'] = time.strftime('%Y-%m-%d', time.localtime(ts))
            except (OSError, ValueError, OverflowError):
                row['announcementDate'] = ''
    return out


SPOT_CODE_CN = {
    '生猪': 'LH', '鸡蛋': 'JD', '玉米': 'C', '淀粉': 'CS', '豆一': 'A', '豆二': 'B',
    '豆粕': 'M', '豆油': 'Y', '棕榈油': 'P', '菜油': 'OI', '菜粕': 'RM', '白糖': 'SR',
    '棉花': 'CF', '苹果': 'AP', '红枣': 'CJ', '花生': 'PK',
    '螺纹钢': 'RB', '热卷': 'HC', '铁矿石': 'I', '焦煤': 'JM', '焦炭': 'J',
    '玻璃': 'FG', '纯碱': 'SA', '硅铁': 'SF', '锰硅': 'SM', '不锈钢': 'SS', '线材': 'WR',
    '铜': 'CU', '铝': 'AL', '锌': 'ZN', '铅': 'PB', '镍': 'NI', '锡': 'SN', '氧化铝': 'AO',
    '黄金': 'AU', '白银': 'AG', '原油': 'SC', '燃料油': 'FU', '沥青': 'BU', '橡胶': 'RU',
    '纸浆': 'SP', 'LPG': 'PG', '液化石油气': 'PG', '塑料': 'L', 'PVC': 'V', 'PP': 'PP',
    '乙二醇': 'EG', '苯乙烯': 'EB', '甲醇': 'MA', 'PTA': 'TA', '短纤': 'PF',
    '尿素': 'UR', '烧碱': 'SH',
}


def spot_price(keyword):
    """产业链现货价格（周期股核心证据：现货 vs 期货近月/主力）。

    keyword: 中文名（如 '生猪'/'螺纹钢'，经 SPOT_CODE_CN 映射为期货代码）或直接期货代码（'LH'）。
    降级链：akshare futures_spot_price 现表 → futures_spot_price_daily 历史 → None（报告标注降级）。
    返回 {'via': 接口, 'row': 现货行, 'columns': [...]} 或 {'via':…, 'rows': 历史}。
    """
    try:
        import akshare as ak
    except ImportError:
        return None
    code = SPOT_CODE_CN.get(keyword, keyword if keyword.isascii() and keyword.isupper() else None)
    try:
        df = ak.futures_spot_price()
        sub = df[df['symbol'].str.upper() == code] if code is not None else df[df.apply(
            lambda r: keyword in str(r.values), axis=1)]
        if sub is not None and len(sub):
            return {'via': 'akshare.futures_spot_price',
                    'row': sub.iloc[0].to_dict(),
                    'all_symbols': df['symbol'].tolist(),
                    'columns': list(df.columns)}
    except Exception:
        pass
    if code:
        try:
            df = ak.futures_spot_price_daily(symbol=code)
            if df is not None and len(df):
                return {'via': 'akshare.futures_spot_price_daily',
                        'rows': df.to_dict(orient='records'),
                        'columns': list(df.columns)}
        except Exception:
            pass
    return None


MACRO_FUNCS = {
    'cpi': 'macro_china_cpi',
    'ppi': 'macro_china_ppi',
    'pmi': 'macro_china_pmi',
    '社会消费品零售': 'macro_china_shrzgm',
    '固定资产投资': 'macro_china_gdzctz',
    'lpr': 'macro_china_lpr',
}


def macro_industry(indicator):
    """宏观/行业统计（统计局口径，行业分析章用）。

    indicator: MACRO_FUNCS 键之一（cpi/ppi/pmi/社会消费品零售/固定资产投资/lpr）。
    返回 {'via': 接口名, 'rows': [...]} 或 None（失败→报告标注降级）。
    """
    try:
        import akshare as ak
    except ImportError:
        return None
    fn_name = MACRO_FUNCS.get(indicator, 'macro_china_%s' % indicator)
    fn = getattr(ak, fn_name, None)
    if fn is None:
        return None
    try:
        df = fn()
        if df is not None and len(df):
            return {'via': 'akshare.' + fn_name,
                    'rows': df.to_dict(orient='records'),
                    'columns': list(df.columns)}
    except Exception:
        return None
    return None


def pdf_text(path, keyword=None):
    """公告/研报 PDF → 文本（pypdf）。keyword 过滤仅返回含关键词的页（商誉/减持数字提取用）。

    返回 [{'page': n, 'text': ...}]；解析失败返回 []。
    """
    try:
        from pypdf import PdfReader
    except ImportError:
        return []
    try:
        reader = PdfReader(path)
        out = []
        for i, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or '')
            if keyword is None or keyword in text:
                out.append({'page': i, 'text': text})
        return out
    except Exception:
        return []


def cache_meta_table(paths):
    """汇总一批缓存文件的 _meta → 附录'数据截止时间表'行。

    返回 [[文件, 抓取时间, TTL(h), scope, source], ...]（按 fetched_at 升序）。
    """
    import json as _json
    rows = []
    for p in paths or []:
        try:
            with open(p, 'r', encoding='utf-8') as f:
                obj = _json.load(f)
            meta = obj.get('_meta') or {}
        except Exception:
            continue
        rows.append([os.path.basename(p), meta.get('fetched_at', ''),
                     str(meta.get('ttl_hours', '')), meta.get('scope', ''),
                     meta.get('source', '')])
    rows.sort(key=lambda r: r[1])
    return rows
