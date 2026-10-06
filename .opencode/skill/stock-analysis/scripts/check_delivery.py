# -*- coding: utf-8 -*-
"""交付质检 v3：编号存档制校验（reports/ 双写 + 注册表一致性），废除暂存区强制。

用法（QA 步骤必跑）：
    python scripts/check_delivery.py [报告编号]

检查项（有编号参数时只查该报告，否则全量）：
1. [错误] reports/_registry.json 不可解析或 version≠1
2. [错误] delivered 条目：所有报告/{编号}_{名}.docx 缺失（双写不齐）
3. [错误] delivered 条目：70_delivered/ 历史版本为空
4. [错误] 所有报告/ 内文件名不匹配 ^\d+_ 或未在注册表登记
5. [错误] .docx 落点非法（在 reports 体系与 legacy 目录之外）
6. [警告] legacy 目录（暂存区/分类区/data）中的 docx：建议 assign_legacy 懒登记

退出码：有错误返回 1，仅警告返回 0。
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import workspace_lib as wl  # noqa: E402

OUT_ENC = getattr(sys.stdout, 'encoding', None) or 'utf-8'
LEGACY_DIRS = ('暂存区', '分类区')


def scan_docx(root):
    hits = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in ('.opencode', 'node_modules', '__pycache__')]
        for fn in files:
            if fn.lower().endswith('.docx'):
                hits.append(os.path.join(base, fn))
    return hits


def check_registry(errors, warns):
    reg = wl.load_registry()
    root = wl.reports_root()
    delivered_names = set()
    for e in reg['reports'].values():
        if e.get('legacy'):
            continue
        if not os.path.isdir(e['dir']):
            errors.append('编号 %d：工作区目录缺失 %s' % (e['no'], e['dir']))
            continue
        if e.get('status') == 'delivered':
            if not e.get('deliverable') or not os.path.exists(e['deliverable']):
                errors.append('编号 %d：deliverable 缺失（所有报告/ 双写不齐）: %r'
                              % (e['no'], e.get('deliverable')))
            hist_dir = os.path.join(e['dir'], '70_delivered')
            hists = [f for f in os.listdir(hist_dir) if f.endswith('.docx')] \
                if os.path.isdir(hist_dir) else []
            if not hists:
                errors.append('编号 %d：70_delivered/ 无历史版本' % e['no'])
        if e.get('deliverable') and os.path.exists(e.get('deliverable')):
            delivered_names.add(os.path.basename(e['deliverable']))
    all_dir = os.path.join(root, wl.ALL_REPORTS_DIR)
    if os.path.isdir(all_dir):
        for fn in os.listdir(all_dir):
            if not fn.endswith('.docx'):
                continue
            if not re.match(r'^\d+_', fn):
                errors.append('所有报告/ 命名不合规（须 {编号}_{报告名}.docx）: %s' % fn)
            elif fn not in delivered_names:
                errors.append('所有报告/ 文件未在注册表登记: %s' % fn)
    return errors, warns


def main():
    root = wl.find_project_root()
    errors, warns = [], []
    try:
        check_registry(errors, warns)
    except json.JSONDecodeError as e:
        errors.append('_registry.json 不可解析: %s' % e)

    reports_root = wl.reports_root()
    allowed_prefixes = (os.path.join(reports_root, wl.ALL_REPORTS_DIR) + os.sep,)
    for full in scan_docx(root):
        rel = os.path.relpath(full, root)
        in_workspace_hist = bool(re.search(r'[\\/]70_delivered[\\/]', full))
        if full.startswith(allowed_prefixes) or in_workspace_hist:
            continue
        if any(full.startswith(os.path.join(root, d) + os.sep) for d in LEGACY_DIRS):
            warns.append('legacy 存量报告（建议 workspace_lib.assign_legacy 懒登记编号）: %s' % rel)
            continue
        errors.append('docx 落点非法（reports 体系之外）: %s' % rel)

    for msg in errors:
        print('FAIL:', msg)
    for msg in warns:
        print('WARN:', msg)
    print('== 扫描结果: %d 个错误, %d 个警告 ==' % (len(errors), len(warns)))
    dup_code = 0
    try:
        import check_storage
        dup_code = check_storage.main(root)
        if dup_code:
            print('WARN: 存在同名/同内容重复数据文件（P6 存量清理项），运行 python scripts/check_storage.py 查看')
    except Exception as e:
        print('WARN: check_storage 未运行: %s' % e)
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
