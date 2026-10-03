# -*- coding: utf-8 -*-
"""盈利预测结构化模型（forecast_lib）：报告的"盈利预测"心脏。

三种范式（与蓝图对应）：
- equity  分业务量价/增速 → 毛利率/费用率 → 3年净利/EPS/ROE（equity_deep_8ch 第四章）
- rental  租金/出租率/成本率 → 3年NOI（rental_asset 第四节）
- balance 供需平衡表（asset_research 第三节，供给增量 vs 需求代理）

铁律：
- 每项假设必须带 {value, basis, tag, probability}，tag ∈ [实证]/[推断]/[观点]，
  缺 basis/tag 视为"裸（估）"，validate_forecast 直接报错。
- 预测数字全部由本库计算，LLM 禁止手算（报告数字可回查 forecast_*.json）。
- 结果用 fetch_lib.save_json 落盘（ttl_hours 建议 168）。

用法：
    from forecast_lib import Assumption, build_equity_forecast, validate_forecast, save_forecast
    a_g = Assumption(0.12, basis='行业增速 8% + 份额提升（近3年市占 5%→7%）', tag='[推断]', probability=0.6)
    fc = build_equity_forecast(
        years=[2026, 2027, 2028],
        segments=[{'name': '主业', 'method': 'growth', 'base': 100.0, 'assumptions': {'growth': a_g}}],
        gross_margin=Assumption(0.32, basis='近5年 30%~34% 区间中枢', tag='[实证]', probability=0.7),
        opex_ratio=Assumption(0.12, basis='费用率历史稳定 11%~13%', tag='[实证]', probability=0.7),
        tax_rate=Assumption(0.15, basis='高新企业 15% 税率（年报披露）', tag='[实证]', probability=0.9),
        shares=12.5, equity_base=90.0, minority_ratio=0.02,
        scenarios={'保守': 0.25, '中性': 0.5, '乐观': 0.25})
    validate_forecast(fc); save_forecast(fc, 'forecast_xx.json', scope='600754')
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_lib import save_json  # noqa: E402

TAGS = ('[实证]', '[推断]', '[观点]')


class Assumption(object):
    """带证据链的假设值。value 可为数值或 (low, high) 区间。

    base_rate_ref：基础比率外部视角锚（技法 base_rate_outside_view）——
    增长/改善类 [推断] 假设必须给参考类依据（行业历史分布/同类达成率，
    指向数据文件或引用）；缺失时 _enforce_base_rate 自动降级 [观点]。
    """

    def __init__(self, value, basis='', tag='[观点]', probability=None,
                 base_rate_ref=None):
        if tag not in TAGS:
            raise ValueError('tag 必须是 %s 之一，得到 %s' % (TAGS, tag))
        if not basis:
            raise ValueError('假设缺少 basis（依据来源），禁止裸（估）')
        self.value = value
        self.basis = basis
        self.tag = tag
        self.probability = probability
        self.base_rate_ref = base_rate_ref

    def to_dict(self):
        return {'value': self.value, 'basis': self.basis, 'tag': self.tag,
                'probability': self.probability,
                'base_rate_ref': self.base_rate_ref}

    def point(self):
        """区间取中点，数值直接返回。"""
        if isinstance(self.value, (tuple, list)):
            return sum(self.value) / 2.0
        return float(self.value)


GROWTH_KEYS = ('growth', 'volume', 'price', 'rent_growth', 'supply_delta',
               'demand_proxy', 'price_change')


def _enforce_base_rate(a, label):
    """[推断] 增长类假设缺 base_rate_ref → 降级 [观点]（外部视角铁律）。"""
    if a.tag == '[推断]' and not a.base_rate_ref:
        a.tag = '[观点]'
        a.basis = a.basis + '（缺基础比率依据，由[推断]降级[观点]）'
        return '%s: [推断]假设未给 base_rate_ref，已降级[观点]' % label
    return None


def _scenario_weights(scenarios):
    if not scenarios:
        return {'中性': 1.0}
    total = float(sum(scenarios.values()))
    if total <= 0:
        raise ValueError('情景权重和必须为正')
    return {k: v / total for k, v in scenarios.items()}


def _seg_point_assumption(seg, key):
    a = seg.get('assumptions', {}).get(key)
    if a is None:
        raise ValueError("分业务 '%s' 缺少假设 '%s'" % (seg.get('name', '?'), key))
    if not isinstance(a, Assumption):
        raise ValueError("分业务 '%s' 假设 '%s' 必须是 Assumption 对象" % (seg.get('name', '?'), key))
    return a


def segment_revenue(seg, year_idx):
    """单分业务第 year_idx 年（0 起）营收预测。

    method='growth'  需要 assumptions.growth（逐年复合增速）
    method='volume_price' 需要 volume（量，可逐年列表）与 price（价）
    """
    name = seg.get('name', '?')
    method = seg.get('method', 'growth')
    if method == 'growth':
        g = _seg_point_assumption(seg, 'growth')
        rev = float(seg['base']) * ((1 + g.point()) ** (year_idx + 1))
        return rev
    if method == 'volume_price':
        vol_a = _seg_point_assumption(seg, 'volume')
        pri_a = _seg_point_assumption(seg, 'price')
        vol, pri = vol_a.value, pri_a.value
        if isinstance(vol, (list, tuple)):
            if year_idx >= len(vol):
                raise ValueError("分业务 '%s' volume 序列长度不足" % name)
            vol = vol[year_idx]
        if isinstance(pri, (list, tuple)):
            if year_idx >= len(pri):
                raise ValueError("分业务 '%s' price 序列长度不足" % name)
            pri = pri[year_idx]
        return float(vol) * float(pri)
    raise ValueError("分业务 '%s' method 未知: %s" % (name, method))


def build_equity_forecast(years, segments, gross_margin, opex_ratio, tax_rate,
                          shares, equity_base, minority_ratio=0.0,
                          other_income_ratio=None, scenarios=None,
                          subject=None):
    """分业务 → 毛利 → 费用 → 归母净利/EPS/ROE 逐年预测。

    years: 预测年列表（如 [2026, 2027, 2028]）
    segments: [{name, method, base, assumptions:{...Assumption}}]（volume_price 无 base）
    gross_margin/opex_ratio/tax_rate: Assumption（比率小数）
    shares: 总股本（亿股）；equity_base: 归母净资产基数（亿元）
    minority_ratio: 少数股东损益占比小数
    other_income_ratio: 其他项目/投资收益占营收比（可 None）
    返回 {kind:'equity', ...} 结构化预测。
    """
    w = _scenario_weights(scenarios)
    downgrades = []
    for s in segments:
        for k, a in s.get('assumptions', {}).items():
            if k in GROWTH_KEYS:
                note = _enforce_base_rate(a, "segment[%s].%s" % (s.get('name'), k))
                if note:
                    downgrades.append(note)
    per_year = []
    for yi, year in enumerate(years):
        revs = {seg['name']: segment_revenue(seg, yi) for seg in segments}
        revenue = sum(revs.values())
        gp = revenue * gross_margin.point()
        opex = revenue * opex_ratio.point()
        other = revenue * other_income_ratio.point() if other_income_ratio else 0.0
        profit_pre = gp - opex + other
        net = profit_pre * (1 - tax_rate.point())
        net_parent = net * (1 - minority_ratio)
        eps = net_parent / float(shares)
        equity = equity_base + sum(y['net_parent'] for y in per_year)
        roe = net_parent / equity if equity else None
        per_year.append({'year': year, 'revenue_by_segment': revs, 'revenue': revenue,
                         'gross_profit': gp, 'opex': opex, 'other': other,
                         'net_profit': net, 'net_parent': net_parent,
                         'eps': eps, 'roe': roe,
                         'equity_end': equity})
    central = per_year[-1]
    return {
        'kind': 'equity', 'subject': subject, 'years': list(years),
        'segments': [{'name': s['name'], 'method': s.get('method', 'growth'),
                      'base': s.get('base'),
                      'assumptions': {k: v.to_dict() for k, v in s.get('assumptions', {}).items()}}
                     for s in segments],
        'global_assumptions': {'gross_margin': gross_margin.to_dict(),
                               'opex_ratio': opex_ratio.to_dict(),
                               'tax_rate': tax_rate.to_dict(),
                               'minority_ratio': minority_ratio,
                               'other_income_ratio': other_income_ratio.to_dict() if other_income_ratio else None},
        'shares': shares, 'equity_base': equity_base,
        'scenario_weights': w,
        'base_rate_downgrades': downgrades,
        'per_year': per_year,
        'central': {'year': central['year'], 'revenue': central['revenue'],
                    'net_parent': central['net_parent'], 'eps': central['eps'],
                    'roe': central['roe']},
    }


def build_rental_forecast(years, gross_rent_base, rent_growth, vacancy_rate,
                          opex_ratio, scenarios=None, subject=None):
    """租金资产 → 3年 NOI 预测（rental_asset 第四节）。

    gross_rent_base: 基年毛租金（亿元/万元，口径自明）
    rent_growth/vacancy_rate/opex_ratio: Assumption
    NOI = 毛租金×(1+增速)^(n) ×(1-空置率) ×(1-运营成本率)
    """
    w = _scenario_weights(scenarios)
    downgrades = []
    for a, label in ((rent_growth, 'rent_growth'), (vacancy_rate, 'vacancy_rate'),
                     (opex_ratio, 'opex_ratio')):
        note = _enforce_base_rate(a, label)
        if note:
            downgrades.append(note)
    per_year = []
    for yi, year in enumerate(years):
        gross = float(gross_rent_base) * ((1 + rent_growth.point()) ** (yi + 1))
        effective = gross * (1 - vacancy_rate.point())
        noi = effective * (1 - opex_ratio.point())
        per_year.append({'year': year, 'gross_rent': gross,
                         'effective_rent': effective, 'noi': noi})
    return {
        'kind': 'rental', 'subject': subject, 'years': list(years),
        'base': gross_rent_base,
        'assumptions': {'rent_growth': rent_growth.to_dict(),
                        'vacancy_rate': vacancy_rate.to_dict(),
                        'opex_ratio': opex_ratio.to_dict()},
        'scenario_weights': w, 'per_year': per_year,
        'base_rate_downgrades': downgrades,
        'central': {'year': per_year[-1]['year'], 'noi': per_year[-1]['noi']},
    }


def build_supply_demand_balance(history, forecast_rows, subject=None):
    """供需平衡表（asset_research 第三节）。

    history: [{year, supply_delta, demand_proxy, price_change}]（供给增量/需求代理/价格变动）
    forecast_rows: [{year, supply_delta: Assumption, demand_proxy: Assumption,
                     price_change: Assumption}] 预测年（假设带证据链）
    """
    hist = [{'year': r['year'], 'supply_delta': r.get('supply_delta'),
             'demand_proxy': r.get('demand_proxy'), 'price_change': r.get('price_change')}
            for r in history]
    downgrades = []
    for r in forecast_rows:
        for k in ('supply_delta', 'demand_proxy', 'price_change'):
            note = _enforce_base_rate(r[k], 'balance[%s].%s' % (r.get('year'), k))
            if note:
                downgrades.append(note)
    fc = [{'year': r['year'],
           'supply_delta': r['supply_delta'].to_dict(),
           'demand_proxy': r['demand_proxy'].to_dict(),
           'price_change': r['price_change'].to_dict()} for r in forecast_rows]
    return {'kind': 'balance', 'subject': subject, 'history': hist,
            'forecast': fc, 'base_rate_downgrades': downgrades}


def validate_forecast(fc):
    """校验：假设证据链完整（basis/tag/probability），数值可计算。缺任何一项即抛错。"""
    problems = []

    def check_assumption(d, path):
        if not isinstance(d, dict):
            problems.append('%s: 不是结构化假设' % path)
            return
        if not d.get('basis'):
            problems.append('%s: 缺 basis（裸（估））' % path)
        if d.get('tag') not in TAGS:
            problems.append('%s: tag 非法 %s' % (path, d.get('tag')))
        if d.get('probability') is None:
            problems.append('%s: 缺 probability' % path)

    kind = fc.get('kind')
    if kind == 'equity':
        for seg in fc.get('segments', []):
            for k, v in seg.get('assumptions', {}).items():
                check_assumption(v, "segment[%s].%s" % (seg.get('name'), k))
        for k, v in fc.get('global_assumptions', {}).items():
            if v is None:
                continue
            if isinstance(v, dict):
                check_assumption(v, 'global.%s' % k)
        if not fc.get('per_year'):
            problems.append('per_year 为空')
    elif kind == 'rental':
        for k, v in fc.get('assumptions', {}).items():
            check_assumption(v, 'rental.%s' % k)
    elif kind == 'balance':
        for row in fc.get('forecast', []):
            for k in ('supply_delta', 'demand_proxy', 'price_change'):
                if isinstance(row.get(k), dict):
                    check_assumption(row[k], 'balance[%s].%s' % (row.get('year'), k))
                else:
                    problems.append('balance[%s].%s: 缺假设' % (row.get('year'), k))
    else:
        problems.append('未知 kind: %s' % kind)
    if problems:
        raise ValueError('预测校验失败: ' + '; '.join(problems))
    return True


def save_forecast(fc, path, scope=None, ttl_hours=168):
    """校验并落盘（复用 fetch_lib 缓存约定）。"""
    validate_forecast(fc)
    return save_json(fc, path, ttl_hours=ttl_hours,
                     scope=scope or (fc.get('subject') or '') + '-forecast',
                     source='forecast_lib')


def scenario_table(fc, low_shift=None, high_shift=None):
    """由中枢与权重生成保守/中性/乐观三档表（供报告引用）。

    档位偏移（low_shift/high_shift）禁止默认值：按核心假设的不确定性/
    历史预测误差分布定，依据写入报告假设表。
    equity 档位 = 中枢净利 ×(1±shift)；rental 档位 = 中枢 NOI ×(1±shift)。
    """
    if low_shift is None or high_shift is None:
        raise ValueError('档位偏移禁止硬编码默认值：low_shift/high_shift 按假设不确定性或'
                         '历史预测误差分布给出（依据写入假设表）')
    w = fc.get('scenario_weights') or {'保守': 0.25, '中性': 0.5, '乐观': 0.25}
    if fc['kind'] == 'equity':
        key, val = 'net_parent', fc['central']['net_parent']
    else:
        key, val = 'noi', fc['central']['noi']
    low, high = val * (1 - low_shift), val * (1 + high_shift)
    weighted = (low * w.get('保守', 0) + val * w.get('中性', 0) + high * w.get('乐观', 0))
    return {'metric': key, '保守': low, '中性': val, '乐观': high,
            'weights': w, 'weighted': weighted}
