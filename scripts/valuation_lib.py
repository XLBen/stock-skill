# -*- coding: utf-8 -*-
"""估值/分析确定性算子库（valuation_lib）——"数字由代码算，叙事由 LLM 写"。

铁律：
- 报告中的估值/预测数字必须出自本库算子（或 forecast_lib），禁止 LLM 心算/临时代码。
- 算子按 method_id 注册；方法集由 profile_lib.derive() 推导（画像谓词），本库不做市场硬编码。
- 每个结果带 provenance（使用的 ctx.data_refs 键），供附录数字溯源表自动生成。
- 多源同指标交叉验证：crosscheck() 误差 >1% 输出告警，报告必须说明取舍。

用法：
    from valuation_lib import run_methods, crosscheck, provenance_rows
    ctx = {
        'data': {'price': 10.5, 'shares': 12.5, 'eps_f': 1.10,
                 'peers': [{'name': '可比A', 'pe': 9.0}, {'name': '可比B', 'pe': 11.5}],
                 'pe_hist': [8.2, 9.1, 10.4, 11.8, 9.7, 12.3, 8.9, 10.1]},
        'refs': {'price': {'file': 'data/xx_quotes.json', 'field': 'f2', 'fetched_at': '...'},
                 'eps_f': {'file': 'forecast_xx.json', 'field': 'central.eps', 'fetched_at': '...'}},
    }
    results = run_methods(['relative_peer', 'pe_quantile'], ctx, params={'pe_quantile': {'eps_key': 'eps_f'}})
    rows = provenance_rows(results)
"""
import math

TOL = 0.01


def _need(ctx, key):
    data = ctx.get('data', {})
    if key not in data or data[key] is None:
        raise KeyError('ctx.data 缺少 %s（请在抓取后传入）' % key)
    return data[key]


def _require(params, key, hint):
    """金融参数禁止硬编码默认值：调用方必须显式给出（依据写入报告假设表）。"""
    if params.get(key) is None:
        raise ValueError('缺少参数 %s：%s（禁止使用硬编码默认值）' % (key, hint))
    return params[key]


def _num_list(xs):
    return [float(x) for x in xs if x is not None]


def _pctile(sorted_xs, q):
    if not sorted_xs:
        raise ValueError('空序列')
    if len(sorted_xs) == 1:
        return float(sorted_xs[0])
    pos = q * (len(sorted_xs) - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, len(sorted_xs) - 1)
    frac = pos - lo
    return sorted_xs[lo] * (1 - frac) + sorted_xs[hi] * frac


def _mk(method_id, name, low, central, high, used, ctx, params=None, flags=None, notes=''):
    low, central, high = float(low), float(central), float(high)
    if not (low <= central <= high):
        low, high = min(low, high, central), max(low, high, central)
    refs = ctx.get('refs', {})
    prov = [dict(refs[k], key=k) for k in used if k in refs]
    return {'method': name, 'method_id': method_id,
            'low': round(low, 4), 'central': round(central, 4), 'high': round(high, 4),
            'provenance': prov, 'params': params or {},
            'flags': flags or [], 'notes': notes}


# ==================== 相对估值 ====================

def op_pe_quantile(ctx, params):
    """PE/PB 历史分位估值：历史倍数分位带 × EPS 锚。"""
    p = {'series_key': 'pe_hist', 'eps_key': 'eps_ttm', 'q_lo': 0.25, 'q_mid': 0.50, 'q_hi': 0.75}
    p.update(params or {})
    xs = sorted(_num_list(_need(ctx, p['series_key'])))
    eps = _need(ctx, p['eps_key'])
    qlo, qmid, qhi = _pctile(xs, p['q_lo']), _pctile(xs, p['q_mid']), _pctile(xs, p['q_hi'])
    cur = _need(ctx, 'pe_now') if ctx['data'].get('pe_now') is not None else qmid
    return _mk('pe_quantile', 'PE 历史分位', qlo * eps, qmid * eps, qhi * eps,
               [p['series_key'], p['eps_key']], ctx, p,
               notes='当前分位 %.0f%%；锚=%s（%s）' % (
                   100.0 * sum(1 for x in xs if x <= cur) / max(len(xs), 1),
                   p['eps_key'], '预测EPS' if '_f' in p['eps_key'] else 'TTM'))


