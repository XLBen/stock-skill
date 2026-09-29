# -*- coding: utf-8 -*-
"""论点树（thesis_lib）——报告核心论证的显式骨架，贯穿写作与质询。

树 = 核心结论 + 3~5 承重柱（每柱带证据映射到 章节/图表/数据文件）。
用途：
- 第 9a 步建树：写作遵循树（每柱在正文有落点，证据映射到具体图表/数据）
- 第 10 步审核：审核员通读重建树 → 检查"报告↔树"一致 + "树↔数据"质疑
- 质询承重清单：两会话 load_bearing_claims = 承重柱 + 核心结论（原则化）
- 反方章节：pillar_status() 产出"承重柱状态总览"（加固/留白/背反/存疑/未质询）

用法：
    from thesis_lib import build_thesis, validate_thesis, save_thesis, load_thesis, pillar_status
    th = build_thesis(subject='XX股份',
                      conclusion='增持：合理区间 10~14 元（中枢 12 元）',
                      pillars=[
                        {'claim': '2028年EPS 2.6元（forecast 中性档）',
                         'probability': 0.6,
                         'evidence': [{'chapter': 'ch4', 'fig': None,
                                       'data_file': 'data/forecast_xx.json'}]},
                        {'claim': '可比公司 PE 中枢 10.5 倍',
                         'probability': 0.7,
                         'evidence': [{'chapter': 'ch6', 'fig': 'fig6_peers',
                                       'data_file': 'data/quotes.json'}]},
                      ])
    validate_thesis(th); save_thesis(th, 'data/thesis_xx.json')
    status = pillar_status(th, [socratic_session_1, socratic_session_2])
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_lib import save_json, load_json  # noqa: E402

STATUS_ORDER = ('加固', '背反', '留白', '存疑', '未质询')


def build_thesis(subject, conclusion, pillars):
    """建树。pillars: [{claim, probability?, evidence: [{chapter?, fig?, data_file?}]}]。"""
    out_pillars = []
    for i, p in enumerate(pillars):
        out_pillars.append({'id': p.get('id') or 'p%d' % (i + 1),
                            'claim': p.get('claim', ''),
                            'probability': p.get('probability'),
                            'evidence': p.get('evidence', []),
                            'source': p.get('source', '')})
    return {'subject': subject, 'conclusion': conclusion, 'pillars': out_pillars}


def validate_thesis(th):
    """校验：结论非空；承重柱 2~6 根；每柱有论断且至少 1 条证据映射。"""
    problems = []
    if not (th.get('conclusion') or '').strip():
        problems.append('conclusion 缺失（核心结论必须一句话可判真伪）')
    pillars = th.get('pillars') or []
    if not (2 <= len(pillars) <= 6):
        problems.append('承重柱应为 2~6 根，当前 %d' % len(pillars))
    for p in pillars:
        if not (p.get('claim') or '').strip():
            problems.append('%s: claim 缺失' % p.get('id'))
        ev = p.get('evidence') or []
        if not ev:
            problems.append("%s: 无证据映射（每柱必须映射到章节/图表/数据文件）" % p.get('id'))
        for e in ev:
            if not any(e.get(k) for k in ('chapter', 'fig', 'data_file')):
                problems.append('%s: 证据映射不完整 %s' % (p.get('id'), e))
    if problems:
        raise ValueError('论点树校验失败: ' + '; '.join(problems))
    return True


def save_thesis(th, path, scope=None):
    validate_thesis(th)
    return save_json(th, path, ttl_hours=None,
                     scope=scope or (th.get('subject') or '') + '-thesis',
                     source='thesis_lib')


def load_thesis(path):
    return load_json(path)


def _claim_hit(claim, items):
    """claim 与会话中论断/背反记录的双向包含匹配。"""
    for it in items:
        c = it.get('claim') if isinstance(it, dict) else it
        if not c:
            continue
        if claim in c or c in claim:
            return it
    return None


def pillar_status(th, sessions):
    """承重柱 × 质询会话 → 状态总览（喂反方章节）。

    sessions: [socratic_session, ...]（字典，含 settled/unknowns/antinomies/challenges）
    单柱状态优先级：背反 > 留白 > 存疑(幸存未决) > 加固(被数据裁决) > 未质询。
    """
    rows = []
    targets = [{'claim': th['conclusion']}] + list(th.get('pillars') or [])
    for t in targets:
        claim = t['claim']
        row = {'id': t.get('id') or 'conclusion', 'claim': claim, 'status': '未质询',
               'detail': []}
        for s in sessions or []:
            ant = _claim_hit(claim, s.get('antinomies') or [])
            if ant:
                row['status'] = '背反'
                row['detail'].append('背反: %s' % ant.get('cause', ''))
                continue
            unk = _claim_hit(claim, s.get('unknowns') or [])
            if unk:
                row['status'] = '留白' if row['status'] != '背反' else row['status']
                row['detail'].append('留白: %s' % (unk.get('note') or unk.get('settling_data_spec') or '')[:60])
                continue
            surv = _claim_hit(claim, [c for c in (s.get('challenges') or [])
                                      if c.get('status') in ('pending', 'revised')])
            if surv:
                row['status'] = '存疑' if row['status'] in ('未质询',) else row['status']
                row['detail'].append('幸存质询: %s' % surv.get('id'))
                continue
            stl = _claim_hit(claim, s.get('settled') or [])
            if stl:
                if row['status'] == '未质询':
                    row['status'] = '加固'
                row['detail'].append('数据裁决: %s' % os.path.basename(stl.get('evidence_file') or ''))
        rows.append(row)
    return {'subject': th.get('subject'), 'conclusion': th.get('conclusion'),
            'pillars': rows,
            'summary': {st: sum(1 for r in rows if r['status'] == st)
                        for st in STATUS_ORDER}}


def tree_diff(built, reconstructed):
    """建的树 vs 审核员重建的树 → 结构化对照（报告↔树一致性）。

    built: thesis_lib 输出（含 conclusion/pillars[].claim）
    reconstructed: 审核员输出 {conclusion: str, pillars: [str]}
    返回 {conclusion_match, matched, missing(报告有树无→柱失守/未呈现), extra(树有报告无→审核员读出更多)}
    """
    rec = reconstructed or {}
    rec_conc = (rec.get('conclusion') or '').strip()
    conc_match = bool(rec_conc and (rec_conc in built.get('conclusion', '')
                                    or built.get('conclusion', '') in rec_conc))
    rec_pillars = [str(p).strip() for p in (rec.get('pillars') or []) if str(p).strip()]
    matched, missing = [], []
    for p in built.get('pillars') or []:
        claim = p.get('claim', '')
        hit = next((r for r in rec_pillars if claim in r or r in claim), None)
        if hit:
            matched.append({'built': claim, 'reconstructed': hit})
        else:
            missing.append(claim)
    matched_claims = {m['built'] for m in matched}
    extra = [r for r in rec_pillars
             if not any(r in c or c in r for c in matched_claims)]
    return {'conclusion_match': conc_match,
            'matched': matched, 'missing': missing, 'extra': extra}


def revision_checklist(th=None, sessions=None):
    """第 10 步修订清单（显式枚举，防漏改）。"""
    items = ['正文修正（存疑/留白对应章节）',
             '反方章节更新（两会话幸存质询并集 + 同一数字两种读法 + 承重柱状态总览）',
             '附录质询统计表重生成（两会话合并）',
             '数字溯源表重生成（若修正引入新数字）']
    if th is not None:
        items.append('论点树状态更新（pillar_status 重跑）')
    if sessions:
        revs = []
        for s in sessions:
            for c in s.get('challenges') or []:
                r = c.get('response') or {}
                if c.get('status') == 'revised':
                    revs.append('%s→%s' % (c.get('target_claim', '')[:30],
                                           r.get('revised_claim', '')[:30]))
        if revs:
            items.append('质询修正核对: %s' % '；'.join(revs[:5]))
    return items
