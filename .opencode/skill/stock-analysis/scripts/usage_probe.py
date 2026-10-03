# -*- coding: utf-8 -*-
"""业界使用证据：抽样券商深度研报 PDF，统计方法关键词命中率。

用法：
    python scripts/usage_probe.py [--count 20] [--page-min 15] [--offline]

输入：reference/signals/method_signals_latest.json 的 research_reports 缓存
输出：reference/signals/usage_evidence_{YYYYMM}.json
      {方法关键词: {hits, total, rate, samples: [{org, title}]}}

规则：
    - 只抽样页数 ≥ page-min 的深度报告（默认 15 页）
    - 按最新日期优先取 count 份（默认 20）；PDF 下载失败跳过
    - 关键词命中率 rate = hits/total；样本 <10 份时降级警告（证据弱）
    - 报告 QA 引用：方法命中率 ≥30% 视为"业界常用"；<10% 且无权威源 → 标注"非常规方法"
"""
import collections
import datetime
import json
import os
import re
import sys
import time

import requests
from pypdf import PdfReader

H = {'User-Agent': 'Mozilla/5.0'}
HERE = os.path.dirname(os.path.abspath(__file__))
SIG_DIR = os.path.join(os.path.dirname(HERE), 'reference', 'signals')
PDF_URL = 'https://pdf.dfcfw.com/pdf/H3_{info}_1.pdf'
MAX_RETRIES = 1
SLEEP = 0.3

KEYWORDS = {
    'pe_quantile': ['PE 分位', 'PE分位', '估值分位'],
    'relative': ['可比公司', '同行', '横向对比'],
    'ev_ebitda': ['EV/EBITDA', 'EV/EBIT'],
    'sotp': ['SOTP', '分部估值'],
    'dcf': ['DCF', '现金流贴现', '自由现金流', 'WACC'],
    'ddm': ['DDM', '股利贴现', '股息贴现'],
    'cap_rate': ['资本化率', 'cap rate', '租售比'],
    'cycle_mean': ['周期平均', '正常化盈利'],
    'replacement': ['重置成本'],
    'price_index': ['价格指数', '成交价'],
    'nvt': ['NVT', 'MVRV', '链上'],
    'dividend': ['股息率', '分红'],
    'scenario': ['情景分析', '敏感性分析'],
    'riskfree': ['无风险利率', '国债收益率'],
}


def get_signals():
    path = os.path.join(SIG_DIR, 'method_signals_latest.json')
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def pick_reports(signals, count, page_min):
    reps = (signals.get('research_reports') or {}).get('data') or []
    deep = [r for r in reps if (r.get('pages') or 0) >= page_min]
    deep.sort(key=lambda r: r.get('date') or '', reverse=True)
    return deep[:count]


def download_pdf(info_code):
    url = PDF_URL.format(info=info_code)
    r = requests.get(url, headers=H, timeout=30)
    r.raise_for_status()
    return r.content


def extract_text(pdf_bytes):
    try:
        reader = PdfReader(io_bytes(pdf_bytes))
        parts = []
        for page in reader.pages[:10]:
            t = page.extract_text() or ''
            parts.append(t)
        return ' '.join(parts)
    except Exception:
        return ''


def io_bytes(b):
    import io
    return io.BytesIO(b)


def main():
    offline = '--offline' in sys.argv
    count = 20
    page_min = 8
    if '--count' in sys.argv:
        count = int(sys.argv[sys.argv.index('--count') + 1])
    if '--page-min' in sys.argv:
        page_min = int(sys.argv[sys.argv.index('--page-min') + 1])
    if offline:
        print('OFFLINE：跳过下载，仅输出关键词定义')
        for k, kws in KEYWORDS.items():
            print('  %-14s %s' % (k, '/'.join(kws)))
        return 0

    signals = get_signals()
    reps = pick_reports(signals, count, page_min)
    print('抽样研报 %d 份（页数≥%d，按最新）' % (len(reps), page_min))
    if len(reps) < 10:
        print('WARN: 样本 %d 份 <10，证据偏弱（检查 signals 缓存是否过期）' % len(reps))

    stats = collections.defaultdict(list)
    ok = 0
    for i, rep in enumerate(reps):
        info = rep.get('infoCode')
        if not info:
            continue
        try:
            pdf = download_pdf(info)
            text = extract_text(pdf)
            if len(text) < 200:
                raise IOError('PDF 文本过短')
            ok += 1
            for k, kws in KEYWORDS.items():
                for kw in kws:
                    if kw.lower() in text.lower():
                        stats[k].append({'org': rep.get('org'), 'title': rep.get('title')})
                        break
        except Exception as e:
            print('  跳过 %s: %s' % (rep.get('title'), e))
        time.sleep(SLEEP)
    print('成功解析 %d/%d 份' % (ok, len(reps)))

    evidence = {
        '_meta': {'fetched_at': datetime.datetime.now().isoformat(timespec='seconds'),
                  'ttl_hours': 720, 'scope': 'usage-evidence', 'source': 'em-research-pdf'},
        'count': len(reps), 'parsed': ok,
        'page_min': page_min,
        'methods': {},
    }
    for k, samples in sorted(stats.items()):
        rate = len(samples) / ok if ok else 0
        evidence['methods'][k] = {
            'hits': len(samples), 'total': ok, 'rate': round(rate, 3),
            'samples': samples[:3],
        }
        tag = '常用' if rate >= 0.30 else ('少见' if rate >= 0.10 else '罕见')
        print('  %-14s 命中 %d/%d (%.0f%%) [%s]' % (k, len(samples), ok, rate * 100, tag))
    for k in KEYWORDS:
        if k not in evidence['methods']:
            evidence['methods'][k] = {'hits': 0, 'total': ok, 'rate': 0.0, 'samples': []}

    os.makedirs(SIG_DIR, exist_ok=True)
    path = os.path.join(SIG_DIR, 'usage_evidence_%s.json' % datetime.date.today().strftime('%Y%m'))
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(evidence, f, ensure_ascii=False, indent=1)
    print('saved:', path)
    return 0


if __name__ == '__main__':
    sys.exit(main())