def op_relative_peer(ctx, params):
    """同业横向对比：可比公司倍数带 × EPS 锚（预测优先）。"""
    p = {'peers_key': 'peers', 'eps_key': 'eps_f', 'metric': 'pe', 'band': (0.25, 0.50, 0.75)}
    p.update(params or {})
    peers = _need(ctx, p['peers_key'])
    eps = _need(ctx, p['eps_key'])
    mults = sorted(float(x[p['metric']]) for x in peers if x.get(p['metric']) is not None)
    if not mults:
        raise ValueError('可比公司缺少 %s 字段' % p['metric'])
    b = p['band']
    lo, mid, hi = _pctile(mults, b[0]), _pctile(mults, b[1]), _pctile(mults, b[2])
    anchor_name = {'pe': 'EPS', 'pb': '每股净资产', 'ps': '每股营收'}.get(
        str(p['metric']).lower(), '每股指标')
    return _mk('relative_peer', '同业可比 %s×%s' % (p['metric'].upper(), anchor_name),
               lo * eps, mid * eps, hi * eps, [p['peers_key'], p['eps_key']], ctx, p,
               notes='可比 n=%d：%s' % (len(mults), '、'.join(str(x.get('name', '?')) for x in peers)))


def op_ev_ebitda(ctx, params):
    """EV/EBITDA：EBITDA×倍数带 −净债务(±少数股东) → 每股。倍数带须按同业/历史分位给出。"""
    p = {'ebitda_key': 'ebitda'}
    p.update(params or {})
    ebitda = _need(ctx, p['ebitda_key'])
    mult_lo = _require(p, 'mult_lo', '倍数带下限按同业可比/历史分位取')
    mult_mid = _require(p, 'mult_mid', '倍数带中枢按同业可比/历史分位取')
    mult_hi = _require(p, 'mult_hi', '倍数带上限按同业可比/历史分位取')
    shares = _need(ctx, 'shares')
    net_debt = float(_need(ctx, 'net_debt')) if ctx['data'].get('net_debt') is not None else 0.0
    minority = float(ctx['data'].get('minority', 0.0)) or 0.0
    ev_lo, ev_hi = ebitda * mult_lo, ebitda * mult_hi
    per = lambda ev: (ev - net_debt - minority) / shares
    return _mk('ev_ebitda', 'EV/EBITDA', per(ev_lo), per(ebitda * mult_mid), per(ev_hi),
               [p['ebitda_key'], 'shares'], ctx, p,
               notes='EV=EBITDA×%s~%s；净债务 %.1f' % (mult_lo, mult_hi, net_debt))


def op_sotp(ctx, params):
    """SOTP 分部估值：Σ(分部指标×分部倍数带) − 净债务 → 每股。"""
    parts = _need(ctx, 'sotp_parts')
    shares = _need(ctx, 'shares')
    net_debt = float(_need(ctx, 'net_debt')) if ctx['data'].get('net_debt') is not None else 0.0
    lo = hi = mid = 0.0
    for part in parts:
        v = float(part['metric'])
        lo += v * part['mult_lo']
        mid += v * part['mult_mid']
        hi += v * part['mult_hi']
    per = lambda ev: (ev - net_debt) / shares
    return _mk('sotp', 'SOTP 分部估值', per(lo), per(mid), per(hi),
               ['sotp_parts', 'shares'], ctx, {'parts': len(parts)},
               notes='分部 n=%d，扣净债务 %.1f' % (len(parts), net_debt))


# ==================== 现金流折现 ====================

def _dcf_one(fcfs, wacc, g, net_debt, shares):
    pv = 0.0
    for i, f in enumerate(fcfs, start=1):
        pv += f / ((1 + wacc) ** i)
    terminal = fcfs[-1] * (1 + g) / (wacc - g)
    pv += terminal / ((1 + wacc) ** len(fcfs))
    return (pv - net_debt) / shares


