# -*- coding: utf-8 -*-
"""缓存新鲜度检查：扫描项目内带 _meta 的 JSON/CSV 缓存，按 TTL 判定 fresh/stale。

用法：
    python scripts/cache_status.py [--strict] [--root 项目根]
    --strict  存在 stale 或缺失 meta 的缓存时退出码 1（QA 用）

判定规则：
    - _meta.fetched_at + _meta.ttl_hours 未过期 → fresh
    - 已过期 → stale（报告若使用必须标注"数据截止日期"）
    - 有 _meta 无 ttl_hours → 按文件名关键词猜测 TTL（kline=24h, f10=168h, signals=720h, damodaran=2160h…）
    - 无 _meta → no-meta（视为未知，提示重抓）

TTL 参照 reference/library/sources.json 的 ttl_hours 字段。
"""
import datetime
import json
import os
import re
import sys

EXT = ('.json', '.csv')
TTL_BY_KEYWORD = [
    (re.compile(r'quote', re.I), 2),
    (re.compile(r'kline|hist|daily|bar', re.I), 24),
    (re.compile(r'f10|finance|balance|income|cashflow|main', re.I), 168),
    (re.compile(r'research|report', re.I), 720),
    (re.compile(r'damodaran|erp|rf_', re.I), 2160),
    (re.compile(r'signal', re.I), 720),
    (re.compile(r'index', re.I), 24),
]


def find_project_root():
    """自 scripts/ 向上找含 .opencode/ 的祖先；找不到返回 None。"""
    d = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    while True:
        if os.path.isdir(os.path.join(d, '.opencode')):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def guess_ttl(filename):
    for pat, ttl in TTL_BY_KEYWORD:
        if pat.search(filename):
            return ttl
    return None


def check_file(path, now):
    name = os.path.basename(path)
    meta = None
    if name.lower().endswith('.json'):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict):
                meta = data.get('_meta')
        except Exception:
            return 'broken'
    if not meta:
        return 'no-meta'
    try:
        fetched = datetime.datetime.fromisoformat(meta['fetched_at'])
    except (KeyError, TypeError, ValueError):
        return 'bad-meta'
    ttl = meta.get('ttl_hours') or guess_ttl(name) or 720
    age = (now - fetched).total_seconds() / 3600
    return 'fresh' if age <= ttl else 'stale(%dh>%.0fh)' % (ttl, age)


def main():
    root = sys.argv[sys.argv.index('--root') + 1] if '--root' in sys.argv else find_project_root()
    if not root or not os.path.isdir(root):
        print('FAIL: 找不到项目根目录（--root 指定或项目含 .opencode/）')
        return 1
    strict = '--strict' in sys.argv
    now = datetime.datetime.now()
    counts = {}
    stale = []
    no_meta = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ('.opencode', 'node_modules', '__pycache__')]
        for fn in files:
            if fn.lower().endswith(EXT):
                full = os.path.join(base, fn)
                st = check_file(full, now)
                counts[st] = counts.get(st, 0) + 1
                if st.startswith('stale'):
                    stale.append(os.path.relpath(full, root))
                elif st == 'no-meta':
                    no_meta.append(os.path.relpath(full, root))
    print('== 缓存状态: %s ==' % counts)
    for p in stale[:20]:
        print('  STALE:', p)
    if len(stale) > 20:
        print('  … 共 %d 个 stale' % len(stale))
    for p in no_meta[:10]:
        print('  NO-META:', p)
    if len(no_meta) > 10:
        print('  … 共 %d 个无元数据（历史缓存，视为未知需重抓）' % len(no_meta))
    if strict and (stale or no_meta):
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
