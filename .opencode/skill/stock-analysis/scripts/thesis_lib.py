# -*- coding: utf-8 -*-
"""论点树（thesis_lib）——报告核心论证的显式骨架，贯穿写作与审阅。

树 = 核心结论 + 3~5 承重柱（每柱带证据映射到 章节/图表/数据文件）。
用途：
- 建树：写作遵循树（每柱在正文有落点，证据映射到具体图表/数据）
- 更新报告/复盘：tree_diff 对照新旧树的结论与承重柱差异

用法：
    from thesis_lib import build_thesis, validate_thesis, save_thesis, load_thesis
    th = build_thesis(subject='XX股份',
                      conclusion='增持：合理区间 10~14 元（中枢 12 元）',
                      pillars=[
                        {'claim': '2028年EPS 2.6元（forecast 中性档）',
                         'probability': 0.6,
                         'evidence': [{'chapter': 'ch4', 'data_file': 'data/forecast_xx.json'}]},
                      ])
    validate_thesis(th); save_thesis(th, 'data/thesis_xx.json')
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_lib import save_json, load_json  # noqa: E402


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