def op_dcf(ctx, params):
    """DCF：FCF 序列（建议来自 forecast_lib）+ WACC 区间 + 永续增长 → 每股 + 敏感性。

    WACC/永续增长 g 禁止默认值：WACC 按 Damodaran 参数锚（method_signals）调整，
    g 按长期名义增速给依据，均写入报告假设表。
    """
    p = {'fcf_key': 'fcf_f', 'sens': True}
    p.update(params or {})
    wacc = _require(p, 'wacc', 'WACC 区间(低,中,高)按 method_signals Damodaran 锚 + 公司风险调整')
    g = _require(p, 'g', '永续增长率按长期名义增速给依据（历史/官方目标）')
    fcfs = _num_list(_need(ctx, p['fcf_key']))
    shares = _need(ctx, 'shares')
    net_debt = float(_need(ctx, 'net_debt')) if ctx['data'].get('net_debt') is not None else 0.0
    wl, wm, wh = wacc
    lo = _dcf_one(fcfs, wh, g, net_debt, shares)
    mid = _dcf_one(fcfs, wm, g, net_debt, shares)
    hi = _dcf_one(fcfs, wl, g, net_debt, shares)
    sens = []
    if p['sens']:
        for w in (wl, wm, wh):
            row = []
            for gg in (g - 0.005, g, g + 0.005):
                row.append(round(_dcf_one(fcfs, w, gg, net_debt, shares), 2))
            sens.append({'wacc': round(w, 4), 'values_by_g': row})
    return _mk('dcf', 'DCF 现金流贴现', lo, mid, hi,
               [p['fcf_key'], 'shares'], ctx, {'n_years': len(fcfs), 'wacc': wacc, 'g': g},
               notes='预测期 %d 年；WACC %s~%s；永续 g=%.1f%%' % (
                   len(fcfs), wl, wh, g * 100) + ('；敏感性见 params.sens' if p['sens'] else ''))


def op_ddm(ctx, params):
    """DDM/股息估值：每股股利 ÷ 目标股息率带（按风险补偿定档并给依据）。"""
    p = {'dps_key': 'dps_f'}
    p.update(params or {})
    dps = _need(ctx, p['dps_key'])
    y_lo = _require(p, 'yield_lo', '目标股息率上限按风险补偿定档（低风险低收益率）')
    y_mid = _require(p, 'yield_mid', '目标股息率中枢（可比股息率/债券利差锚）')
    y_hi = _require(p, 'yield_hi', '目标股息率下限（风险补偿）')
    return _mk('ddm', 'DDM 股息估值', dps / y_lo, dps / y_mid, dps / y_hi,
               [p['dps_key']], ctx, p, notes='目标股息率 %.1f%%~%.1f%%' % (y_lo * 100, y_hi * 100))


def op_cap_rate(ctx, params):
    """资本化率估值：NOI（建议来自 forecast_lib.rental）÷ cap rate 带（取值给依据）。"""
    p = {'noi_key': 'noi_f'}
    p.update(params or {})
    noi = _need(ctx, p['noi_key'])
    c_lo = _require(p, 'cap_lo', 'cap rate 上限（保守，可比成交/债券利差锚）')
    c_mid = _require(p, 'cap_mid', 'cap rate 中枢（可比成交给依据）')
    c_hi = _require(p, 'cap_hi', 'cap rate 下限（乐观，可比成交给依据）')
    return _mk('cap_rate', '资本化率估值', noi / c_lo, noi / c_mid, noi / c_hi,
               [p['noi_key']], ctx, p, notes='cap rate %.1f%%~%.1f%%' % (c_lo * 100, c_hi * 100))


# ==================== 周期方法 ====================

def op_cycle_mean(ctx, params):
    """周期平均盈利法：完整周期平均净利 × 正常化 PE → 每股（正常化 PE 给依据）。"""
    p = {'earn_key': 'cycle_earnings'}
    p.update(params or {})
    pe_mid = _require(p, 'pe_mid', '正常化 PE 按该行业周期中枢给依据')
    pe_lo = _require(p, 'pe_lo', 'PE 带下限')
    pe_hi = _require(p, 'pe_hi', 'PE 带上限')
    earns = _num_list(_need(ctx, p['earn_key']))
    shares = _need(ctx, 'shares')
    avg = sum(earns) / len(earns)
    lo = avg * pe_lo / shares
    hi = avg * pe_hi / shares
    return _mk('cycle_mean', '周期平均盈利法', lo, avg * pe_mid / shares, hi,
               [p['earn_key'], 'shares'], ctx,
               {'n_years': len(earns), 'avg_profit': round(avg, 4)},
               notes='周期样本 n=%d，平均净利 %.2f' % (len(earns), avg))


