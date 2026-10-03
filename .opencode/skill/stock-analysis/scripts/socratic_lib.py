# -*- coding: utf-8 -*-
"""苏格拉底质询引擎（socratic_lib）——规则裁决器，LLM 只当双方辩手。

v3.0 单次审计模式（mode='single_audit'，新流水线唯一用法）：
- 两会话合一：写作前假设质询并入终稿后单次审计（承重论点=论点树承重柱+核心结论）
- 硬上限 2 轮：R1 攻防（审计员攻击→立论者回应），R2 修复核验（只审修改处+未决）
- 火力下限（audit_readiness）：R1 受理 ≥4 条（full）/≥3 条（standard），full 必含 ≥1 替代解读/隐含前提
- 覆盖度量（audit_coverage）：每承重柱 ≥1 受理质询或书面免检理由（exempt_pillar）
- 裁决门禁（audit_gate）：高严重度质询无四归宿（data/revise/unknown/背反）→ 禁止终稿
- H1 回流保留：revise 带 assumption_ref → revised_assumption_claims → 重跑预测估值 → R2 核验

经典模式（mode='classic'）保留循环至收敛行为，供库能力兼容与回溯测试。

三方结构：立论者（主上下文）/ 质询者（Task 子代理，全新上下文）/ 裁决（本库，纯规则）。

质询准入（反胡搅蛮缠过滤器，三缺一即驳回）：
1. 只打承重墙：target_claim 必须在会话的 load_bearing_claims 内（核心论点/关键假设/估值中枢/因果链）
2. 以数据立状：settling_data_spec 必须写明"什么可观测数据能裁决此问"
3. 一事不再理：已被磁盘上可回查数据裁决的论点永久锁定（settled 登记簿），重问即驳回

立论者三种回应（每条质询必有归宿）：
- data   引用磁盘上的数据文件裁决（文件必须存在，否则降级失败）
- revise 让步并修改论点（新论点进下一轮）
- unknown 双方无数据 → 留白（已知未知），关闭并进盲点清单

"到底"= 论点落到四层基岩之一：[实证]数据 / [假设]显式假设 / [留白]盲点 / [背反]二律背反记录。
二律背反检测（触发其一即转为背反记录，永久关闭）：
- 同一论点被有效质询 ≥2 轮且无任何一条被数据裁决
- 正题↔反题振荡（论点被修正后又改回原样）
- 双方各持落盘数据但结论相反（data 对 data 且互斥）

循环终止（无轮数上限）：
- 全部承重论点触底且无新有效质询 → 完成
- 停滞判定：本轮 0 条新有效质询 → 立即结束（防原地打转）
- 每轮必须以文档变更结束（修正/补数据/进盲点），禁止纯辩论轮

用法：
    from socratic_lib import new_session, submit_challenges, defend, round_summary, stats
    s = new_session(subject='XX股份', load_bearing_claims=['2028年EPS达2.6元', '合理区间10~13元'])
    admitted = submit_challenges(s, [{'target_claim': '2028年EPS达2.6元', 'type': '证据',
        'settling_data_spec': '近3年分部营收与毛利率的一手财报数据', 'severity': '高'}])
    defend(s, admitted[0]['id'], 'data', evidence_file='data/xx_fin.json')
    print(round_summary(s), stats(s))
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_lib import save_json, load_json  # noqa: E402

VALID_TYPES = ('证据', '因果', '反例', '口径', '反事实',
               '替代解读', '隐含前提', '联合脆弱',
               '数字一致性', '结论-证据', '图文引用', '章节矛盾', '蓝图缺口')
INTERPRETATION_TYPES = ('替代解读', '隐含前提')
CLERICAL_TYPES = ('数字一致性', '结论-证据', '图文引用', '章节矛盾', '蓝图缺口')
FETCH_BUDGET_PER_ROUND = 3
RESPONSES = ('data', 'revise', 'unknown')
ANTINOMY_CAUSES = ('预设不可通约', '裁决数据不可得', '价值判断分歧')
CRUX_STRUCT_WORDS = ('预言', '分辨', '读法', '观测', '成立', '支撑', '翻案', '则', '改善')
CRUX_MIN_LEN = 12
NOTE_MIN_LEN = 8


def _crux_quality_ok(crux):
    """crux 最低质量启发式：长度达标且含结构性表述（防"是的它有区别"式敷衍）。"""
    return len(crux) >= CRUX_MIN_LEN and any(w in crux for w in CRUX_STRUCT_WORDS)


def new_session(subject, load_bearing_claims, max_repeats=2, mode='classic',
                max_rounds=None):
    """建会话。load_bearing_claims：承重论点清单（质询只准打这些）。

    mode='single_audit'：单次审计（轮次硬上限 max_rounds，默认 2）；
    mode='classic'：循环至收敛（旧行为，兼容保留）。
    """
    if not load_bearing_claims:
        raise ValueError('load_bearing_claims 不能为空：先从盈利预测/估值/核心逻辑中提取承重论点')
    if mode not in ('classic', 'single_audit'):
        raise ValueError("mode 必须是 'classic' 或 'single_audit'")
    if mode == 'single_audit' and max_rounds is None:
        max_rounds = 2
    return {'subject': subject,
            'mode': mode,
            'load_bearing_claims': list(load_bearing_claims),
            'challenges': [],
            'settled': [],
            'unknowns': [],
            'antinomies': [],
            'claims_current': list(load_bearing_claims),
            'claims_history': {c: [c] for c in load_bearing_claims},
            'rounds': [],
            'round_counter': 0,
            'evidence_registry': [],
            'exemptions': [],
            'config': {'max_repeats': max_repeats,
                       'fetch_budget_per_round': FETCH_BUDGET_PER_ROUND,
                       'max_rounds': max_rounds}}


def exempt_pillar(session, claim, reason):
    """书面免检（audit_coverage 用）：某承重柱明确不质询必须给理由。

    claim 可以来自会话承重清单，也可来自 thesis 柱（外部树核对场景）。
    """
    if not (reason or '').strip():
        raise ValueError('免检必须给书面理由（覆盖度量可审计）')
    if not (claim or '').strip():
        raise ValueError('免检对象不能为空')
    matched = _match_claim(session, claim)
    session.setdefault('exemptions', []).append(
        {'claim': matched or claim.strip(), 'reason': reason})
    return session['exemptions'][-1]


def register_discriminating_evidence(session, path, purpose=''):
    """登记问答中新引入的区分性证据（替代解读类 data 回应只认这里登记的文件）。

    path 必须已存在于磁盘；命名建议 challenge_r{轮}_{序}.json / review_r{轮}_{序}.json。
    """
    if not path or not os.path.exists(path):
        raise ValueError('区分性证据必须落盘可回查: %r' % path)
    session['evidence_registry'].append({'path': os.path.abspath(path), 'purpose': purpose})
    return session['evidence_registry'][-1]


def _is_new_evidence(session, path):
    """判定 evidence_file 是否为问答中新引入（登记过或 r{轮} 命名）。"""
    if not path:
        return False
    ap = os.path.abspath(path)
    for e in session.get('evidence_registry', []):
        if os.path.abspath(e['path']) == ap:
            return True
    return bool(re.search(r'[\\/](challenge|review)_r\d+', path))


def _match_claim(session, target):
    """承重墙匹配：target 与登记论点精确或包含匹配。"""
    for c in session['claims_current']:
        if target == c or (isinstance(target, str) and isinstance(c, str)
                           and (target in c or c in target)):
            return c
    return None


def _is_settled(session, claim):
    return any(s['claim'] == claim for s in session['settled'])


def submit_challenges(session, challenges):
    """质询者提交一批质询（通常来自子代理 JSON）。逐条裁决准入，返回被受理的质询。"""
    session['round_counter'] += 1
    rnd = session['round_counter']
    admitted, rejected = [], []
    for i, ch in enumerate(challenges or []):
        target = (ch.get('target_claim') or '').strip()
        spec = (ch.get('settling_data_spec') or '').strip()
        ctype = ch.get('type', '证据')
        cid = ch.get('id') or 'r%d_%02d' % (rnd, i + 1)
        reason = None
        if ctype not in VALID_TYPES:
            reason = 'type 非法：%s（可用 %s）' % (ctype, VALID_TYPES)
        matched = _match_claim(session, target) if target else None
        if reason is None and matched is None:
            reason = '不打承重墙：%s 不在承重论点清单' % target[:50]
        if reason is None and not spec:
            reason = '未以数据立状：缺 settling_data_spec（提不出裁决数据就没有质询资格）'
        crux = (ch.get('crux') or '').strip()
        if reason is None and ctype in INTERPRETATION_TYPES and not crux:
            reason = '替代解读/隐含前提类质询必须给 crux（区分两种解读的可观测证据：读法A预言X、读法B预言Y）'
        if reason is None and ctype in INTERPRETATION_TYPES and crux and not _crux_quality_ok(crux):
            reason = 'crux 质量不足：需 ≥%d 字且含结构性表述（%s）——写清"哪种读法预言什么、查什么分辨"' % (
                CRUX_MIN_LEN, '/'.join(CRUX_STRUCT_WORDS[:5]))
        if reason is None and _is_settled(session, matched):
            reason = '一事不再理：%s 已被数据裁决（settled 登记簿）' % matched[:50]
        if reason is None:
            dup = any(c['target_claim'] == matched and c['type'] == ctype
                      for c in session['challenges']
                      if c['status'] in ('pending', 'settled', 'unknown', 'antinomy'))
            if dup:
                reason = '重复质询：%s[%s] 已在质询队列' % (matched[:40], ctype)
        if reason is None:
            record = {'id': cid, 'round': rnd, 'target_claim': matched,
                      'raw_target': target, 'type': ctype,
                      'settling_data_spec': spec, 'crux': crux or None,
                      'severity': ch.get('severity', '中'),
                      'challenger_data_files': ch.get('data_files', []),
                      'argument': ch.get('argument', ''),
                      'status': 'pending', 'response': None}
            session['challenges'].append(record)
            admitted.append(record)
        else:
            rejected.append({'id': cid, 'target_claim': target, 'reason': reason})
    fetches = _fetches_used(session, rnd)
    session['rounds'].append({'round': rnd, 'admitted': len(admitted),
                              'rejected': rejected, 'fetches_used': fetches,
                              'fetch_budget': session['config'].get('fetch_budget_per_round',
                                                                    FETCH_BUDGET_PER_ROUND)})
    _detect_antinomy(session)
    return admitted


def defend(session, challenge_id, response, evidence_file=None, revised_claim=None, note='',
           assumption_ref=None):
    """立论者回应（note 必填：反驳理由）。

    data：证据文件必须在磁盘存在；替代解读/隐含前提类只认问答中【新引入】的
    区分性证据（evidence_registry 登记过或 challenge_r*/review_r* 命名）——
    "数字本身没错"不构成对解读质询的回应。
    revise：给新论点；assumption_ref 可标记该修正涉及的预测假设
    （回流协议：凡带 assumption_ref 的 revise 必须重跑 forecast_lib 再估值）。
    unknown：留白。
    """
    ch = None
    for c in session['challenges']:
        if c['id'] == challenge_id:
            ch = c
            break
    if ch is None:
        raise KeyError('未找到质询 %s' % challenge_id)
    if ch['status'] != 'pending':
        raise ValueError('质询 %s 已关闭（%s），不可重复回应' % (challenge_id, ch['status']))
    if response not in RESPONSES:
        raise ValueError('response 必须是 %s' % (RESPONSES,))
    if not (note or '').strip():
        raise ValueError('回应必须给理由（note）：为什么这个证据/修正/留白回应了质询——裸断言无效')
    if len(note.strip()) < NOTE_MIN_LEN:
        raise ValueError('note 过短（<%d 字）——敷衍式理由无效，写清证据如何回应质询' % NOTE_MIN_LEN)
    if response == 'data':
        if not evidence_file or not os.path.exists(evidence_file):
            raise ValueError('data 回应的 evidence_file 必须存在于磁盘（可回查才配裁决）: %r'
                             % evidence_file)
        if ch['type'] in INTERPRETATION_TYPES and not _is_new_evidence(session, evidence_file):
            raise ValueError('替代解读/隐含前提类只认问答中【新引入】的区分性证据'
                             '（先 register_discriminating_evidence 或按 challenge_r*/review_r* 命名落盘）: %r'
                             % evidence_file)
        ch['status'] = 'settled'
        ch['response'] = {'type': 'data', 'evidence_file': evidence_file, 'note': note}
        session['settled'].append({'claim': ch['target_claim'], 'challenge': ch['id'],
                                   'evidence_file': evidence_file})
    elif response == 'revise':
        if not revised_claim:
            raise ValueError('revise 回应必须给 revised_claim（新论点）')
        old = ch['target_claim']
        ch['status'] = 'revised'
        ch['response'] = {'type': 'revise', 'revised_claim': revised_claim, 'note': note,
                          'assumption_ref': assumption_ref or None}
        if revised_claim not in session['claims_current']:
            session['claims_current'].append(revised_claim)
        session['claims_history'].setdefault(old, []).append(revised_claim)
    else:
        ch['status'] = 'unknown'
        ch['response'] = {'type': 'unknown', 'note': note}
        session['unknowns'].append({'claim': ch['target_claim'], 'challenge': ch['id'],
                                    'settling_data_spec': ch['settling_data_spec'], 'note': note})
    _detect_antinomy(session)
    return ch


def revised_assumption_claims(session):
    """回流查询：质询中修正过、且涉及预测假设的论点（凡在此清单——
    必须重跑 forecast_lib 重建预测、再重跑估值，禁止沿用旧数字）。"""
    out = []
    for c in session.get('challenges') or []:
        r = c.get('response') or {}
        if c.get('status') == 'revised' and r.get('assumption_ref'):
            out.append({'challenge': c['id'], 'old_claim': c['target_claim'],
                        'revised_claim': r.get('revised_claim'),
                        'assumption_ref': r.get('assumption_ref'), 'note': r.get('note')})
    return out


def _fetches_used(session, round_no):
    """统计某轮双方新抓取的数据文件数（质询者 data_files + 立论者新引入证据）。"""
    n = 0
    for c in session['challenges']:
        if c.get('round') == round_no:
            n += len(c.get('challenger_data_files') or [])
            resp = c.get('response') or {}
            if resp.get('type') == 'data' and _is_new_evidence(session, resp.get('evidence_file') or ''):
                n += 1
    return n


def fetch_budget_left(session):
    """当前轮剩余新抓取预算（每轮默认 ≤3）。超出预算的抓取建议留到下一轮。"""
    if not session['rounds']:
        return session['config'].get('fetch_budget_per_round', FETCH_BUDGET_PER_ROUND)
    last = session['rounds'][-1]
    return max(0, last.get('fetch_budget', FETCH_BUDGET_PER_ROUND) - last.get('fetches_used', 0))


def _detect_antinomy(session):
    """二律背反检测：同论点有效质询≥max_repeats 且无数据裁决且有回应痕迹 → 转背反记录。"""
    max_repeats = session['config'].get('max_repeats', 2)
    by_claim = {}
    for c in session['challenges']:
        by_claim.setdefault(c['target_claim'], []).append(c)
    for claim, chs in by_claim.items():
        if _is_settled(session, claim):
            continue
        already = any(a['claim'] == claim for a in session['antinomies'])
        if already:
            continue
        valid = [c for c in chs if c['status'] in ('pending', 'revised', 'unknown', 'settled', 'antinomy')]
        pending = [c for c in chs if c['status'] == 'pending']
        data_vs_data = (any(c.get('challenger_data_files') for c in chs)
                        and any(c.get('response', {}) and c['response'].get('type') == 'data'
                                for c in chs if c.get('response')))
        oscillated = _oscillation(session, claim)
        rounds_hit = len({c['round'] for c in valid}) >= max_repeats
        if (rounds_hit or data_vs_data or oscillated) and not pending:
            causes = []
            if data_vs_data:
                causes.append('双方各持落盘数据但结论相反')
            elif oscillated:
                causes.append('正题↔反题振荡（修正后又改回）')
            else:
                causes.append('裁决数据不可得（≥%d 轮无数据裁决）' % max_repeats)
            thesis_data = [f for c in chs for f in (c.get('challenger_data_files') or [])]
            antithesis_data = [c['response'].get('evidence_file') for c in chs
                               if c.get('response') and c['response'].get('type') == 'data']
            session['antinomies'].append({
                'claim': claim,
                'cause': '；'.join(causes),
                'thesis_data': thesis_data,
                'antithesis_data': [f for f in antithesis_data if f],
                'impact': '（立论者须填写：若该背反为真，结论如何变化——衔接 reverse_stress）'})
            for c in chs:
                if c['status'] == 'pending':
                    c['status'] = 'antinomy'


def _oscillation(session, claim):
    """振荡检测：论点历史出现 A→B→A 回环。"""
    hist = session.get('claims_history', {}).get(claim, [])
    seen = {}
    for i, c in enumerate(hist):
        if c in seen and i - seen[c] >= 2:
            return True
        seen[c] = i
    return False


def pending_challenges(session):
    return [c for c in session['challenges'] if c['status'] == 'pending']


def at_bedrock(session):
    """全部承重论点是否触底（无 pending 且当前论点全部落在四层基岩）。"""
    if pending_challenges(session):
        return False
    for claim in session['claims_current']:
        if _is_settled(session, claim):
            continue
        if any(u['claim'] == claim for u in session['unknowns']):
            continue
        if any(a['claim'] == claim for a in session['antinomies']):
            continue
        return False
    return True


def should_continue(session):
    """是否继续下一轮。

    single_audit：轮次硬上限（默认 2）优先——R1 攻防、R2 修复核验后无论 pending
    与否一律收束（未决高严重度质询由 audit_gate 拦截终稿，不靠加轮数）。
    classic：有 pending 必继续；无 pending 触底即完成；上一轮 0 新受理=停滞。
    """
    if session.get('mode') == 'single_audit':
        max_rounds = session['config'].get('max_rounds') or 2
        if session['round_counter'] >= max_rounds:
            return False, '单次审计轮次上限 %d 已达（R1 攻防 + R2 修复核验）' % max_rounds
        if pending_challenges(session):
            return True, '轮次内仍有 pending 待回应'
        if at_bedrock(session):
            return False, '全部承重论点已触底（四层基岩）'
        last = session['rounds'][-1] if session['rounds'] else None
        if last and last['admitted'] == 0:
            return False, '停滞判定：上一轮 0 条新有效质询'
        return True, '有新论点待质询'
    if pending_challenges(session):
        return True, ''
    if at_bedrock(session):
        return False, '全部承重论点已触底（四层基岩）'
    last = session['rounds'][-1] if session['rounds'] else None
    if last and last['admitted'] == 0:
        return False, '停滞判定：上一轮 0 条新有效质询'
    return True, '有新论点待质询'


def _round1_admitted(session):
    return [c for c in session['challenges'] if c.get('round') == 1]


def audit_readiness(session, level='full'):
    """防掉队闸 1·火力下限：R1 受理数与质询类型构成。

    full: R1 ≥4 条且必含 ≥1 替代解读/隐含前提类；standard: ≥3 条。
    """
    need = 4 if level == 'full' else 3
    r1 = _round1_admitted(session)
    issues = []
    if len(r1) < need:
        issues.append('R1 受理质询 %d 条 < 下限 %d 条（审计员火力不足）' % (len(r1), need))
    if level == 'full' and not any(c['type'] in INTERPRETATION_TYPES for c in r1):
        issues.append('full 级 R1 必含 ≥1 条替代解读/隐含前提类质询（最锋利的攻击缺席）')
    return {'ok': not issues, 'level': level, 'r1_admitted': len(r1), 'issues': issues}


def audit_coverage(session, thesis=None):
    """防掉队闸 2·覆盖度量：每承重柱（+核心结论）≥1 受理质询或书面免检理由。"""
    if thesis:
        claims = [thesis.get('conclusion', '')] + \
                 [p.get('claim', '') for p in (thesis.get('pillars') or [])]
    else:
        claims = list(session.get('load_bearing_claims') or [])
    covered_idx = set()
    for c in session.get('challenges') or []:
        m = c.get('target_claim') or ''
        for i, cl in enumerate(claims):
            if cl and (m == cl or m in cl or cl in m):
                covered_idx.add(i)
    exemptions = session.get('exemptions') or []
    exempt_idx = set()
    for e in exemptions:
        ec = e.get('claim') or ''
        for i, cl in enumerate(claims):
            if cl and (ec == cl or ec in cl or cl in ec):
                exempt_idx.add(i)
    missing = [claims[i] for i in range(len(claims))
               if i not in covered_idx and i not in exempt_idx]
    return {'ok': not missing, 'total': len(claims),
            'covered': len(covered_idx), 'exempted': len(exempt_idx),
            'missing': missing,
            'exemptions': exemptions}


def audit_gate(session):
    """防掉队闸 3·裁决门禁：高严重度质询无四归宿 → 禁止 save_stage 终稿。

    四归宿：data（裁决）/ revise（修正）/ unknown（留白）/ antinomy（背反记录）。
    pending 的高严重度质询 = 未归宿 = 流水线物理上无法绕过审计交付。
    """
    unresolved = [c['id'] for c in session.get('challenges') or []
                  if c.get('status') == 'pending' and c.get('severity') == '高']
    return {'pass': not unresolved, 'unresolved_high': unresolved,
            'pending_total': len(pending_challenges(session))}


def audit_checklist(session):
    """防掉队闸 4·审计员自检清单（输出自评，进附录审计统计）。"""
    r1 = _round1_admitted(session)
    return {
        'readiness': audit_readiness(session),
        'coverage': audit_coverage(session),
        'gate': audit_gate(session),
        'rounds_used': session.get('round_counter', 0),
        'interpretation_present': any(c['type'] in INTERPRETATION_TYPES for c in r1),
    }


def round_summary(session):
    pend = pending_challenges(session)
    return {'round': session['round_counter'],
            'pending': len(pend),
            'pending_ids': [c['id'] for c in pend],
            'settled': len(session['settled']),
            'unknowns': len(session['unknowns']),
            'antinomies': len(session['antinomies'])}


def stats(session):
    total = len(session['challenges'])
    st = {}
    for c in session['challenges']:
        st[c['status']] = st.get(c['status'], 0) + 1
    rejected = sum(len(r['rejected']) for r in session['rounds'])
    return {'rounds': session['round_counter'], 'total': total,
            'settled': st.get('settled', 0), 'revised': st.get('revised', 0),
            'unknown': st.get('unknown', 0), 'antinomy': st.get('antinomy', 0),
            'pending': st.get('pending', 0), 'rejected': rejected}


def surviving_challenges(session):
    """幸存未决质询（喂给'最强反方论点'章节）。"""
    return [c for c in session['challenges'] if c['status'] in ('pending', 'revised')]


def export_for_report(session):
    """导出报告所需：反方论点素材 + 背反记录 + 统计。"""
    return {'surviving': surviving_challenges(session),
            'antinomies': session['antinomies'],
            'unknowns': session['unknowns'],
            'settled_count': len(session['settled']),
            'stats': stats(session)}


def save_session(session, path, scope=None):
    return save_json(session, path, ttl_hours=None,
                     scope=scope or (session.get('subject') or '') + '-socratic',
                     source='socratic_lib')


def load_session(path):
    return load_json(path)
