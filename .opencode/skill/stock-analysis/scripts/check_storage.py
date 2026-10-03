# -*- coding: utf-8 -*-
"""防堆积检查：扫描同名/同内容重复数据文件（JSON/PNG/CSV），报告重复项。

用法：
    python scripts/check_storage.py [--max-mb 10] [--min-dup 2]
    --max-mb 仅对比 ≤N MB 的文件（默认 10MB，避免大文件哈希耗时）
    退出码：有重复项返回 1，无重复返回 0。

原则：AI 抓取脚本必须幂等（同一任务固定文件名覆盖写）；
发现重复 → 保留主题目录主份，其余由用户确认后删除（本脚本只报告不删除）。
"""
import collections
import hashlib
import os
import sys

EXT = ('.json', '.png', '.csv', '.xlsx')


def find_project_root():
    d = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    while True:
        parent = os.path.dirname(d)
        if parent == d:
            return d
        if os.path.isdir(os.path.join(d, '暂存区')) and os.path.isdir(os.path.join(d, '分类区')):
            return d
        d = parent


def main():
    root = find_project_root()
    max_mb = 10
    if '--max-mb' in sys.argv:
        max_mb = int(sys.argv[sys.argv.index('--max-mb') + 1])
    by_name = collections.defaultdict(list)
    by_hash = collections.defaultdict(list)
    total = 0
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ('.opencode', 'node_modules', '__pycache__')]
        for fn in files:
            if not fn.lower().endswith(EXT):
                continue
            full = os.path.join(base, fn)
            total += 1
            by_name[fn.lower()].append(full)
            try:
                size = os.path.getsize(full)
                if size > max_mb * 1024 * 1024:
                    continue
                h = hashlib.md5()
                with open(full, 'rb') as f:
                    for chunk in iter(lambda: f.read(1 << 20), b''):
                        h.update(chunk)
                by_hash[h.hexdigest()].append(full)
            except OSError:
                pass

    dup_names = {k: v for k, v in by_name.items() if len(v) > 1}
    dup_hashes = {k: v for k, v in by_hash.items() if len(v) > 1}
    print('== 扫描 %d 个数据文件：同名组 %d，同内容组 %d ==' % (total, len(dup_names), len(dup_hashes)))
    for k, v in sorted(dup_names.items()):
        print('  同名: %s (%d 处)' % (k, len(v)))
        for p in v:
            print('        %s' % os.path.relpath(p, root))
    for k, v in sorted(dup_hashes.items()):
        print('  同内容 %d bytes x%d:' % (os.path.getsize(v[0]), len(v)))
        for p in v:
            print('        %s' % os.path.relpath(p, root))
    return 1 if (dup_names or dup_hashes) else 0


if __name__ == '__main__':
    sys.exit(main())
