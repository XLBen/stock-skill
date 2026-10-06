# -*- coding: utf-8 -*-
"""报告工作区与编号账本（workspace_lib）——v3.0 文件系统基座。

目录约定（项目根/reports/，替代旧 暂存区/分类区 交付机制）：

    reports/
      _registry.json              编号账本 {"version", "next", "reports": {"7": {...}}}
      7_中药行业/                  一报告一文件夹（agent 阅读版）
        brief.json                grill 产物（询问/追问都更新此文件）
        WORKSPACE.md              文件清单索引（agent 导航唯一入口，自动生成）
        files.json                登记数据（WORKSPACE.md 的数据源）
        00_cache/                 原始抓取（fetch_lib.save_json 带 _meta）
        10_facts/FACTS.md         数据抓取产出的中性事实清单（冻结后禁改）
        20_forecast/ 30_valuation/ 40_thesis/    预测/估值/论点树输出
        60_draft/                 分章草稿（md）
        70_delivered/             历史交付版本（YYYYMMDD_7_报告名.docx 全留）
        80_reflection/            更新报告/复盘产物
        pipeline_log.json         flow_log 输出
      所有报告/                    人类入口：{编号}_{报告名}.docx（最新版覆盖）

用法：
    from workspace_lib import init_workspace, register_file, deliver, locate
    e = init_workspace('中药行业')            # 分配编号 7，建目录树
    register_file(7, path, kind='forecast', desc='3年盈利预测')
    deliver(7, hist_docx_path)               # 双写：70_delivered 历史 + 所有报告 最新
    locate('7') / locate(7) / locate('中药行业')

隔离规则：跨工作区互读禁止（更新报告例外=显式 dossier.inherited 指针）；
旧 data/ 与 暂存区/ 报告不迁移，首次被 /grill 定位时 assign_legacy 懒分配编号。
"""
import datetime
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_ROOT_OVERRIDE = None
SUBDIRS = ('00_cache', '10_facts', '20_forecast', '30_valuation', '40_thesis',
           '60_draft', '70_delivered', '80_reflection')
STATUSES = ('draft', 'delivered', 'blocked', 'archived')
ALL_REPORTS_DIR = '所有报告'


def set_root(path):
    """测试用：覆盖项目根定位。"""
    global _ROOT_OVERRIDE
    _ROOT_OVERRIDE = path


def find_project_root():
    """自 scripts/ 向上找含 .opencode/ 目录的祖先（v3.0 起不再依赖 暂存区/分类区 标记）。"""
    if _ROOT_OVERRIDE:
        return _ROOT_OVERRIDE
    d = os.path.dirname(os.path.abspath(__file__))
    while True:
        if os.path.isdir(os.path.join(d, '.opencode')):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            raise RuntimeError('未找到项目根（需含 .opencode/ 目录）')
        d = parent


def reports_root():
    d = os.path.join(find_project_root(), 'reports')
    os.makedirs(d, exist_ok=True)
    return d


def registry_path():
    return os.path.join(reports_root(), '_registry.json')


def load_registry():
    p = registry_path()
    if os.path.exists(p):
        with open(p, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'version': 1, 'next': 1, 'reports': {}}


def _save_registry(reg):
    reg['version'] = 1
    with open(registry_path(), 'w', encoding='utf-8') as f:
        json.dump(reg, f, ensure_ascii=False, indent=2)


def _now():
    return datetime.datetime.now().isoformat(timespec='seconds')


def _slug(subject):
    s = re.sub(r'[\\/:*?"<>|\s]+', '_', str(subject).strip())
    return s[:40] or '未命名'


def _dir_name(no, subject):
    return '%d_%s' % (no, _slug(subject))


def workspace_dir(no):
    e = entry(no)
    if e is None:
        raise KeyError('报告编号不存在: %r' % no)
    return e['dir']


def _touch_dirs(d):
    for sd in SUBDIRS:
        os.makedirs(os.path.join(d, sd), exist_ok=True)


