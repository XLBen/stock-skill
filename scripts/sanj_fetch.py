# -*- coding: utf-8 -*-
"""华润三九 000999 2026Q1/H1 财报对比数据抓取脚本。"""
import os
import sys
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_lib import em_f10, http_get, save_json

CODE = '000999.SZ'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
os.makedirs(OUT, exist_ok=True)

def main():
    reports = {
        'gincome': 'RPT_F10_FINANCE_GINCOME',
        'gbalance': 'RPT_F10_FINANCE_GBALANCE',
        'gcashflow': 'RPT_F10_FINANCE_GCASHFLOW',
        'mainfin': 'RPT_F10_FINANCE_MAINFINADATA',
    }
    for key, rn in reports.items():
        rows = em_f10(rn, CODE, columns='ALL', pages=12, page_size=50)
        save_json(rows, os.path.join(OUT, 'sanj_%s.json' % key),
                  ttl_hours=24, scope='000999-2026q1h1', source='eastmoney-datacenter')
        print(key, 'rows:', len(rows))
        time.sleep(0.3)

    # 股东户数（东财 datacenter RPT_HOLDERNUM）
    try:
        params = {'reportName': 'RPT_HOLDERNUM', 'columns': 'ALL',
                  'filter': '(SECURITY_CODE="000999")',
                  'pageNumber': 1, 'pageSize': 50,
                  'sortTypes': -1, 'sortColumns': 'END_DATE',
                  'source': 'WEB', 'client': 'WEB'}
        r = http_get('https://datacenter-web.eastmoney.com/api/data/v1/get', params=params)
        d = r.json()
        rows = (d.get('result') or {}).get('data') or []
        save_json(rows, os.path.join(OUT, 'sanj_holdernum.json'),
                  ttl_hours=24, scope='000999-holdernum', source='eastmoney-datacenter')
        print('holdernum rows:', len(rows))
    except Exception as e:
        print('holdernum failed:', e)

if __name__ == '__main__':
    main()