def op_replacement_cost(ctx, params):
    """重置成本法：产能×单位成本带（单位成本按当期行情/公告给依据）。"""
    p = {'units_key': 'capacity_units'}
    p.update(params or {})
    units = float(_need(ctx, p['units_key']))
    c_lo = _require(p, 'cost_lo', '单位重置成本下限（当期行情/公告/在建工程口径）')
    c_mid = _require(p, 'cost_mid', '单位重置成本中枢')
    c_hi = _require(p, 'cost_hi', '单位重置成本上限')
    shares = _need(ctx, 'shares')
    lo, hi = units * c_lo, units * c_hi
    return _mk('replacement_cost', '重置成本法', lo / shares, units * c_mid / shares, hi / shares,
               [p['units_key'], 'shares'], ctx, p)


def op_scenario_price(ctx, params):
    """情景价格法：多情景（量×(价-成本) 或直接净利）加权 → 每股。"""
    scs = _need(ctx, 'scenarios_fin')
    shares = _need(ctx, 'shares')
    lo = min(float(s['value']) for s in scs)
    hi = max(float(s['value']) for s in scs)
    weighted = sum(float(s['value']) * float(s.get('prob', 1.0 / len(scs))) for s in scs)
    return _mk('scenario_price', '情景价格法（加权）', lo / shares, weighted / shares, hi / shares,
               ['scenarios_fin', 'shares'], ctx,
               {'scenarios': [{'name': s.get('name', '?'), 'prob': s.get('prob')} for s in scs]},
               notes='情景 n=%d' % len(scs))


# ==================== 资产方法 ====================

def op_price_index(ctx, params):
    """价格指数化：成交记录 → 指数与区间统计（起点=100）。"""
    p = {'rec_key': 'trade_records', 'date_field': 'date', 'price_field': 'price'}
    p.update(params or {})
    recs = _need(ctx, p['rec_key'])
    recs = sorted(recs, key=lambda r: str(r.get(p['date_field'], '')))
    prices = _num_list([r.get(p['price_field']) for r in recs])
    if not prices:
        raise ValueError('成交记录为空')
    base = prices[0]
    idx = [round(x / base * 100, 2) for x in prices]
    return _mk('price_index', '价格指数化（统计描述）',
               _pctile(sorted(idx), 0.25), _pctile(sorted(idx), 0.50), _pctile(sorted(idx), 0.75),
               [p['rec_key']], ctx, {'n': len(prices), 'first': idx[0], 'last': idx[-1]},
               notes='样本 n=%d；指数 %s→%s；本方法为区间统计参考' % (len(prices), idx[0], idx[-1]))


def op_scarcity_premium(ctx, params):
    """稀缺/限量溢价：替代基准价 ×(1+溢价带)。溢价带须给依据（历史成交溢价分布）。"""
    p = {'base_key': 'replacement_base_price'}
    p.update(params or {})
    base = float(_need(ctx, p['base_key']))
    prem_lo = _require(p, 'prem_lo', '溢价带下限按历史成交溢价分布给依据')
    prem_mid = _require(p, 'prem_mid', '溢价带中枢（历史分布）')
    prem_hi = _require(p, 'prem_hi', '溢价带上限（历史分布）')
    return _mk('scarcity_premium', '稀缺溢价模型',
               base * (1 + prem_lo), base * (1 + prem_mid), base * (1 + prem_hi),
               [p['base_key']], ctx, p,
               notes='溢价带 %.0f%%~%.0f%%（依据须在报告假设表给出）' % (prem_lo * 100, prem_hi * 100))


def op_nvt_mvrv(ctx, params):
    """链上估值：NVT/MVRV vs 历史带 → 隐含区间（历史带须取自当期链上数据）。"""
    p = {'mcap_key': 'market_cap', 'vol_key': 'onchain_volume', 'rc_key': 'realized_cap'}
    p.update(params or {})
    nvt_band = _require(p, 'nvt_band', 'NVT 历史带(低,中,高)按当期历史分位统计')
    mcap = float(_need(ctx, p['mcap_key']))
    vol = float(_need(ctx, p['vol_key']))
    nvt_now = mcap / vol if vol else None
    mvrv_now = None
    if ctx['data'].get(p['rc_key']) is not None:
        mvrv_now = round(mcap / float(ctx['data'][p['rc_key']]), 2)
    lo = mcap / nvt_band[2]
    mid = mcap / nvt_band[1]
    hi = mcap / nvt_band[0]
    return _mk('nvt_mvrv', '链上估值 NVT/MVRV', lo, mid, hi,
               [p['mcap_key'], p['vol_key']], ctx,
               {'nvt_now': round(nvt_now, 2) if nvt_now else None, 'mvrv_now': mvrv_now,
                'nvt_band': nvt_band},
               notes='当前 NVT≈%s；区间=市值/NVT 带隐含（带取自历史分位）' % (
                   round(nvt_now, 1) if nvt_now else 'NA'))


