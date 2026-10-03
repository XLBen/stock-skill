# -*- coding: utf-8 -*-
"""资产画像引擎与规则库谓词求值（股票分析 skill 核心）。

职责：
1. 资产/对象 8 维属性画像：预设档案（profiles.json）或 8 问画像（profile_from_answers）
2. 谓词求值：方法/数据源/报告蓝图/回测规则库条目均带 applies 谓词
3. derive(profile, report_type, lib)：推导出 {方法集, 源集, 蓝图, 回测, QA}
4. dispute_analysis()：方法分歧检测（正反对比判定，规则见 dispute.json）

画像字段（profile）：
    cf        现金流: 有 | 租金型 | 无
    disc      披露/官方锚: 有 | 无
    supply    供给: 无限 | 稀缺 | 限量
    hold_cost 持有成本: 0=无 1=低 2=高
    liq       流动性: 高 | 中 | 低
    beh       价格行为: 均值回归 | 趋势 | 周期
    tplus     T+1: bool
    short     可做空: bool
    min_unit  最小交易单位: int（0=无限制）
    data      可得数据: [kline, chain, listing, trade, index, research]
    inv       投资/收藏/消费

谓词语法（applies 字段）：
    cf=有 & (disc=有 | data=research)
    data=kline          数组包含
    hold_cost>=1        数值比较
    true / false        字面量
    操作符: = != >= <=  & | ! ( )
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LIB_DIR = os.path.join(os.path.dirname(HERE), 'reference', 'library')

FIELD_RE = r"[a-zA-Z_][a-zA-Z0-9_.]*"
CN_RE = r"[\u4e00-\u9fa5]+"
NUM_RE = r"[0-9]+(?:\.[0-9]+)?"
TOKEN_RE = __import__('re').compile(r'(%s|%s|%s|!=|>=|<=|=|&|\||!|\(|\))' % (FIELD_RE, CN_RE, NUM_RE))

# 8 问画像（需求确认第 1 步，库外对象走此问答）
QUESTIONS = [
    ('cf', '该对象是否产生可预测的经营现金流（租金/股息/盈利）？[有/租金型/无]'),
    ('disc', '是否有财务披露或官方定价锚（财报/指数/监管数据）？[有/无]'),
    ('supply', '供给弹性如何？[无限/稀缺/限量]'),
    ('hold_cost', '持有成本（仓储/维护/融资/税费）？[0=无 1=低 2=高]'),
    ('liq', '流动性（成交活跃度）？[高/中/低]'),
    ('beh', '价格行为特征？[均值回归/趋势/周期]'),
    ('tplus', '是否 T+1（当日买入当日不可卖）？[true/false]'),
    ('short', '是否可做空？[true/false]'),
    ('min_unit', '最小交易单位（股/份，0=无限制）？[数字]'),
    ('data', '可得数据（逗号分隔）：kline,chain,listing,trade,index,research'),
    ('inv', '投资/收藏/消费属性？[投资/收藏/消费]'),
]

_TRUE = ('true', '1', 'yes', '是')
_FALSE = ('false', '0', 'no', '否')


# ==================== 谓词求值 ====================

def _field_get(profile, path):
    cur = profile
    for part in path.split('.'):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def _value(profile, path):
    v = _field_get(profile, path)
    if isinstance(v, list):
        return v
    if isinstance(v, bool):
        return str(v).lower()
    if isinstance(v, (int, float)):
        return v
    if v is None:
        return None
    return str(v)


def _num(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v))
    except (TypeError, ValueError):
        return None


class _Parser(object):
    def __init__(self, toks, profile):
        self.toks = toks
        self.i = 0
        self.profile = profile

    def peek(self):
        return self.toks[self.i] if self.i < len(self.toks) else None

    def next(self):
        t = self.peek()
        self.i += 1
        return t

    def parse_or(self):
        v = self.parse_and()
        while self.peek() == '|':
            self.next()
            r = self.parse_and()
            v = v or r
        return v

    def parse_and(self):
        v = self.parse_not()
        while self.peek() == '&':
            self.next()
            r = self.parse_not()
            v = v and r
        return v

    def parse_not(self):
        if self.peek() == '!':
            self.next()
            return not self.parse_not()
        return self.parse_primary()

    def parse_primary(self):
        t = self.peek()
        if t == '(':
            self.next()
            v = self.parse_or()
            if self.peek() != ')':
                raise ValueError('谓词括号不匹配: %r' % ' '.join(self.toks))
            self.next()
            return v
        if t == 'true':
            self.next()
            return True
        if t == 'false':
            self.next()
            return False
        return self.parse_compare()

    def parse_compare(self):
        field = self.next()
        if field is None:
            raise ValueError('谓词不完整: %r' % ' '.join(self.toks))
        op = self.next()
        if op not in ('=', '!=', '>=', '<='):
            raise ValueError('未知操作符 %r（字段 %s）' % (op, field))
        val_tok = self.next()
        val = _num(val_tok) if _num(val_tok) is not None else val_tok
        cur = _value(self.profile, field)
        if isinstance(cur, list):
            if op in ('=', '!='):
                hit = any(str(x) == str(val) for x in cur)
                return hit if op == '=' else not hit
            raise ValueError('数组字段 %s 仅支持 =/!=' % field)
        if op in ('>=', '<='):
            a, b = _num(cur), _num(val)
            if a is None or b is None:
                raise ValueError('数值比较字段需为数值: %s %s %s' % (field, op, val_tok))
            return a >= b if op == '>=' else a <= b
        if op == '=':
            return cur == val
        return cur != val


def eval_pred(expr, profile):
    """求值谓词表达式。expr 为空/True 恒真。"""
    if expr is None:
        return True
    expr = expr.strip()
    if not expr or expr == 'true':
        return True
    if expr == 'false':
        return False
    toks = [t for t in TOKEN_RE.findall(expr)]
    if not toks:
        return False
    p = _Parser(toks, profile)
    v = p.parse_or()
    if p.i != len(toks):
        raise ValueError('谓词多余 token: %r' % expr)
    return v


# ==================== 画像 ====================

def load_profile(pid):
    """从 profiles.json 加载预设档案。"""
    profs = _load_json('profiles.json')
    for p in profs.get('profiles', []):
        if p.get('id') == pid:
            return p
    raise KeyError('未找到预设档案: %s（可用: %s）' % (pid, ', '.join(x['id'] for x in profs.get('profiles', []))))


def profile_from_answers(answers):
    """8 问画像：answers 为 {字段: 值}，规范化类型。"""
    p = dict(answers)
    for k in ('tplus', 'short'):
        raw = str(p.get(k, '')).strip().lower()
        p[k] = raw in _TRUE
    p['min_unit'] = int(p.get('min_unit') or 0)
    p['hold_cost'] = int(p.get('hold_cost') or 0)
    if isinstance(p.get('data'), str):
        p['data'] = [x.strip() for x in p['data'].split(',') if x.strip()]
    if isinstance(p.get('data'), list) and all(isinstance(x, str) for x in p['data']):
        pass
    return p


# ==================== 规则库 ====================

def _load_json(name):
    path = os.path.join(LIB_DIR, name)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_library():
    """加载全部规则库。"""
    return {
        'methods': _load_json('methods.json').get('methods', []),
        'sources': _load_json('sources.json').get('sources', []),
        'blueprints': _load_json('blueprints.json').get('blueprints', []),
        'backtest': _load_json('backtest.json').get('rules', []),
        'dispute': _load_json('dispute.json'),
    }


def match_items(items, profile):
    """返回 applies 谓词匹配的全部条目 id。"""
    return [it['id'] for it in items if eval_pred(it.get('applies'), profile)]


def derive(profile, report_type, lib=None):
    """推导：画像+报告类型 → 方法集/源集/蓝图/回测规则/QA 项。

    report_type: 深度研究 | 主题量化 | 资产研究 | 策略手册 | 科普 | 决策测算
    """
    lib = lib or load_library()
    methods = [m for m in lib['methods'] if eval_pred(m.get('applies'), profile)]
    sources = [s for s in lib['sources'] if eval_pred(s.get('applies'), profile)]
    backtest = [b for b in lib['backtest'] if eval_pred(b.get('applies'), profile)]
    blueprint = None
    for b in lib['blueprints']:
        if b.get('type') != report_type:
            continue
        if eval_pred(b.get('applies'), profile):
            blueprint = b
            break
    if blueprint is None:
        raise ValueError('报告类型 %s 无匹配蓝图（画像: %s）' % (report_type, profile.get('id', '自定义')))
    return {
        'profile': profile,
        'methods': methods,
        'sources': sources,
        'blueprint': blueprint,
        'backtest': backtest,
        'qa': blueprint.get('qa', []),
    }


# ==================== 方法分歧检测 ====================

def dispute_analysis(results, dispute_cfg):
    """方法分歧检测（正反对比判定）。

    results: [{method, low, high, central, flags: [...]}]
    dispute_cfg 字段：
        threshold            中枢离散度阈值（如 0.20）
        consensus_ratio      区间重叠方法占比（≥ 则视为一致）
        penalty_excluded_ratio  带"失真/慎用"flag 且偏离主流中枢比例 > 该值 → 剔除为牵强
        min_methods          有效方法数下限
        flags                ["失真", "慎用"]
    返回 {trigger, reason, excluded, summary}
    """
    if len(results) < dispute_cfg.get('min_methods', 2):
        return {'trigger': False, 'reason': '方法数不足，不做分歧对比', 'excluded': [], 'summary': results}

    th = dispute_cfg.get('threshold', 0.20)
    cons = dispute_cfg.get('consensus_ratio', 0.60)
    pen = dispute_cfg.get('penalty_excluded_ratio', 0.30)
    flags = dispute_cfg.get('flags', ['失真', '慎用'])

    def central(r):
        return r.get('central') if r.get('central') is not None else (r['low'] + r['high']) / 2.0

    med = sorted(central(r) for r in results)[len(results) // 2]
    excluded = []
    kept = []
    for r in results:
        flagged = any(f in (r.get('flags') or []) for f in flags)
        if flagged and med and abs(central(r) - med) / abs(med) > pen:
            excluded.append(r)
        else:
            kept.append(r)
    if len(kept) < dispute_cfg.get('min_methods', 2):
        return {'trigger': False, 'reason': '剔除失真方法后不足 2 个，不做对比',
                'excluded': excluded, 'summary': kept}

    cents = sorted(central(r) for r in kept)
    med2 = cents[len(cents) // 2]
    disp = (cents[-1] - cents[0]) / abs(med2) if med2 else 0.0
    overlap_pairs = 0
    total_pairs = 0
    for i in range(len(kept)):
        for j in range(i + 1, len(kept)):
            total_pairs += 1
            lo = max(kept[i]['low'], kept[j]['low'])
            hi = min(kept[i]['high'], kept[j]['high'])
            if hi >= lo:
                overlap_pairs += 1
    ovr = overlap_pairs / total_pairs if total_pairs else 1.0

    reason = '中枢离散度 %.1f%%（阈值 %.0f%%），区间重叠比例 %.0f%%' % (disp * 100, th * 100, ovr * 100)
    if ovr >= cons:
        return {'trigger': False, 'reason': '多方法一致：' + reason,
                'excluded': excluded, 'summary': kept}
    if disp <= th:
        return {'trigger': False, 'reason': '分歧不显著：' + reason,
                'excluded': excluded, 'summary': kept}
    if excluded:
        reason += '；已剔除牵强方法: %s' % ', '.join(e['method'] for e in excluded)
    return {'trigger': True, 'reason': reason, 'excluded': excluded, 'summary': kept}


# ==================== ACH 竞争性假设矩阵（技法 ach_matrix） ====================

ACH_SCORES = ('一致', '不一致', '无关')


def ach_matrix(hypotheses, evidence):
    """Analysis of Competing Hypotheses（Heuer 1987/CIA Tradecraft）。

    hypotheses: [str]（互斥读法/方法结论）
    evidence:   [{'desc', 'source', 'scores': {假设: '一致'|'不一致'|'无关'}}]
    排序规则：按"最少不一致"（诊断性优先），而非多数证据——证据可以与多个假设
    一致，只有"不一致"才有区分力。
    返回 {hypotheses, matrix, inconsistency, ranking, diagnostic_evidence}
    """
    if len(hypotheses) < 2:
        raise ValueError('ACH 至少 2 个假设')
    rows = []
    inconsistency = {h: 0 for h in hypotheses}
    for e in evidence or []:
        scores = e.get('scores') or {}
        bad = [h for h in hypotheses if scores.get(h) == '不一致']
        for h in bad:
            inconsistency[h] += 1
        rows.append({'desc': e.get('desc', ''), 'source': e.get('source', ''),
                     'scores': {h: scores.get(h, '无关') for h in hypotheses},
                     'diagnostic': len(bad) >= 1 and len(
                         {scores.get(h, '无关') for h in hypotheses}) > 1})
    ranking = sorted(hypotheses, key=lambda h: inconsistency[h])
    return {'method': 'ACH', 'hypotheses': list(hypotheses), 'matrix': rows,
            'inconsistency': inconsistency, 'ranking': ranking,
            'diagnostic_evidence': [r['desc'] for r in rows if r['diagnostic']],
            'note': '按最少不一致排序（%s）' % ' < '.join(ranking)}


if __name__ == '__main__':
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    lib = load_library()
    for pid in ('a_share_stock', 'real_estate', 'crypto', 'collectible'):
        p = load_profile(pid)
        rtype = {'有': '深度研究', '租金型': '租金资产研究', '无': '资产研究'}[p['cf']]
        d = derive(p, rtype, lib)
        print('== %s (%s)' % (p.get('name'), pid))
        print('   方法: %s' % ', '.join(m['id'] for m in d['methods']))
        print('   源:   %s' % ', '.join(s['id'] for s in d['sources']))
        print('   蓝图: %s' % d['blueprint']['id'])
        print('   回测: %s' % ', '.join(b['id'] for b in d['backtest']) or '无')