def init_workspace(subject, report_no=None, meta=None):
    """新建报告工作区：分配编号、建目录树、登记账本、生成 WORKSPACE.md 骨架。"""
    reg = load_registry()
    if report_no is None:
        report_no = reg['next']
    key = str(report_no)
    if key in reg['reports']:
        raise ValueError('编号 %s 已被占用: %s' % (key, reg['reports'][key].get('subject')))
    d = os.path.join(reports_root(), _dir_name(report_no, subject))
    if os.path.exists(d):
        raise ValueError('工作区目录已存在: %s' % d)
    _touch_dirs(d)
    e = {'no': int(report_no), 'subject': str(subject), 'dir': d,
         'status': 'draft', 'created': _now(), 'updated': _now(),
         'report_name': None, 'deliverable': None, 'history': [],
         'legacy': False, 'legacy_path': None,
         'brief_approved': False, 'flow_level': None, 'report_type': None}
    if meta:
        e.update({k: v for k, v in meta.items() if k in
                  ('report_type', 'flow_level', 'report_name')})
    reg['reports'][key] = e
    reg['next'] = max(reg['next'], int(report_no) + 1)
    _save_registry(reg)
    _write_files_json(d, [])
    manifest(report_no)
    return e


def assign_legacy(path, subject=None):
    """旧报告（data/ 目录或 暂存区 docx）懒分配编号：只登记不迁移。"""
    if not os.path.exists(path):
        raise ValueError('旧报告路径不存在: %s' % path)
    reg = load_registry()
    for e in reg['reports'].values():
        if e.get('legacy_path') and os.path.abspath(e['legacy_path']) == os.path.abspath(path):
            return e
    e = {'no': reg['next'], 'subject': subject or os.path.basename(path),
         'dir': None, 'status': 'archived', 'created': _now(), 'updated': _now(),
         'report_name': None, 'deliverable': os.path.abspath(path)
         if path.lower().endswith('.docx') else None, 'history': [],
         'legacy': True, 'legacy_path': os.path.abspath(path),
         'brief_approved': None, 'flow_level': None, 'report_type': None}
    reg['reports'][str(e['no'])] = e
    reg['next'] = e['no'] + 1
    _save_registry(reg)
    return e


def entry(no):
    reg = load_registry()
    if isinstance(no, str) and no.isdigit():
        no = int(no)
    if isinstance(no, int):
        return reg['reports'].get(str(no))
    for e in reg['reports'].values():
        if e.get('subject') == no or os.path.basename(e.get('dir') or '') == no:
            return e
    return None


def locate(ref):
    """编号(int/str)/主题名/目录名 → 账本条目；找不到返回 None。"""
    return entry(ref)


def list_reports(status=None, include_legacy=True):
    reg = load_registry()
    out = [e for e in reg['reports'].values()
           if (status is None or e.get('status') == status)
           and (include_legacy or not e.get('legacy'))]
    return sorted(out, key=lambda x: x['no'])


def _files_path(no):
    return os.path.join(workspace_dir(no), 'files.json')


def _write_files_json(d, rows):
    with open(os.path.join(d, 'files.json'), 'w', encoding='utf-8') as f:
        json.dump({'files': rows}, f, ensure_ascii=False, indent=1)


def _read_files(no):
    p = _files_path(no)
    if os.path.exists(p):
        with open(p, 'r', encoding='utf-8') as f:
            return json.load(f).get('files', [])
    return []


def register_file(no, path, kind, desc='', by=''):
    """登记产物进 files.json 并重生成 WORKSPACE.md（QA：未登记=游离文件）。"""
    d = workspace_dir(no)
    ap = os.path.abspath(path)
    if not os.path.exists(ap):
        raise ValueError('登记的文件必须已存在: %s' % ap)
    rows = [r for r in _read_files(no) if r['path'] != os.path.relpath(ap, d)]
    rows.append({'path': os.path.relpath(ap, d), 'kind': kind, 'desc': desc,
                 'asof': _now()[:10], 'by': by})
    _write_files_json(d, rows)
    set_status(no, None)
    manifest(no)
    return rows[-1]