# ==================== 固收/跨市场/财报 ====================

def op_yield_curve(ctx, params):
    """收益率曲线与利差：关键期限利差 + 利率敏感性。"""
    rates = _need(ctx, 'spot_rates')
    def r(t):
        return float(rates[t])
    spread_10y_2y = r('10y') - r('2y')
    sens = {'+50bp_10y': round(r('10y') + 0.005, 4), '+100bp_10y': round(r('10y') + 0.01, 4)}
    return _mk('yield_curve', '收益率曲线利差', spread_10y_2y - 0.005, spread_10y_2y, spread_10y_2y + 0.005,
               ['spot_rates'], ctx, {'spread_10y2y': round(spread_10y_2y, 4), 'sens': sens},
               notes='10y-2y=%.2f%%；敏感性见 params' % (spread_10y_2y * 100))


def op_dividend_spread(ctx, params):
    """股息率-利率利差：当前利差 + ±50/100bp 压力。"""
    dy = float(_need(ctx, 'div_yield'))
    rf = float(_need(ctx, 'rf_rate'))
    spread = dy - rf
    stress = {'-100bp_rf': round(spread + 0.01, 4), '+100bp_rf': round(spread - 0.01, 4)}
    return _mk('dividend_spread', '股息率-利差', spread - 0.01, spread, spread + 0.01,
               ['div_yield', 'rf_rate'], ctx, {'spread': round(spread, 4), 'stress': stress},
               notes='当前利差 %.2f%%；压力 ±100bp' % (spread * 100))


def op_ah_premium(ctx, params):
    """AH 溢价：A/H 价格比 + 历史分位（若给历史）。汇率取自抓取数据。"""
    a = float(_need(ctx, 'a_price'))
    h = float(_need(ctx, 'h_price'))
    fx = float(_need(ctx, 'hkd_cny'))
    prem = a / (h * fx) - 1
    hist = _num_list(ctx['data'].get('ah_prem_hist', []) or [])
    note = '溢价率 %.1f%%' % (prem * 100)
    if hist:
        s = sorted(hist)
        note += '；历史分位 %.0f%%' % (100.0 * sum(1 for x in s if x <= prem) / len(s))
    return _mk('ah_premium', 'AH 溢价分析', prem - 0.1, prem, prem + 0.1,
               ['a_price', 'h_price'], ctx, {'premium': round(prem, 4)}, notes=note)


def op_ab_discount(ctx, params):
    """AB 股折价：1 - B×汇率/A。汇率取自抓取数据。"""
    a = float(_need(ctx, 'a_price'))
    b = float(_need(ctx, 'b_price'))
    fx = float(_need(ctx, 'usd_cny'))
    disc = 1 - (b * fx) / a
    return _mk('ab_discount', 'AB 股折价', disc - 0.05, disc, disc + 0.05,
               ['a_price', 'b_price'], ctx, {'discount': round(disc, 4)},
               notes='折价率 %.1f%%' % (disc * 100))


def op_goodwill_analysis(ctx, params):
    """商誉/减值核查：测试余量 + 触发阈值 + 对净资产/PB 冲击。"""
    gw = float(_need(ctx, 'goodwill'))
    rec = float(_need(ctx, 'recoverable'))
    na = float(_need(ctx, 'net_assets'))
    margin = rec - gw
    trigger_pct = (1 - rec / gw) * 100 if gw else None
    impact = {'net_assets_after': round(na - gw, 4),
              'write_down_pct_on_na': round(gw / na * 100, 2) if na else None}
    return _mk('goodwill_analysis', '商誉减值核查', 0, margin, max(margin, 0) * 2,
               ['goodwill', 'recoverable'], ctx,
               {'margin': round(margin, 4), 'trigger_pct': round(trigger_pct, 2) if trigger_pct is not None else None,
                'impact': impact},
               notes='可收回金额再降 %.1f%% 触发减值；全额减值将侵蚀净资产 %.1f%%' % (
                   trigger_pct or 0, impact['write_down_pct_on_na'] or 0))


