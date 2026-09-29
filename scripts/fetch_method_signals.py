# -*- coding: utf-8 -*-
"""方法新鲜度信号抓取：Damodaran 估值参数锚 + 券商研报元数据 + 关键词讨论度。

用法：
    python scripts/fetch_method_signals.py

输出（reference/library/ 同级 signals 目录）：
    reference/signals/method_signals_{YYYYMM}.json   月度信号快照
    reference/signals/method_signals_latest.json     最新快照（QA/cache_status 读取）

内容：
    1. damodaran：无风险利率/ERP/行业倍数（datacurrent.html，每年 1 月更新）——DCF 类资产的参数锚
    2. research_reports：东财研报中心近 3 个月研报元数据（title/org/pages/date/infoCode），供 usage_probe 取证
    3. keyword_hits：东财资讯搜索关键词 hitsTotal（业界讨论度信号）

容错：任一源失败仅记录 error 字段，不中断；限速 sleep 0.3，失败重试 1 次。
"""
import datetime
import json
import os
import re
import sys
import time
import urllib.parse

import requests

H = {'User-Agent': 'Mozilla/5.0'}
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(os.path.dirname(HERE), 'reference', 'signals')

DAMODARAN_URL = 'https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datacurrent.html'
DAMODARAN_HISTIMPL = 'https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/histimpl.html'
DAMODARAN_CTRYPREM = 'https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/ctryprem.html'
RESEARCH_API = 'https://reportapi.eastmoney.com/report/list'
SEARCH_API = 'https://search-api-web.eastmoney.com/search/jsonp'

KEYWORDS = ['DCF', 'SOTP', '自由现金流贴现', '股息率', '网格交易', '红利低波',
            '资本化率', '重置成本', 'PE百分位', '情景分析']
REPORT_MONTHS = 3
REPORT_PAGES = 6


def get(url, params=None, timeout=25):
    r = requests.get(url, params=params, headers=H, timeout=timeout)
    r.raise_for_status()
    return r


def fetch_damodaran():
    """Damodaran 估值参数锚：
    - datacurrent.html → 数据更新日期
    - histimpl.html   → 美国隐含 ERP（Implied ERP FCFE）与 10 年国债利率（最新年份）
    - ctryprem.html   → 美国/中国国家风险溢价（容错，找不到置 None）
    """
    out = {}
    t = get(DAMODARAN_URL).text
    m = re.search(r'most recent update was on\s+([A-Za-z0-9 ,]+)', t)
    if not m:
        m = re.search(r'last full update:\s*(?:<[^>]+>)*([A-Za-z0-9 ,]+)', t)
    out['data_date'] = m.group(1) if m else None

    # 隐含 ERP：取表格最新年份行（最后一行的 Implied ERP 列）
    out['implied_erp'] = None
    out['us10y_tbond'] = None
    try:
        t2 = get(DAMODARAN_HISTIMPL).text
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', t2, re.S)
        year_rows = []
        for r in rows:
            cells = [re.sub(r'<[^>]+>', '', c).strip() for c in re.findall(r'<td[^>]*>(.*?)</td>', r, re.S)]
            if len(cells) >= 8 and re.match(r'^\d{4}$', cells[0]):
                year_rows.append(cells)
        if year_rows:
            last = year_rows[-1]
            out['implied_erp_year'] = last[0]
            out['implied_erp'] = last[-1] or None
            m = re.search(r'([\d.]+)%', last[5] or '')
            out['us10y_tbond'] = m.group(1) if m else None
    except Exception as e:
        out['histimpl_error'] = str(e)

    # 国家风险溢价（China / US）
    out['china_erp'] = None
    try:
        t3 = get(DAMODARAN_CTRYPREM).text
        plain = re.sub(r'<[^>]+>', ' ', t3)
        plain = re.sub(r'\s+', ' ', plain)
        for name, key in (('China', 'china_erp'), ('United States', 'us_erp')):
            m = re.search(name + r'[^.]*?([\d.]+)%', plain)
            if m:
                out[key] = m.group(1)
    except Exception as e:
        out['ctryprem_error'] = str(e)
    return out


def fetch_research_reports():
    """东财研报中心近 N 个月列表（每页 50，取 6 页=300 条元数据）。"""
    now = datetime.date.today()
    beg = (now - datetime.timedelta(days=30 * REPORT_MONTHS)).isoformat()
    rows = []
    for page in range(1, REPORT_PAGES + 1):
        params = {'industryCode': '*', 'pageSize': 50, 'pageNo': page,
                  'beginTime': beg, 'endTime': now.isoformat(),
                  'qType': 0, 'code': '*', 'p': page, 'pageNumber': page}
        d = get(RESEARCH_API, params=params).json()
        data = d.get('data') or []
        for it in data:
            rows.append({
                'title': it.get('title'),
                'org': it.get('orgName'),
                'pages': it.get('attachPages'),
                'date': (it.get('publishDate') or '')[:10],
                'infoCode': it.get('infoCode'),
                'column': it.get('column'),
            })
        if len(data) < 50:
            break
        time.sleep(0.3)
    return rows


def fetch_keyword_hits():
    out = {}
    for kw in KEYWORDS:
        try:
            param = {
                'uid': '', 'keyword': kw, 'type': ['cmsArticleWebOld'],
                'client': 'web', 'clientType': 'web', 'clientVersion': 'curr',
                'param': {'cmsArticleWebOld': {'searchScope': 'default', 'sort': 'default',
                                               'pageIndex': 1, 'pageSize': 1,
                                               'preTag': '', 'postTag': ''}},
            }
            r = get(SEARCH_API, params={'cb': 'cb', 'param': json.dumps(param, ensure_ascii=False)})
            m = re.search(r'\{.*\}', r.text, re.S)
            if m:
                d = json.loads(m.group(0))
                out[kw] = d.get('hitsTotal')
            else:
                out[kw] = None
            time.sleep(0.3)
        except Exception as e:
            out[kw] = 'ERR:%s' % e
    return out


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    now = datetime.datetime.now()
    sig = {'fetched_at': now.isoformat(timespec='seconds'),
           'ttl_hours': 720, 'scope': 'methods-signals', 'source': 'multi'}

    sections = {}
    for name, fn in (('damodaran', fetch_damodaran),
                     ('research_reports', fetch_research_reports),
                     ('keyword_hits', fetch_keyword_hits)):
        try:
            sections[name] = {'ok': True, 'data': fn()}
        except Exception as e:
            sections[name] = {'ok': False, 'error': str(e)}
        print('%s: %s' % (name, 'OK' if sections[name]['ok'] else sections[name]['error']))
        time.sleep(0.3)

    sig.update(sections)
    path = os.path.join(OUT_DIR, 'method_signals_%s.json' % now.strftime('%Y%m'))
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(sig, f, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT_DIR, 'method_signals_latest.json'), 'w', encoding='utf-8') as f:
        json.dump(sig, f, ensure_ascii=False, indent=1)
    print('saved:', path)
    return 0


if __name__ == '__main__':
    sys.exit(main())