def manifest(no):
    """重生成 WORKSPACE.md（导航唯一入口：agent 只读此文件，禁止全目录扫描）。"""
    e = entry(no)
    d = e['dir']
    rows = _read_files(no)
    lines = ['# 工作区 %d · %s' % (e['no'], e['subject']),
             '',
             '- 编号: %d' % e['no'],
             '- 状态: %s' % e.get('status', 'draft'),
             '- 创建: %s    更新: %s' % (e.get('created'), e.get('updated')),
             '- brief: %s' % ('已批准' if e.get('brief_approved') else '未批准'),
             '',
             '| 路径 | 类型 | 说明 | 日期 | 产出者 |',
             '|---|---|---|---|---|']
    for r in rows:
        lines.append('| %s | %s | %s | %s | %s |'
                     % (r['path'], r['kind'], r['desc'], r['asof'], r['by']))
    lines += ['', '子目录: ' + ' '.join(SUBDIRS)]
    with open(os.path.join(d, 'WORKSPACE.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    return os.path.join(d, 'WORKSPACE.md')


def set_status(no, status, **fields):
    """更新状态（draft/delivered/blocked/archived）与任意账本字段。"""
    reg = load_registry()
    key = str(no if isinstance(no, int) else no)
    e = reg['reports'].get(key)
    if e is None:
        raise KeyError('报告编号不存在: %r' % no)
    if status is not None:
        if status not in STATUSES:
            raise ValueError('status 必须是 %s' % (STATUSES,))
        e['status'] = status
    e.update(fields)
    e['updated'] = _now()
    reg['reports'][key] = e
    _save_registry(reg)
    if status is not None and e.get('dir'):
        manifest(no)
    return e


def history_path(no, filename, report_name=None):
    """70_delivered 历史版本路径：YYYYMMDD_{编号}_{报告名}.docx。"""
    d = workspace_dir(no)
    name = _clean_report_name(filename, report_name)
    return os.path.join(d, '70_delivered', '%s_%d_%s' % (_now()[:10].replace('-', ''), no, name))


def _clean_report_name(filename, report_name=None):
    base = os.path.basename(report_name or filename)
    base = re.sub(r'\.docx?$', '', base)
    base = re.sub(r'^\d+_', '', base)
    base = re.sub(r'_\d{8}$', '', base)
    return _slug(base) + '.docx'


def deliver(no, hist_path, report_name=None):
    """交付双写：70_delivered 已由调用方保存 → 复制最新版到 所有报告/{编号}_{名}.docx。"""
    e = entry(no)
    if e is None:
        raise KeyError('报告编号不存在: %r' % no)
    name = _clean_report_name(report_name or os.path.basename(hist_path))
    latest_dir = os.path.join(reports_root(), ALL_REPORTS_DIR)
    os.makedirs(latest_dir, exist_ok=True)
    latest = os.path.join(latest_dir, '%d_%s' % (e['no'], name))
    shutil.copyfile(hist_path, latest)
    hist_abs = os.path.abspath(hist_path)
    history = [h for h in e.get('history', []) if h != hist_abs] + [hist_abs]
    set_status(no, 'delivered', report_name=name, deliverable=latest,
               history=history)
    register_file(no, hist_path, kind='report',
                  desc='历史交付版本 %s' % os.path.basename(hist_path), by='pipeline')
    return latest


def blocked(no, reason, resume_hint=''):
    """唯一合法中断态：写明卡点与恢复命令，不空等用户。"""
    return set_status(no, 'blocked',
                      blocked={'reason': reason, 'resume_hint': resume_hint,
                               'at': _now()})


def brief_path(no):
    return os.path.join(workspace_dir(no), 'brief.json')


def facts_path(no):
    return os.path.join(workspace_dir(no), '10_facts', 'FACTS.md')


def flow_log_path(no):
    return os.path.join(workspace_dir(no), 'pipeline_log.json')


if __name__ == '__main__':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    for e in list_reports():
        print('%4d  %-8s  %s' % (e['no'], e['status'], e['subject']))