# ==================== 统计兜底/论证辅助 ====================

def op_stats_baseline(ctx, params):
    """统计兜底：价格序列分布/波动/回撤（无业界惯例时）。"""
    p = {'price_key': 'price_hist'}
    p.update(params or {})
    xs = _num_list(_need(ctx, p['price_key']))
    if len(xs) < 2:
        raise ValueError('价格序列过短')
    rets = [(xs[i] / xs[i - 1] - 1) for i in range(1, len(xs)) if xs[i - 1]]
    mean = sum(rets) / len(rets)
    vol = math.sqrt(sum((r - mean) ** 2 for r in rets) / len(rets)) if len(rets) > 1 else 0.0
    peak, mdd = xs[0], 0.0
    for x in xs:
        peak = max(peak, x)
        mdd = min(mdd, x / peak - 1)
    return _mk('stats_baseline', '统计描述（波动/回撤）',
               _pctile(sorted(xs), 0.25), _pctile(sorted(xs), 0.50), _pctile(sorted(xs), 0.75),
               [p['price_key']], ctx, {'period_ret': round(xs[-1] / xs[0] - 1, 4) if xs[0] else None,
                                       'vol_per_period': round(vol, 4), 'max_drawdown': round(mdd, 4)},
               flags=['统计性描述'],
               notes='统计性描述，无业界惯例；波动 %.2f%%、最大回撤 %.1f%%' % (vol * 100, mdd * 100))


def historical_analog_stats(cases):
    """历史类比结局统计：cases=[{name, duration_m, drawdown, recovery_m}] → 分布。"""
    def col(k):
        return _num_list([c.get(k) for c in cases])
    out = {'n': len(cases)}
    for k in ('duration_m', 'drawdown', 'recovery_m'):
        xs = sorted(col(k))
        if xs:
            out[k] = {'min': xs[0], 'median': _pctile(xs, 0.5), 'max': xs[-1]}
    return out


def flip_point(fn, target, lo, hi, tol=1e-4, max_iter=60):
    """反向压力：求使 fn(x)=target 的 x（单调函数二分）。
    例如结论区间 low>现价 才看多，问"盈利降到多少翻车"→ 解 EPS。"""
    flo, fhi = fn(lo) - target, fn(hi) - target
    if flo * fhi > 0:
        return None
    for _ in range(max_iter):
        mid = (lo + hi) / 2.0
        fm = fn(mid) - target
        if abs(fm) < tol:
            return round(mid, 6)
        if flo * fm <= 0:
            hi, fhi = mid, fm
        else:
            lo, flo = mid, fm
    return round((lo + hi) / 2.0, 6)


# ==================== 注册表与调度 ====================

OPERATORS = {
    'pe_quantile': op_pe_quantile,
    'relative_peer': op_relative_peer,
    'ev_ebitda': op_ev_ebitda,
    'sotp': op_sotp,
    'dcf': op_dcf,
    'ddm': op_ddm,
    'cap_rate': op_cap_rate,
    'cycle_mean': op_cycle_mean,
    'replacement_cost': op_replacement_cost,
    'scenario_price': op_scenario_price,
    'price_index': op_price_index,
    'scarcity_premium': op_scarcity_premium,
    'nvt_mvrv': op_nvt_mvrv,
    'yield_curve': op_yield_curve,
    'dividend_spread': op_dividend_spread,
    'ah_premium': op_ah_premium,
    'ab_discount': op_ab_discount,
    'goodwill_analysis': op_goodwill_analysis,
    'stats_baseline': op_stats_baseline,
}

NARRATIVE_ONLY = {'bull_bear', 'sector_screen', 'index_fund_screen',
                  'historical_analog', 'probability_with_evidence', 'reverse_stress'}


def run_method(method_id, ctx, params=None):
    if method_id not in OPERATORS:
        raise KeyError('未知算子: %s（可用: %s）' % (method_id, ', '.join(sorted(OPERATORS))))
    return OPERATORS[method_id](ctx, params or {})


