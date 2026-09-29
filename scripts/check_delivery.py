# -*- coding: utf-8 -*-
"""交付质检：扫描全项目，校验报告落点与命名。

用法（QA 步骤必跑）：
    python scripts/check_delivery.py

检查项：
1. [错误] 任何 .docx 位于 暂存区/ 与 分类区/ 之外（排除 .opencode、node_modules、__pycache__）
2. [错误] 暂存区/ 内文件名不以 _YYYYMMDD.docx 结尾（特殊文档如 手册/科普 需带日期）
3. [警告] 分类区/ 内文件名不含日期
4. [警告] 数据文件重复（并入 check_storage.py：同名/同内容堆积，P6 存量清理项）

退出码：有错误返回 1，仅警告返回 0。
"""
import os
import re
import sys

OUT_ENC = getattr(sys.stdout, 'encoding', None) or 'utf-8'

MARKERS = ('暂存区', '分类区')


def find_project_root():
    d = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    while True:
        parent = os.path.dirname(d)
        if parent == d:
            return None
        if all(os.path.isdir(os.path.join(d, m)) for m in MARKERS):
            return d
        d = parent


def scan_docx(root):
    hits = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in ('.opencode', 'node_modules', '__pycache__')]
        for fn in files:
            if fn.lower().endswith('.docx'):
                hits.append(os.path.join(base, fn))
    return hits


def main():
    root = find_project_root()
    if not root:
        print('FAIL: 找不到项目根目录（需同时含 暂存区/ 与 分类区/）')
        return 1
    stage = os.path.join(root, '暂存区')
    arch = os.path.join(root, '分类区')
    errors, warns = [], []
    docs = scan_docx(root)

    for full in docs:
        rel = os.path.relpath(full, root)
        name = os.path.basename(full)
        if full.startswith(stage + os.sep):
            if not re.search(r'_\d{8}\.docx$', name):
                errors.append('命名不合规（暂存区需 _YYYYMMDD.docx 结尾）: %s' % rel)
        elif full.startswith(arch + os.sep):
            if not re.search(r'\d{8}', name):
                warns.append('归档文件无日期: %s' % rel)
        else:
            errors.append('报告落点在暂存区/分类区之外: %s' % rel)

    for msg in errors:
        print('FAIL:', msg)
    for msg in warns:
        print('WARN:', msg)
    print('== 扫描结果: %d 个错误, %d 个警告, 共 %d 份 docx =='
          % (len(errors), len(warns), len(docs)))
    dup_code = 0
    try:
        import check_storage
        dup_code = check_storage.main()
        if dup_code:
            print('WARN: 存在同名/同内容重复数据文件（P6 存量清理项），运行 python scripts/check_storage.py 查看')
    except Exception as e:
        print('WARN: check_storage 未运行: %s' % e)
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
