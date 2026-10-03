# -*- coding: utf-8 -*-
"""资产档案与复盘闭环（review_lib）——让第 N 份报告站在第 N-1 份的肩上。

档案（dossier）= 工作区根 档案/{资产}.json：
- conclusions   历次结论（评级/区间/中枢/当时价/有效期/复查触发条件）
- assumptions   历次关键假设（含失效信号，供后续核对）
- judgments     前次结论的事后判定（命中/失误/待定 + 依据）
- calibration   校准率 = 命中 / (命中+失误)
- data_notes    数据源可靠性笔记（哪个源总 stale/字段总对不上，跨报告积累）
- inherited     可继承调研资产（验证过的可比公司清单/口径/行业数据线索）

闭环流程：
1. 新报告第 1 步：load_dossier(资产) → 有档案则生成 prior 上下文（前次结论复盘素材）
2. LLM 抓当前行情，逐条判定前次结论 → update_judgment()（判定必须带当前事实依据）
3. 报告蓝图插入条件章节"前次结论复盘"（dossier.prior=true 时）
4. save_stage 落档时自动 record()（结论+假设+触发条件进档案）

用法：
    from review_lib import load_dossier, record, update_judgment, calibration
    d = load_dossier('锦江酒店')                # None 或档案 dict
    record('锦江酒店', {'date': '2026-08-30', 'rating': '买入', 'range_low': 28.0,
                       'central': 32.0, 'range_high': 36.0, 'price_now': 30.1,
                       'expiry': '2027-08-30',
                       'review_triggers': ['单季RevPAR同比转负', 'PB升破2.5'],
                       'assumptions': [{'desc': '2027年EPS 1.9元', 'probability': 0.6,
                                        'trigger': 'Q3业绩低于预期20%'}]},
          report_file='锦江投资研究报告_20260830.docx')
    update_judgment('锦江酒店', 0, '命中', evidence='当前价33.5处于区间内', asof='2027-02-01')
    print(calibration('锦江酒店'))
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_lib import save_json  # noqa: E402

JUDGMENTS = ('命中', '失误', '待定')


def _sanitize(subject):
    return ''.join(c if c not in r'\/:*?"<>|' else '_' for c in subject.strip())


def dossier_key(subject):
    """主键解析（代码优先）：subject 含 6 位数字代码 → 用代码；否则用净化名。
    '锦江酒店(600754)'/'600754'/'锦江酒店600754' 都归档到 600754.json。"""
    m = re.search(r'([0-9]{6})', str(subject))
    return m.group(1) if m else _sanitize(subject)


def _find_project_root():
    d = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    while True:
        parent = os.path.dirname(d)
        if parent == d:
            return None
        if os.path.isdir(os.path.join(d, '暂存区')) and os.path.isdir(os.path.join(d, '分类区')):
            return d
        if os.path.isdir(os.path.join(d, '.opencode')):
            return d
        d = parent


def dossier_dir():
    root = _find_project_root()
    if root is None:
        raise RuntimeError('未找到项目根（需同时含 暂存区/ 与 分类区/）')
    d = os.path.join(root, '档案')
    os.makedirs(d, exist_ok=True)
    return d


def dossier_path(subject):
    return os.path.join(dossier_dir(), dossier_key(subject) + '.json')


def _legacy_path(subject):
    return os.path.join(dossier_dir(), _sanitize(subject) + '.json')


def load_dossier(subject):
    """加载档案；兼容旧命名（无代码文件名）自动迁移到代码主键。无档案返回 None。"""
    p = dossier_path(subject)
    if not os.path.exists(p):
        lp = _legacy_path(subject)
        if lp != p and os.path.exists(lp):
            with open(lp, 'r', encoding='utf-8') as f:
                d = json.load(f)
            d.setdefault('aliases', [])
            if str(subject).strip() not in d['aliases']:
                d['aliases'].append(str(subject).strip())
            save_json(d, p, ttl_hours=None, source='review_lib')
            os.remove(lp)
            return d
        return None
    with open(p, 'r', encoding='utf-8') as f:
        return json.load(f)


def has_prior(subject):
    """蓝图条件：prior_review 章节是否出现。"""
    d = load_dossier(subject)
    return bool(d and d.get('conclusions'))


def new_dossier(subject):
    return {'subject': subject, 'aliases': [str(subject).strip()],
            'conclusions': [], 'assumptions': [],
            'judgments': {}, 'data_notes': [], 'inherited': {}}


def _save(dossier, path):
    dossier['updated_at'] = os.path.getmtime(path) if os.path.exists(path) else None
    return save_json(dossier, path, ttl_hours=None,
                     scope=dossier.get('subject', '') + '-dossier', source='review_lib')


def record(subject, entry, report_file=None, report_no=None):
    """落档一份报告的结论（save_stage 自动调用或手动）。entry 字段见模块 docstring。"""
    for k in ('date', 'rating', 'range_low', 'range_high', 'central'):
        if entry.get(k) is None:
            raise ValueError('结论 entry 缺少必填字段 %s（评级/区间/中枢/日期）' % k)
    if not entry.get('review_triggers'):
        raise ValueError('缺少 review_triggers（复查触发条件）——开环结论禁止入档')
    d = load_dossier(subject) or new_dossier(subject)
    if str(subject).strip() not in (d.get('aliases') or []):
        d.setdefault('aliases', []).append(str(subject).strip())
    item = dict(entry)
    item['report_file'] = report_file
    item['report_no'] = report_no
    idx = len(d['conclusions'])
    d['conclusions'].append(item)
    for a in entry.get('assumptions', []) or []:
        a = dict(a)
        a['conclusion_idx'] = idx
        d['assumptions'].append(a)
    return _save(d, dossier_path(subject))


def update_judgment(subject, conclusion_idx, judgment, evidence='', asof=''):
    """事后判定前次结论。judgment ∈ 命中/失误/待定；evidence 必须写当前事实（价格/事件）。"""
    if judgment not in JUDGMENTS:
        raise ValueError('judgment 必须是 %s' % (JUDGMENTS,))
    if not evidence:
        raise ValueError('判定必须带 evidence（当前事实：价格/事件/数据）')
    d = load_dossier(subject)
    if d is None:
        raise KeyError('无档案: %s' % subject)
    if not (0 <= conclusion_idx < len(d['conclusions'])):
        raise IndexError('conclusion_idx 越界: %s（共 %d 条）' % (conclusion_idx, len(d['conclusions'])))
    c = d['conclusions'][conclusion_idx]
    if c.get('expiry') and asof and asof > c['expiry'] and judgment == '待定':
        pass
    d['judgments'].setdefault(str(conclusion_idx), []).append(
        {'judgment': judgment, 'evidence': evidence, 'asof': asof})
    return _save(d, dossier_path(subject))


def suggest_judgment(conclusion, price_now, asof=''):
    """量化判定建议（校准率的地基不许自由心证）。

    规则：未到期且无触发信息 → 待定；价格落在区间内 → 命中；区间外（已到期或无有效期）→ 失误。
    """
    if price_now is None:
        return {'judgment': '待定', 'reason': '无当前价'}
    low, high = conclusion.get('range_low'), conclusion.get('range_high')
    expiry = conclusion.get('expiry')
    inside = (low is not None and high is not None and low <= price_now <= high)
    if expiry and asof and asof < expiry and not inside:
        return {'judgment': '待定', 'reason': '未到期（%s 到期），当前价 %.2f 在区间外，跟踪' % (expiry, price_now)}
    if inside:
        return {'judgment': '命中', 'reason': '价格 %.2f 落在区间 [%s, %s] 内' % (price_now, low, high)}
    return {'judgment': '失误', 'reason': '价格 %.2f 在区间 [%s, %s] 外%s'
            % (price_now, low, high, '（已到期）' if expiry and asof and asof >= expiry else '')}


def prior_review_table(subject, price_now=None, asof=''):
    """前次结论复盘素材：历次结论 + 最新判定 + 量化建议判定 + 是否触发复查。"""
    d = load_dossier(subject)
    if not d or not d['conclusions']:
        return None
    rows = []
    for i, c in enumerate(d['conclusions']):
        j = (d.get('judgments') or {}).get(str(i), [])
        last_j = j[-1] if j else None
        rows.append({'idx': i, 'date': c['date'], 'rating': c['rating'],
                     'range': [c['range_low'], c['range_high']], 'central': c['central'],
                     'price_then': c.get('price_now'), 'expiry': c.get('expiry'),
                     'review_triggers': c.get('review_triggers', []),
                     'last_judgment': last_j, 'price_now': price_now,
                     'suggested': suggest_judgment(c, price_now, asof) if price_now is not None else None})
    return {'subject': subject, 'rows': rows, 'calibration': calibration(subject)}


def calibration(subject):
    """校准率 = 命中 / (命中+失误)（取每条结论的最新判定）。"""
    d = load_dossier(subject)
    if not d:
        return None
    hit = miss = 0
    for i in range(len(d['conclusions'])):
        js = (d.get('judgments') or {}).get(str(i), [])
        if not js:
            continue
        last = js[-1]['judgment']
        if last == '命中':
            hit += 1
        elif last == '失误':
            miss += 1
    total = hit + miss
    return {'hit': hit, 'miss': miss, 'rate': round(hit / total, 4) if total else None}


def error_patterns(subject=None):
    """跨档案错误模式聚合：哪类评级总失误（方法库自学习的入口）。

    subject 为空时扫描全部档案。返回 {by_rating, overall, failures}：
    - by_rating: {评级: {hit, miss, rate}}
    - overall:   全部判定汇总
    - failures:  失误样本清单（subject/结论/判定依据，最多 10 条）供人工归因
    """
    def _load_all():
        d = dossier_dir()
        out = []
        for fn in os.listdir(d):
            if fn.endswith('.json'):
                try:
                    with open(os.path.join(d, fn), 'r', encoding='utf-8') as f:
                        out.append(json.load(f))
                except Exception:
                    continue
        return out

    dossiers = [load_dossier(subject)] if subject else _load_all()
    dossiers = [x for x in dossiers if x]
    by_rating, failures = {}, []
    hit = miss = 0
    for d in dossiers:
        for i, c in enumerate(d.get('conclusions') or []):
            js = (d.get('judgments') or {}).get(str(i), [])
            if not js:
                continue
            last = js[-1]
            rating = c.get('rating') or '未标'
            slot = by_rating.setdefault(rating, {'hit': 0, 'miss': 0})
            if last['judgment'] == '命中':
                slot['hit'] += 1
                hit += 1
            elif last['judgment'] == '失误':
                slot['miss'] += 1
                miss += 1
                failures.append({'subject': d.get('subject'), 'rating': rating,
                                 'claim_range': [c.get('range_low'), c.get('range_high')],
                                 'evidence': (last.get('evidence') or '')[:80]})
    for v in by_rating.values():
        t = v['hit'] + v['miss']
        v['rate'] = round(v['hit'] / t, 4) if t else None
    total = hit + miss
    return {'by_rating': by_rating,
            'overall': {'hit': hit, 'miss': miss,
                        'rate': round(hit / total, 4) if total else None},
            'failures': failures[:10]}


def note_data_source(subject, source, note, reliability):
    """积累数据源可靠性笔记（哪个源总失效/字段总对不上）。"""
    d = load_dossier(subject) or new_dossier(subject)
    d['data_notes'].append({'source': source, 'note': note, 'reliability': reliability})
    return _save(d, dossier_path(subject))


def inherit_asset(subject, key, value):
    """登记可继承调研资产（可比公司清单/口径/行业数据线索），下次报告直接复用。"""
    d = load_dossier(subject) or new_dossier(subject)
    d['inherited'][key] = value
    return _save(d, dossier_path(subject))