def run_methods(method_ids, ctx, params_map=None):
    """批量运行（跳过 ctx 数据不足的方法并记录 skipped）。"""
    params_map = params_map or {}
    results, skipped = [], []
    for mid in method_ids:
        if mid in NARRATIVE_ONLY:
            skipped.append({'method': mid, 'reason': '论证/筛选类方法，非数值算子'})
            continue
        try:
            results.append(run_method(mid, ctx, params_map.get(mid)))
        except (KeyError, ValueError) as e:
            skipped.append({'method': mid, 'reason': str(e)})
    return results, skipped


def run_derived(derive_result, ctx, params_map=None):
    """直接吃 profile_lib.derive() 输出：只跑推导方法集内、ctx 数据就绪的算子。"""
    ids = [m['id'] for m in derive_result.get('methods', [])]
    return run_methods(ids, ctx, params_map)


def weighted_synthesis(results, weights, label='估值合成'):
    """多方法加权合成（确定性计算——最后一步也不许 LLM 手算）。

    results: run_methods/run_derived 输出（每条含 low/central/high）
    weights: {method_id: 权重}（须给理由，写入报告；缺失方法权重 0）
    输出：加权中枢/加权区间/包络区间/两两重叠率（喂 dispute 检测旁注）。
    """
    if not results:
        raise ValueError('results 为空，无法合成')
    ws = {str(k): float(v) for k, v in (weights or {}).items()}
    picked = []
    for r in results:
        w = ws.get(r.get('method_id'), 0.0)
        if w > 0:
            picked.append((r, w))
    if not picked:
        raise ValueError('全部方法权重为 0，无法合成（权重须给理由）')
    total = sum(w for _, w in picked)
    central = sum(r['central'] * w for r, w in picked) / total
    low = sum(r['low'] * w for r, w in picked) / total
    high = sum(r['high'] * w for r, w in picked) / total
    overlap_pairs = total_pairs = 0
    for i in range(len(picked)):
        for j in range(i + 1, len(picked)):
            total_pairs += 1
            lo = max(picked[i][0]['low'], picked[j][0]['low'])
            hi = min(picked[i][0]['high'], picked[j][0]['high'])
            if hi >= lo:
                overlap_pairs += 1
    return {'label': label,
            'weighted_central': round(central, 4),
            'weighted_low': round(low, 4), 'weighted_high': round(high, 4),
            'envelope_low': round(min(r['low'] for r, _ in picked), 4),
            'envelope_high': round(max(r['high'] for r, _ in picked), 4),
            'weights': {r['method_id']: round(w / total, 4) for r, w in picked},
            'overlap_ratio': round(overlap_pairs / total_pairs, 4) if total_pairs else None,
            'methods_used': [r['method_id'] for r, _ in picked]}


def crosscheck(values, tol=TOL, metric=''):
    """多源交叉验证：同名指标多来源误差 >tol → 告警（报告必须说明取舍）。"""
    vals = {k: float(v) for k, v in values.items() if v is not None}
    if len(vals) < 2:
        return {'metric': metric, 'ok': True, 'sources': vals, 'warnings': []}
    xs = list(vals.values())
    lo, hi = min(xs), max(xs)
    base = max(abs(x) for x in xs) or 1.0
    rel = (hi - lo) / abs(base)
    warnings = []
    if rel > tol:
        warnings.append('指标%s多源差异 %.2f%% > %.0f%%：%s' % (
            ('[%s]' % metric) if metric else '', rel * 100, tol * 100,
            '、'.join('%s=%.4g' % kv for kv in vals.items())))
    return {'metric': metric, 'ok': not warnings, 'spread_rel': round(rel, 6),
            'sources': vals, 'warnings': warnings}


def provenance_rows(results):
    """估值结果 → 附录数字溯源表行（方法|关键值|来源文件|字段|抓取时间）。"""
    rows = []
    for r in results:
        for pv in r.get('provenance', []):
            rows.append([r['method'],
                         '%.4g~%.4g（中 %.4g）' % (r['low'], r['high'], r['central']),
                         pv.get('file', ''), pv.get('field', ''), pv.get('fetched_at', '')])
        if not r.get('provenance'):
            rows.append([r['method'], '%.4g~%.4g（中 %.4g）' % (r['low'], r['high'], r['central']),
                         '（未登记来源）', '', ''])
    return rows
