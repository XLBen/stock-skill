# -*- coding: utf-8 -*-
"""分析技法注册表引擎（technique_lib）——技法按需激活 + 注册表自动扩充。

设计：技法不全部使用。编排器每到挂点调 recommend() 拿候选（谓词命中+理由），
自主决定激活哪些（每挂点 ≤3，必填理由记 flow_log technique_activated 事件）。
注册表无合适方法论时走 propose_auto() 自动扩充（auto 区，证据门槛同 usage_probe）。

来源优先级（写进每个条目 sources）：机构方法论 > 教材·论文 > GitHub·业界实践。

用法：
    import technique_lib as tcl
    cands = tcl.recommend(profile, stage='预测前', flow_level='full')
    tcl.activate(flow_log, 'premortem', reason='full 级强制')
    tcl.propose_auto({'id': 'x', 'name': 'X', 'stage': '风险', 'trigger': '...',
                      'protocol': '...', 'applies': 'true',
                      'sources': [{'tier': '教材·论文', 'cite': '...'}]})
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from profile_lib import eval_pred  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TECHNIQUES_PATH = os.path.join(os.path.dirname(HERE), 'reference', 'library', 'techniques.json')

STAGES = ('预测前', '假设校验', '分歧', '情景', '财务质量', '风险', '催化剂',
          '仓位', '复盘', '数据质量', '行业驱动')
TIERS = ('机构方法论', '教材·论文', 'GitHub·业界实践')
AUTO_MAX = 20
ACTIVATE_PER_STAGE = 3

_DUMMY_PROFILE = {'cf': '有', 'disc': '有', 'supply': '无限', 'hold_cost': 0,
                  'liq': '高', 'beh': '均值回归', 'tplus': True, 'short': True,
                  'min_unit': 0, 'data': ['kline'], 'inv': '投资'}


def load_techniques(path=None):
    with open(path or TECHNIQUES_PATH, 'r', encoding='utf-8') as f:
        import json
        d = json.load(f)
    return {'core': d.get('core', []), 'auto': d.get('auto', [])}


def _hit(entry, profile, blueprint_id, flow_level):
    if entry.get('stage') not in STAGES:
        return None
    if not eval_pred(entry.get('applies'), profile):
        return None
    bps = entry.get('blueprints') or []
    if bps and blueprint_id and blueprint_id not in bps:
        return None
    always = entry.get('always_on') or []
    forced = bool(flow_level and flow_level in always)
    return {'id': entry['id'], 'name': entry.get('name', entry['id']),
            'stage': entry['stage'], 'trigger': entry.get('trigger', ''),
            'protocol': entry.get('protocol', ''),
            'always_on': forced, 'origin': entry.get('origin', 'core'),
            'sources': entry.get('sources', []),
            'hit_reason': '谓词 %s 命中%s%s' % (
                entry.get('applies', 'true'),
                ('，蓝图 %s 匹配' % blueprint_id) if bps else '',
                '，%s 级强制' % flow_level if forced else '')}


def recommend(profile, stage, blueprint_id=None, flow_level=None, path=None):
    """某挂点的候选技法（core+auto 合并，谓词/蓝图/流程级别过滤）。"""
    if stage not in STAGES:
        raise ValueError('stage 必须是 %s' % (STAGES,))
    reg = load_techniques(path)
    out = []
    for entry in reg['core'] + reg['auto']:
        h = _hit(entry, profile, blueprint_id, flow_level)
        if h:
            out.append(h)
    return out


def get(technique_id):
    reg = load_techniques()
    for entry in reg['core'] + reg['auto']:
        if entry['id'] == technique_id:
            return entry
    return None


def activate(flow_log, technique_id, reason, stage=None):
    """激活登记（必填理由）。flow_log 为 FlowLog 实例；同一挂点 ≤3 次激活。"""
    if not (reason or '').strip():
        raise ValueError('激活技法必须给理由（flow_log 可审计）')
    t = get(technique_id)
    if t is None:
        raise KeyError('技法不存在: %s' % technique_id)
    if flow_log is not None:
        used = [e for e in flow_log.events
                if e.get('event') == 'technique_activated' and e.get('stage') == (stage or t['stage'])]
        if len(used) >= ACTIVATE_PER_STAGE:
            raise ValueError('挂点 %s 激活数已达上限 %d（防技法泛滥）'
                             % (stage or t['stage'], ACTIVATE_PER_STAGE))
        flow_log.event('technique_activated', technique=technique_id,
                       stage=stage or t['stage'], reason=reason,
                       origin=t.get('origin', 'core'))
    return t


def validate_proposal(proposal):
    """auto 扩充提案校验：字段齐全、stage 合法、id 唯一、来源达证据门槛。"""
    for k in ('id', 'name', 'stage', 'trigger', 'protocol'):
        v = proposal.get(k)
        if v is None or (isinstance(v, str) and not v.strip()):
            raise ValueError('提案缺字段 %s' % k)
    if proposal['stage'] not in STAGES:
        raise ValueError('stage 非法: %r（可用 %s）' % (proposal['stage'], STAGES))
    if get(proposal['id']) is not None:
        raise ValueError('技法 id 已存在: %s' % proposal['id'])
    srcs = proposal.get('sources') or []
    if not srcs:
        raise ValueError('自动扩充必须带来源（证据门槛）：至少 1 条，'
                         '优先级 机构方法论 > 教材·论文 > GitHub·业界实践')
    for s in srcs:
        if s.get('tier') not in TIERS or not (s.get('cite') or '').strip():
            raise ValueError('来源需 {tier, cite}，tier ∈ %s: %r' % (TIERS, s))
    eval_pred(proposal.get('applies'), _DUMMY_PROFILE)
    return True


def propose_auto(proposal, path=None, flow_log=None):
    """注册表自动扩充：过证据门槛 → 写入 auto 区（上限 %d），报告附录标注。"""
    validate_proposal(proposal)
    import json
    p = path or TECHNIQUES_PATH
    with open(p, 'r', encoding='utf-8') as f:
        d = json.load(f)
    if len(d.get('auto', [])) >= AUTO_MAX:
        raise ValueError('auto 区已达上限 %d（先人工评审晋升 core 或清理）' % AUTO_MAX)
    entry = dict(proposal)
    entry.update({'origin': 'auto', 'added_at':
                  datetime.datetime.now().isoformat(timespec='seconds'),
                  'always_on': proposal.get('always_on') or []})
    d.setdefault('auto', []).append(entry)
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    if flow_log is not None:
        flow_log.event('technique_auto_added', technique=entry['id'],
                       stage=entry['stage'], sources=entry['sources'])
    return entry


def techniques_used(flow_log):
    """从 flow_log 提取本报告激活的技法（附录'新引入技法'标注用）。"""
    out = []
    for e in flow_log.events:
        if e.get('event') == 'technique_activated':
            out.append({'technique': e.get('technique'), 'stage': e.get('stage'),
                        'reason': e.get('reason'), 'origin': e.get('origin')})
    return out
