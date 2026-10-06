# -*- coding: utf-8 -*-
"""股票分析 skill 自测脚本：覆盖 scripts/ 全部模块与规则库推导。

用法：python selftest.py [--offline]   （--offline 跳过需要联网的测试）
通过则输出所有 PASS，退出码 0；任何失败输出 FAIL 并退出码 1。

覆盖：
- docx_helpers / chart_helpers / fetch_lib（原有用例保留）
- profile_lib：谓词求值、四类资产推导、手办库外画像、分歧检测三例
- 规则库完整性：JSON 可解析、谓词可求值
- cache_status / check_storage / check_delivery（离线）
- forecast_lib：盈利预测/NOI/裸（估）拦截/情景表
- valuation_lib：算子批量运行/交叉验证/翻车点/溯源行
- review_lib：档案落档/判定/校准率（save_stage 自动落档）
- brief_lib：单波需求书/必填校验/自我批准；technique_lib：推荐/激活/自动扩充
- check_report_depth v2：蓝图必备章/数字溯源抽查
- 联网：Damodaran 抓取、研报列表抓取、研报取证抽样（--offline 跳过）
"""
import json
import os
import sys
import shutil
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import docx_helpers as dh
import chart_helpers as ch
import fetch_lib as fl
import profile_lib as pl
import check_delivery as cd
import cache_status as cs
import check_storage as csg

OFFLINE = '--offline' in sys.argv
TMP = os.path.join(tempfile.gettempdir(), 'opencode', 'skill_selftest')

PASSED = []
FAILED = []


def check(name, fn):
    try:
        fn()
        PASSED.append(name)
        print('PASS  %s' % name)
    except Exception as e:
        FAILED.append((name, e))
        print('FAIL  %s: %s' % (name, e))


def expect(cond, msg):
    if not cond:
        raise AssertionError(msg)


# ==================== docx_helpers ====================

def test_new_document():
    doc = dh.new_document()
    expect(doc.styles['Normal'].font.size.pt == 11, 'Normal 字号应为 11pt')
    expect(doc.sections[0].left_margin.cm > 2, '页边距未生效')


def test_cover_and_structure():
    doc = dh.new_document()
    dh.cover(doc, '测试公司（600000.SH）投资研究报告',
             subtitle='—— 副标题 ——',
             meta=['报告日期：2026年8月13日', '数据来源：测试'],
             disclaim='本报告仅供测试', badge='个股深度研究')
    dh.h1(doc, '一、核心结论')
    dh.h2(doc, '1.1 小节')
    dh.h3(doc, '1.1.1 三级')
    dh.para(doc, '正文段落', indent=True)
    dh.rich(doc, [('关键点：', True, dh.RED), ('说明', False, dh.DARK)])
    dh.bullet(doc, '内容文本', bold_prefix='结论一：')
    dh.pagebreak(doc)
    path = os.path.join(TMP, 'structure.docx')
    dh.save(doc, path)
    doc2 = dh.Document(path)
    texts = [p.text for p in doc2.paragraphs]
    expect('测试公司（600000.SH）投资研究报告' in texts, '封面标题缺失')
    expect('一、核心结论' in texts, '一级标题缺失')
    expect('正文段落' in texts, '正文缺失')
    band = doc2.tables[0].cell(0, 0)
    shd = band._tc.find(dh.qn('w:tcPr') + '/' + dh.qn('w:shd'))
    expect(shd is not None and shd.get(dh.qn('w:fill')) == dh.NAVY_HEX, '封面顶部色带缺失')
    expect(band.text == '个股深度研究', '封面徽章缺失')


def test_para_heading_styles():
    doc = dh.new_document()
    p = dh.para(doc, '加粗', bold=True)
    expect(p.runs[0].font.bold, '加粗未生效')
    p1 = dh.h1(doc, 'H1')
    expect(p1.runs[0].font.color.rgb == dh.MAROON, 'H1 应为酒红')
    pPr = p1._p.get_or_add_pPr()
    pbdr = pPr.find(dh.qn('w:pBdr'))
    expect(pbdr is not None, 'H1 缺少边框')
    expect(pbdr.find(dh.qn('w:left')) is not None, 'H1 缺少左侧色条')
    expect(pbdr.find(dh.qn('w:bottom')) is not None, 'H1 缺少底部金线')
    p2 = dh.h2(doc, 'H2')
    expect(p2.runs[0].font.color.rgb == dh.MAROON, 'H2 应为酒红')
    p2Pr = p2._p.get_or_add_pPr()
    expect(p2Pr.find(dh.qn('w:pBdr')) is not None, 'H2 缺少左侧细条')


def test_table_callout_img():
    import pandas as pd
    doc = dh.new_document()
    t = dh.add_table(doc, ['列A', '列B'], [['1', '2'], ['3', '4']], col_widths=[3, 3])
    expect(len(t.rows) == 3, '表格维度错误')
    expect(t.rows[1].cells[0].text == '1', '表格数据错误')
    hdr_shd = t.rows[0].cells[0]._tc.find(dh.qn('w:tcPr') + '/' + dh.qn('w:shd'))
    expect(hdr_shd is not None and hdr_shd.get(dh.qn('w:fill')) == dh.NAVY_HEX, '表头应为深蓝底')
    zebra_shd = t.rows[2].cells[1]._tc.find(dh.qn('w:tcPr') + '/' + dh.qn('w:shd'))
    expect(zebra_shd is not None and zebra_shd.get(dh.qn('w:fill')) == dh.ZEBRA, '斑马纹应为浅蓝灰')
    expect(t.rows[1].cells[0].paragraphs[0].runs[-1].font.bold, '首列应加粗')
    df = pd.DataFrame({'指标': ['营收'], '2024': [100.0], '2025': [None]})
    t2 = dh.table_from(doc, df)
    expect(t2.rows[1].cells[2].text == '—', 'NaN 应显示为 —')
    c = dh.callout(doc, '重点', color=dh.MAROON)
    expect(c.rows[0].cells[0].text.startswith('★ '), '结论 callout 应带 ★')
    tcPr = c.rows[0].cells[0]._tc.find(dh.qn('w:tcPr'))
    expect(tcPr.find(dh.qn('w:tcBorders')) is not None, 'callout 缺少左侧色条')
    c2 = dh.callout(doc, '风险', color=dh.RED)
    expect(c2.rows[0].cells[0].text.startswith('⚠ '), '风险 callout 应带 ⚠')


def test_setup_page():
    doc = dh.new_document()
    dh.setup_page(doc, '测试报告', '2026-08-20')
    sec = doc.sections[0]
    expect(sec.different_first_page_header_footer, '首页应跳过页眉页脚')
    hdr_text = ''.join(r.text for r in sec.header.paragraphs[0].runs)
    expect('测试报告' in hdr_text and '2026-08-20' in hdr_text, '页眉内容缺失: %r' % hdr_text)
    ftr_xml = sec.footer.paragraphs[0]._p.xml
    expect('PAGE' in ftr_xml, '页脚缺少 PAGE 页码域')


def test_save_stage():
    saved = dh.PROJECT_ROOT
    try:
        dh.PROJECT_ROOT = TMP
        doc = dh.new_document()
        dh.para(doc, 'x')
        out = dh.save_stage(doc, '测试报告_20260820.docx')
        expect(out == os.path.join(TMP, '暂存区', '测试报告_20260820.docx'), 'save_stage 未写根暂存区')
        try:
            dh.save_stage(doc, os.path.join('sub', 'a.docx'))
            raise AssertionError('save_stage 应拒绝带路径文件名')
        except ValueError:
            pass
    finally:
        dh.PROJECT_ROOT = saved


def test_save_json_meta():
    path = os.path.join(TMP, 'meta.json')
    fl.save_json({'a': 1}, path, ttl_hours=24, scope='test')
    d = fl.load_json(path)
    expect(d['_meta']['ttl_hours'] == 24, 'meta ttl 未注入')
    expect('fetched_at' in d['_meta'], 'meta fetched_at 缺失')


# ==================== chart_helpers ====================

def test_charts():
    ch.setup_cn()
    png = os.path.join(TMP, 'line.png')
    ch.line_chart([1, 2, 3], [1, 4, 9], title='折线', path=png)
    import matplotlib.image as mpimg
    expect(os.path.getsize(png) > 1000 and mpimg.imread(png).size > 0, '折线图无效')
    import matplotlib
    expect(matplotlib.get_backend().lower() == 'agg', '应为 Agg 后端')


# ==================== v3.2：通俗外挂层 / 图表编号 / 逻辑示意图 ====================

def _doc_all_text(doc):
    out = [p.text for p in doc.paragraphs]
    for tbl in doc.tables:
        for row in tbl.rows:
            for c in row.cells:
                out.append(c.text or '')
    return '\n'.join(out)


def test_plain_layout_elements():
    doc = dh.new_document()
    dh.speedread_page(doc, '测试公司', '评级：增持｜现价 10.2 元｜合理区间 11~14 元',
                      reasons=['理由一：量增', '理由二：价稳'],
                      key_numbers=(['指标', '值'], [['EPS', '2.6']]),
                      risks='最大风险：集采降价', bull='多头：新品放量', bear='空头：竞争加剧')
    dh.h1(doc, '一、正文')
    dh.para(doc, '专业论述段：EPS 2.6 元出自 forecast_lib。', indent=True)
    dh.plain_note(doc, '每股赚 2.6 元，PE 就像按房租算回本年限。', analogy=True)
    dh.so_what(doc, '按 12.4 元中枢折算，估值仍有空间。')
    dh.faq_box(doc, '为什么营收涨、利润反降？', '费用涨得更快，见 3.2 节。')
    dh.method_card(doc, 'DCF 现金流折现', what='把未来现金流折成今天的价值',
                   why='现金流稳定可预测时最可靠', how_to_read='中枢高于现价=低估')
    dh.table_intro(doc, '这张表想说明：盈利预测的量价假设')
    dh.fig_intro(doc, '这张图看的是营收趋势：2026 年增速见顶。')
    dh.add_table(doc, ['指标', '2026'], [['EPS', '2.6']], caption='盈利预测速览')
    dh.callout(doc, '评级：增持')
    path = os.path.join(TMP, 'plain.docx')
    dh.save(doc, path)
    doc2 = dh.Document(path)
    full = _doc_all_text(doc2)
    for mark in ('30秒速读｜测试公司', '评级：增持', '理由1：', '看表先读：', '看图先读：',
                 '白话解读｜', '※ 比喻仅为助记', '所以呢｜', '小白问：', '答：',
                 '方法卡｜DCF 现金流折现', '是什么', '为什么用它', '结果怎么读',
                 '表1　速读关键数字', '表2　盈利预测速览', '最大风险：', '多头最强论点：',
                 '空头最强论点：', '详细论证见后文'):
        expect(mark in full, '通俗件缺失: %r' % mark)


def test_fig_table_numbering():
    ch.setup_cn()
    png = os.path.join(TMP, 'num_fig.png')
    ch.line_chart([1, 2], [1, 2], path=png)
    doc = dh.new_document()
    dh.img(doc, png, caption='营收趋势', source='公司公告')
    dh.img(doc, png, caption='图5　历史股价')      # 已带编号：不重复编号
    dh.img(doc, png, caption='毛利率走势')
    dh.add_table(doc, ['A'], [['1']], caption='表A')
    dh.add_table(doc, ['B'], [['2']], caption='表B')
    st = dh._no_state(doc)
    expect(st['fig'] == 6 and st['tab'] == 2,
           '编号状态错误: %s' % st)  # 图1、图5(沿用)、图6；表1、表2
    full = _doc_all_text(doc)
    expect('图1　营收趋势（资料来源：公司公告）' in full, '自动图号缺失')
    expect('图5　历史股价' in full, '已带图号应沿用')
    expect('图6　毛利率走势' in full, '后续图号应接续')
    expect('表1　表A' in full and '表2　表B' in full, '自动表号缺失')
    lst = dh.fig_table_list(doc)
    expect(lst is not None and len(lst.rows) == 6, '图表清单应含表头+5 项')
    dh.reset_numbering(doc)


def test_diagram():
    ch.setup_cn()
    p = os.path.join(TMP, 'diag.png')
    ch.diagram([('上游\n原料', 5, 30, 22, 20), ('中游\n制造', 39, 30, 22, 20),
                ('下游\n渠道', 73, 30, 22, 20)],
               [(0, 1, '供货'), (1, 2, '销售'), (5, 8, 60, 20, '外部冲击')],
               title='产业链位置', path=p, note='※ 仅为逻辑示意，非按比例绘制')
    expect(os.path.getsize(p) > 1000, '逻辑示意图无效')


def test_depth_plain_checks():
    import check_report_depth as crd
    p = os.path.join(TMP, 'plaincheck.docx')
    doc = dh.new_document()
    dh.para(doc, '一、正文')
    dh.para(doc, '调研过程与盲点已列明。未查到项写明原因。' * 10)
    dh.para(doc, '假设有效性：失效信号与发生概率齐备。' * 10)
    dh.para(doc, '发散检验：历史类比/反事实/机会成本。' * 10)
    dh.para(doc, '公司 EPS 2.6 元，营收 87.3 亿。')
    dh.plain_note(doc, '每股赚 2.6 元。')        # 数字与专业层一致 → 合法
    dh.so_what(doc, '折算市占率高达 999.7。')    # 999.7 凭空出现 → 违规
    dh.save(doc, p)
    r = crd.check_docx(p, min_words=10)
    expect(any('通俗层数字与专业层不一致' in e for e in r['errors']),
           '应检出通俗层数字越权: %s' % r['errors'])
    expect(r['plain_blocks']['plain_texts'] >= 2, '外挂件应被统计')
    # 一致 + 有速读页 → 不出通俗类错误
    doc2 = dh.new_document()
    dh.para(doc2, '30秒速读｜测试资产')
    for t_ in ('调研过程与盲点已列明。未查到项写明原因。',
               '假设有效性：失效信号与发生概率齐备。',
               '发散检验：历史类比/反事实/机会成本。'):
        dh.para(doc2, t_ * 10)
    dh.plain_note(doc2, '一切照旧，没有新数字。')
    p2 = os.path.join(TMP, 'plaincheck2.docx')
    dh.save(doc2, p2)
    r2 = crd.check_docx(p2, min_words=10)
    expect(not any('通俗层' in e for e in r2['errors']), '一致时不应报通俗错误: %s' % r2['errors'])
    expect(not any('速读页' in w for w in r2['warns']), '有速读页不应警告')


# ==================== profile_lib：谓词求值 ====================

def test_eval_pred_basic():
    prof = {'cf': '有', 'data': ['kline', 'research'], 'hold_cost': 1, 'tplus': True}
    expect(pl.eval_pred('cf=有', prof), '等值求值失败')
    expect(pl.eval_pred('cf!=无', prof), '不等求值失败')
    expect(pl.eval_pred('data=research', prof), '数组包含求值失败')
    expect(pl.eval_pred('data=chain', prof) is False, '数组不包含应 False')
    expect(pl.eval_pred('hold_cost>=1', prof), '数值比较失败')
    expect(pl.eval_pred('true', prof), '恒真字面量失败')
    expect(pl.eval_pred('cf=有 & (data=kline | data=chain)', prof), '逻辑组合失败')
    expect(pl.eval_pred('!cf=无', prof), '取反失败')


def test_profile_from_answers():
    a = pl.profile_from_answers({'cf': '无', 'disc': '无', 'supply': '限量',
                                 'hold_cost': '1', 'liq': '低', 'beh': '趋势',
                                 'tplus': 'false', 'short': 'no',
                                 'min_unit': '0', 'data': 'listing, trade',
                                 'inv': '收藏'})
    expect(a['tplus'] is False, 'tplus 布尔解析失败')
    expect(a['hold_cost'] == 1, 'hold_cost 数值解析失败')
    expect(a['data'] == ['listing', 'trade'], 'data 数组解析失败')


# ==================== profile_lib：推导四例 ====================

def _derive(pid, rtype):
    p = pl.load_profile(pid)
    return p, pl.derive(p, rtype)


def test_derive_a_share():
    p, d = _derive('a_share_stock', '深度研究')
    ids = [m['id'] for m in d['methods']]
    expect('pe_quantile' in ids and 'dcf' in ids, 'A股应含 PE 分位与 DCF')
    expect('nvt_mvrv' not in ids, 'A股不应含链上指标')
    expect('cap_rate' not in ids, 'A股不应含资本化率（cf=有）')
    expect(d['blueprint']['id'] == 'equity_deep_8ch', 'A股蓝图应为 8 章专业研报范式')
    sec_ids = [s['id'] for s in d['blueprint']['sections']]
    expect('ch4' in sec_ids and 'counter_view' in sec_ids,
           '8 章蓝图应含盈利预测章(ch4)与反方章节')
    bts = [b['id'] for b in d['backtest']]
    expect('grid' in bts and 'dca' in bts, 'A股应含网格与定投回测')


def test_derive_real_estate():
    p, d = _derive('real_estate', '租金资产研究')
    ids = [m['id'] for m in d['methods']]
    expect('pe_quantile' not in ids and 'dcf' not in ids, '地产禁止 PE/DCF')
    expect('cap_rate' in ids and 'replacement_cost' in ids, '地产应含资本化率与重置成本')
    expect(d['blueprint']['id'] == 'rental_asset', '地产蓝图应为租金型')


def test_derive_crypto():
    p, d = _derive('crypto', '资产研究')
    ids = [m['id'] for m in d['methods']]
    expect('nvt_mvrv' in ids, '比特币应含链上指标')
    expect('dcf' not in ids and 'pe_quantile' not in ids, '比特币禁止 DCF/PE')
    expect(d['blueprint']['id'] == 'asset_research', '比特币蓝图应为资产研究')


def test_derive_collectible():
    p, d = _derive('collectible', '资产研究')
    ids = [m['id'] for m in d['methods']]
    expect('price_index' in ids and 'scarcity_premium' in ids, '手办应含价格指数化与稀缺溢价')
    expect('dcf' not in ids and 'ddm' not in ids, '手办禁止 DCF/DDM')
    expect('stats_baseline' in ids, '应有统计兜底')
    srcs = [s['id'] for s in d['sources']]
    expect('em_research' not in srcs, '手办不应匹配研报源（取证降级）')


def test_derive_unknown_profile():
    a = pl.profile_from_answers({'cf': '无', 'disc': '无', 'supply': '限量',
                                 'hold_cost': '1', 'liq': '低', 'beh': '趋势',
                                 'tplus': 'false', 'short': 'no',
                                 'min_unit': '0', 'data': 'listing, trade',
                                 'inv': '收藏'})
    d = pl.derive(a, '资产研究')
    expect(d['blueprint']['id'] == 'asset_research', '库外对象应推导出资产研究蓝图')
    expect(any(m['id'] == 'stats_baseline' for m in d['methods']), '库外对象应有统计兜底')


# ==================== profile_lib：分歧检测三例 ====================

def test_dispute_trigger():
    cfg = pl.load_library()['dispute']
    r = pl.dispute_analysis([
        {'method': 'DCF', 'low': 9, 'high': 13, 'central': 11},
        {'method': 'DDM', 'low': 14, 'high': 18, 'central': 16},
    ], cfg)
    expect(r['trigger'] is True, '中枢偏离 37%% 应触发，实际: %s' % r['reason'])


def test_dispute_consensus():
    cfg = pl.load_library()['dispute']
    r = pl.dispute_analysis([
        {'method': 'A', 'low': 10, 'high': 12, 'central': 11},
        {'method': 'B', 'low': 10.5, 'high': 12.5, 'central': 11.5},
        {'method': 'C', 'low': 9.5, 'high': 11.5, 'central': 10.5},
        {'method': 'D', 'low': 10, 'high': 12, 'central': 11},
        {'method': 'E', 'low': 15, 'high': 17, 'central': 16},
        {'method': 'F', 'low': 10.2, 'high': 11.8, 'central': 11},
    ], cfg)
    expect(r['trigger'] is False, '5/6 一致不应触发，实际: %s' % r['reason'])


def test_dispute_penalty_excluded():
    cfg = pl.load_library()['dispute']
    r = pl.dispute_analysis([
        {'method': 'PE', 'low': 30, 'high': 38, 'central': 34, 'flags': ['失真']},
        {'method': 'PB', 'low': 9, 'high': 11, 'central': 10},
        {'method': 'DCF', 'low': 9.5, 'high': 11.5, 'central': 10.5},
    ], cfg)
    expect(r['trigger'] is False, '失真方法剔除后应一致不触发，实际: %s' % r['reason'])
    expect(len(r['excluded']) == 1 and r['excluded'][0]['method'] == 'PE', '应剔除失真 PE')


def test_dispute_few_methods():
    cfg = pl.load_library()['dispute']
    r = pl.dispute_analysis([{'method': 'A', 'low': 1, 'high': 2, 'central': 1.5}], cfg)
    expect(r['trigger'] is False, '方法数不足不应触发')


# ==================== 规则库完整性 ====================

def test_library_integrity():
    lib = pl.load_library()
    expect(len(lib['methods']) >= 15, '方法库条目不足')
    expect(len(lib['sources']) >= 10, '源库条目不足')
    expect(len(lib['blueprints']) >= 6, '蓝图不足 6 个')
    profs = pl._load_json('profiles.json')['profiles']
    for prof in profs:
        for key in ('cf', 'disc', 'supply', 'hold_cost', 'liq', 'beh',
                    'tplus', 'short', 'min_unit', 'data', 'inv'):
            expect(key in prof, '档案 %s 缺字段 %s' % (prof['id'], key))
    for blp in lib['blueprints']:
        expect('sections' in blp and len(blp['sections']) >= 4, '蓝图 %s 章节不足' % blp['id'])
        for s in blp['sections']:
            expect('name' in s and 'spec' in s, '蓝图 %s 章节缺 name/spec' % blp['id'])
    for m in lib['methods']:
        pl.eval_pred(m.get('applies'), profs[0])
        pl.eval_pred(m.get('applies'), profs[-1])
    for blp in lib['blueprints']:
        pl.eval_pred(blp.get('applies'), profs[0])
    for s in lib['sources']:
        pl.eval_pred(s.get('applies'), profs[0])
        pl.eval_pred(s.get('applies'), profs[-1])


def test_stats_baseline_universal():
    lib = pl.load_library()
    stats = [m for m in lib['methods'] if m['id'] == 'stats_baseline']
    expect(len(stats) == 1, '统计兜底应唯一')
    for pid in ('a_share_stock', 'real_estate', 'crypto', 'collectible', 'bond_rate', 'index_fund'):
        p = pl.load_profile(pid)
        expect(pl.eval_pred(stats[0]['applies'], p), '统计兜底应恒真（%s）' % pid)


# ==================== 缓存/防堆积/交付（离线） ====================

def _make_project(tmp):
    os.makedirs(os.path.join(tmp, '暂存区'), exist_ok=True)
    os.makedirs(os.path.join(tmp, '分类区'), exist_ok=True)
    os.makedirs(os.path.join(tmp, 'sub'), exist_ok=True)
    return tmp


def test_cache_status():
    root = os.path.join(TMP, 'caches')
    _make_project(root)
    with open(os.path.join(root, 'sub', 'c1.json'), 'w', encoding='utf-8') as f:
        import json, datetime
        json.dump({'_meta': {'fetched_at': datetime.datetime.now().isoformat(timespec='seconds'),
                             'ttl_hours': 24, 'scope': 't'}}, f)
    with open(os.path.join(root, 'sub', 'c2.json'), 'w', encoding='utf-8') as f:
        json.dump({}, f)
    with open(os.path.join(root, 'sub', 'c3.json'), 'w', encoding='utf-8') as f:
        import json, datetime
        old = (datetime.datetime.now() - datetime.timedelta(days=400)).isoformat(timespec='seconds')
        json.dump({'_meta': {'fetched_at': old, 'ttl_hours': 24, 'scope': 't'}}, f)
    st_fresh = cs.check_file(os.path.join(root, 'sub', 'c1.json'), datetime.datetime.now())
    st_nometa = cs.check_file(os.path.join(root, 'sub', 'c2.json'), datetime.datetime.now())
    st_stale = cs.check_file(os.path.join(root, 'sub', 'c3.json'), datetime.datetime.now())
    expect(st_fresh == 'fresh', '新鲜缓存判定错误: %s' % st_fresh)
    expect(st_nometa == 'no-meta', '无 meta 判定错误: %s' % st_nometa)
    expect(st_stale.startswith('stale'), '过期判定错误: %s' % st_stale)


def test_check_storage():
    root = os.path.join(TMP, 'storage')
    os.makedirs(os.path.join(root, 'a'), exist_ok=True)
    os.makedirs(os.path.join(root, 'b'), exist_ok=True)
    data = b'x' * 1000
    for sub in ('a', 'b'):
        with open(os.path.join(root, sub, 'dup.json'), 'wb') as f:
            f.write(data)
    with open(os.path.join(root, 'a', 'uniq.json'), 'wb') as f:
        f.write(b'y' * 999)
    names = {}
    for base, _, files in os.walk(root):
        for fn in files:
            names.setdefault(fn, []).append(os.path.join(base, fn))
    expect(len(names['dup.json']) == 2, '测试夹具重复文件应存在')
    expect(len(names['uniq.json']) == 1, 'uniq 不应重复')
    print('  (check_storage 全项目扫描在 check_delivery 中执行)')


def test_check_delivery():
    import workspace_lib as wl
    # v3.3 封闭化：独立 fixture 根跑（原实现扫真实项目根，用户实测残留会误伤 CI）
    root = os.path.join(TMP, 'wsroot_cd')
    os.makedirs(os.path.join(root, '.opencode'), exist_ok=True)
    wl.set_root(root)
    try:
        expect(cd.main() == 0, '空注册表+无产物应 0 错误（落点/命名/防堆积违规）')
        e = wl.init_workspace('交付质检资产')
        doc = dh.new_document()
        dh.para(doc, 'x')
        dh.save_stage(doc, '交付质检资产报告_20260101.docx', report_no=e['no'])
        expect(cd.main() == 0, '合法双写交付应 0 错误')
    finally:
        wl.set_root(None)


def test_check_report_depth():
    import check_report_depth as crd
    expect(crd.DEFAULT_MIN_WORDS == 8000, 'lite 字数门槛应为 8000')
    floor = {'equity_deep_8ch': 8000, 'asset_research': 8000, 'rental_asset': 8000,
             'theme_quant': 6000, 'strategy_manual': 5000, 'educational': 5000,
             'decision_report': 4000, 'update_report': 3000}
    for blp in pl._load_json('blueprints.json')['blueprints']:
        expect(blp.get('min_words', 0) >= floor.get(blp['id'], 8000),
               '蓝图 %s min_words 应 ≥%s' % (blp['id'], floor.get(blp['id'], 8000)))
        expect(blp.get('flow') in ('full', 'standard', 'minimal'),
               '蓝图 %s 应有合法 flow 分级' % blp['id'])
    # 差报告：空章节 + 字数不足 + 缺强制章节
    p1 = os.path.join(TMP, 'bad.docx')
    doc = dh.new_document()
    dh.para(doc, '一、空章节标题')          # 紧跟下一标题 → 空
    dh.para(doc, '二、下一标题')
    dh.para(doc, '正文一两句')
    dh.save(doc, p1)
    r1 = crd.check_docx(p1, min_words=3000)
    expect(any('空章节' in e for e in r1['errors']), '应检出空章节')
    expect(any('字数不足' in e for e in r1['errors']), '应检字数不足')
    expect(any('强制章节缺失' in e for e in r1['errors']), '应检强制章节缺失')
    # 好报告：分组标题下接小节不报空
    p2 = os.path.join(TMP, 'good.docx')
    doc = dh.new_document()
    dh.para(doc, '第一节 分组标题')
    dh.para(doc, '一、子节')
    dh.para(doc, '本报告调研过程与方法：调研源清单与盲点清单已列明。未查到部分写明原因。' * 40)
    dh.para(doc, '关键假设有效性评估：发生概率与概率依据见下表，失效信号明确。' * 40)
    dh.para(doc, '发散检验：历史类比、反事实推演与机会成本对比详见正文。' * 40)
    dh.save(doc, p2)
    r2 = crd.check_docx(p2, min_words=100)
    expect(not r2['errors'], '合格报告不应有错误: %s' % r2['errors'])
    print('  (空章节检测验证: 分组标题→小节不误报)')


# ==================== forecast_lib ====================

def test_forecast_equity():
    import forecast_lib as fcl
    os.makedirs(TMP, exist_ok=True)
    a = fcl.Assumption(0.12, basis='行业增速8%+份额提升', tag='[推断]', probability=0.6)
    fc = fcl.build_equity_forecast(
        years=[2026, 2027, 2028],
        segments=[{'name': '主业', 'method': 'growth', 'base': 100.0,
                   'assumptions': {'growth': a}}],
        gross_margin=fcl.Assumption(0.32, basis='近5年中枢', tag='[实证]', probability=0.7),
        opex_ratio=fcl.Assumption(0.12, basis='费用率稳定', tag='[实证]', probability=0.7),
        tax_rate=fcl.Assumption(0.15, basis='高新税率', tag='[实证]', probability=0.9),
        shares=10.0, equity_base=50.0)
    fcl.validate_forecast(fc)
    expect(fc['per_year'][-1]['revenue'] > 100, '营收应增长')
    expect(abs(fc['central']['eps'] - fc['per_year'][-1]['eps']) < 1e-9, '中枢应取末年')
    st = fcl.scenario_table(fc, low_shift=0.2, high_shift=0.2)
    expect(st['保守'] < st['中性'] < st['乐观'], '情景三档应递增')
    try:
        fcl.scenario_table(fc)
        raise AssertionError('档位偏移缺省应被拒绝（禁止硬编码默认值）')
    except ValueError:
        pass
    try:
        fcl.Assumption(0.1, basis='', tag='[观点]')
        raise AssertionError('裸（估）应被拦截')
    except ValueError:
        pass
    try:
        fcl.Assumption(0.1, basis='x', tag='[瞎写]')
        raise AssertionError('非法 tag 应被拦截')
    except ValueError:
        pass


def test_forecast_rental_and_balance():
    import forecast_lib as fcl
    fc = fcl.build_rental_forecast(
        [2026, 2027], gross_rent_base=1.0,
        rent_growth=fcl.Assumption(0.03, basis='CPI 联动历史', tag='[实证]', probability=0.7),
        vacancy_rate=fcl.Assumption(0.05, basis='近3年出租率', tag='[实证]', probability=0.7),
        opex_ratio=fcl.Assumption(0.20, basis='运营成本台账', tag='[实证]', probability=0.8))
    fcl.validate_forecast(fc)
    expect(fc['per_year'][1]['noi'] > fc['per_year'][0]['noi'], 'NOI 应增长')
    bal = fcl.build_supply_demand_balance(
        history=[{'year': 2020, 'supply_delta': 1, 'demand_proxy': 2, 'price_change': 0.1}],
        forecast_rows=[{'year': 2027,
                        'supply_delta': fcl.Assumption(1, basis='官宣产能', tag='[实证]', probability=0.8),
                        'demand_proxy': fcl.Assumption(2, basis='人群扩张', tag='[推断]', probability=0.5),
                        'price_change': fcl.Assumption(0.05, basis='供需比外推', tag='[观点]', probability=0.4)}])
    fcl.validate_forecast(bal)
    expect(bal['forecast'][0]['supply_delta']['tag'] == '[实证]', '平衡表假设应保留标签')


# ==================== valuation_lib ====================

def test_valuation_operators():
    import valuation_lib as vl
    ctx = {'data': {'shares': 10.0, 'eps_f': 2.0, 'eps_ttm': 1.6,
                    'pe_hist': [8, 9, 10, 11, 12, 9.5, 10.5],
                    'peers': [{'name': 'A', 'pe': 9.0}, {'name': 'B', 'pe': 11.0}],
                    'fcf_f': [5.0, 5.5, 6.0], 'net_debt': 10.0,
                    'ebitda': 8.0, 'dps_f': 0.5,
                    'price_hist': [10, 11, 9, 12, 8, 11.5]},
           'refs': {'eps_f': {'file': 'forecast_t.json', 'field': 'central.eps',
                              'fetched_at': '2026-08-30'}}}
    results, skipped = vl.run_methods(
        ['relative_peer', 'pe_quantile', 'dcf', 'ddm', 'ev_ebitda',
         'stats_baseline', 'bull_bear'], ctx,
        {'dcf': {'wacc': (0.08, 0.09, 0.10), 'g': 0.02},
         'ev_ebitda': {'mult_lo': 6.0, 'mult_mid': 8.0, 'mult_hi': 10.0},
         'ddm': {'yield_lo': 0.05, 'yield_mid': 0.045, 'yield_hi': 0.04}})
    ids = [r['method_id'] for r in results]
    expect('relative_peer' in ids and 'dcf' in ids, '主力算子应可运行')
    expect(any(s['method'] == 'bull_bear' for s in skipped), '论证类方法应跳过并记录')
    for r in results:
        expect(r['low'] <= r['central'] <= r['high'], '%s 区间应有序' % r['method_id'])
    no_param, _ = vl.run_methods(['dcf'], ctx, {'dcf': {'wacc': (0.08, 0.09, 0.10)}})
    expect(not no_param, 'DCF 缺 g 应被拒绝（禁止硬编码默认值）')
    d = pl.dispute_analysis(results, pl.load_library()['dispute'])
    expect('trigger' in d, '结果应兼容分歧检测')
    rows = vl.provenance_rows(results)
    expect(any('forecast_t.json' in str(row) for row in rows), '溯源行应含来源文件')


def test_valuation_crosscheck_flip():
    import valuation_lib as vl
    cc = vl.crosscheck({'em': 100.0, 'tx': 100.8})
    expect(cc['ok'], '1% 内应通过')
    cc2 = vl.crosscheck({'em': 100.0, 'tx': 103.0}, metric='mcap')
    expect(not cc2['ok'] and cc2['warnings'], '>1% 应告警')
    fp = vl.flip_point(lambda eps: eps * 10.0, target=15.0, lo=0.5, hi=5.0)
    expect(abs(fp - 1.5) < 1e-3, '翻车点应解出 EPS=1.5')
    d = pl.derive(pl.load_profile('a_share_stock'), '深度研究')
    res, sk = vl.run_derived(d, {'data': {}, 'refs': {}})
    expect(res == [] and sk, 'ctx 为空时应全部跳过而非崩溃')


# ==================== review_lib ====================

def test_review_dossier():
    import review_lib as rl
    saved_root = rl._find_project_root
    os.makedirs(os.path.join(TMP, '暂存区'), exist_ok=True)
    os.makedirs(os.path.join(TMP, '分类区'), exist_ok=True)
    rl._find_project_root = lambda: TMP
    try:
        subj = '自测资产'
        p = rl.dossier_path(subj)
        if os.path.exists(p):
            os.remove(p)
        expect(rl.load_dossier(subj) is None and not rl.has_prior(subj), '初始无档案')
        try:
            rl.record(subj, {'date': '2026-08-30', 'rating': '买入', 'range_low': 10,
                             'central': 12, 'range_high': 14})
            raise AssertionError('缺复查触发条件应拒绝')
        except ValueError:
            pass
        rl.record(subj, {'date': '2026-08-30', 'rating': '买入', 'range_low': 10,
                         'central': 12, 'range_high': 14, 'price_now': 11,
                         'expiry': '2027-08-30',
                         'review_triggers': ['跌破10元'],
                         'assumptions': [{'desc': 'EPS 1.9', 'probability': 0.6,
                                          'trigger': 'Q3 低于预期'}]},
                  report_file='t.docx')
        rl.update_judgment(subj, 0, '命中', evidence='现价12.5在区间内', asof='2027-02-01')
        cal = rl.calibration(subj)
        expect(cal['hit'] == 1 and cal['rate'] == 1.0, '校准率应为 1.0: %s' % cal)
        t = rl.prior_review_table(subj, price_now=12.5)
        expect(t['rows'] and t['rows'][0]['last_judgment']['judgment'] == '命中',
               '复盘表应含最新判定')
        doc = dh.new_document()
        dh.para(doc, 'x')
        dh.PROJECT_ROOT = TMP
        dh.save_stage(doc, '自测报告.docx', subject=subj,
                      review={'date': '2026-09-01', 'rating': '持有', 'range_low': 11,
                              'central': 13, 'range_high': 15, 'price_now': 12.5,
                              'expiry': '2027-09-01', 'review_triggers': ['跌破11']})
        expect(len(rl.load_dossier(subj)['conclusions']) == 2, 'save_stage 应自动落档')
    finally:
        rl._find_project_root = saved_root
        dh.PROJECT_ROOT = None


# ==================== thesis_lib / 合成 / H 修复 ====================

def test_thesis_lib():
    import thesis_lib as tl
    th = tl.build_thesis(subject='XX', conclusion='增持：区间10~14元',
                         pillars=[
                             {'claim': '2028年EPS 2.6元', 'probability': 0.6,
                              'evidence': [{'chapter': 'ch4', 'data_file': 'data/forecast.json'}]},
                             {'claim': '可比PE中枢10.5倍', 'probability': 0.7,
                              'evidence': [{'chapter': 'ch6', 'fig': 'fig6'}]},
                             {'claim': '行业格局稳定', 'probability': 0.5,
                              'evidence': [{'chapter': 'ch2'}]}])
    tl.validate_thesis(th)
    bad = tl.build_thesis('X', '结论', pillars=[{'claim': '无证据柱', 'evidence': []},
                                                {'claim': 'b', 'evidence': [{'chapter': 'c1'}]}])
    try:
        tl.validate_thesis(bad)
        raise AssertionError('无证据映射的柱应拒绝')
    except ValueError:
        pass


def test_weighted_synthesis():
    import valuation_lib as vl
    results = [{'method_id': 'a', 'low': 8, 'central': 10, 'high': 12},
               {'method_id': 'b', 'low': 13, 'central': 16, 'high': 20}]
    syn = vl.weighted_synthesis(results, {'a': 0.75, 'b': 0.25})
    expect(abs(syn['weighted_central'] - 11.5) < 1e-6, '加权中枢应为 11.5')
    expect(syn['envelope_low'] == 8 and syn['envelope_high'] == 20, '包络区间应正确')
    expect(syn['overlap_ratio'] == 0.0, '两区间不重叠应为 0')
    try:
        vl.weighted_synthesis(results, {})
        raise AssertionError('全零权重应拒绝')
    except ValueError:
        pass


def test_dossier_code_key_and_judgment():
    import review_lib as rl
    saved_root = rl._find_project_root
    os.makedirs(os.path.join(TMP, '暂存区'), exist_ok=True)
    os.makedirs(os.path.join(TMP, '分类区'), exist_ok=True)
    rl._find_project_root = lambda: TMP
    try:
        rl.record('锦江酒店(600754)', {'date': '2026-08-30', 'rating': '买入',
                                      'range_low': 28, 'central': 32, 'range_high': 36,
                                      'price_now': 30, 'expiry': '2027-08-30',
                                      'review_triggers': ['跌破28']})
        d = rl.load_dossier('600754')
        expect(d is not None and '锦江酒店(600754)' in d['aliases'], '代码主键+别名应生效')
        expect(rl.dossier_key('锦江酒店600754') == '600754', '主键应解析出代码')
        sg = rl.suggest_judgment({'range_low': 28, 'range_high': 36, 'expiry': '2027-08-30'},
                                 price_now=33.0, asof='2027-08-30')
        expect(sg['judgment'] == '命中', '区间内应建议命中: %s' % sg)
        sg2 = rl.suggest_judgment({'range_low': 28, 'range_high': 36, 'expiry': '2027-08-30'},
                                  price_now=25.0, asof='2026-09-30')
        expect(sg2['judgment'] == '待定', '未到期区间外应建议待定: %s' % sg2)
        sg3 = rl.suggest_judgment({'range_low': 28, 'range_high': 36, 'expiry': '2027-08-30'},
                                  price_now=25.0, asof='2027-12-30')
        expect(sg3['judgment'] == '失误', '到期区间外应建议失误: %s' % sg3)
        t = rl.prior_review_table('600754', price_now=33.0, asof='2027-08-30')
        expect(t['rows'][0]['suggested']['judgment'] == '命中', '复盘表应附建议判定')
    finally:
        rl._find_project_root = saved_root
        p = os.path.join(TMP, '档案', '600754.json')
        if os.path.exists(p):
            os.remove(p)


def test_dump_markers():
    doc = dh.new_document()
    dh.para(doc, '第一章 公司概况')
    dh.para(doc, '1.1 业务构成')
    dh.para(doc, '正文段落2026年营收100亿元')
    dh.para(doc, '图1 营收趋势')
    dh.add_table(doc, ['a'], [['b']])
    p = os.path.join(TMP, 'marked.docx')
    dh.save(doc, p)
    txt = dh.dump_doc_text(p, os.path.join(TMP, 'marked.txt'))
    content = open(txt, encoding='utf-8').read()
    expect('【H1】第一章' in content and '【H2】1.1' in content, '标题标记应生效')
    expect('【图注】图1' in content and '【表】' in content, '图注/表标记应生效')


def test_trace_missing_files_fail():
    import check_report_depth as crd
    os.makedirs(TMP, exist_ok=True)
    empty_dir = os.path.join(TMP, 'empty_trace')
    os.makedirs(empty_dir, exist_ok=True)
    doc = dh.new_document()
    dh.para(doc, '一、结论')
    dh.para(doc, '调研过程与盲点清单已列明，未查到项说明。假设有效性含失效信号与发生概率。'
                 '发散检验：历史类比/反事实/机会成本。' * 5)
    dh.para(doc, '综合估值中枢 12.5 元，合理区间 10~14 元。' * 5)
    p = os.path.join(TMP, 'nores.docx')
    dh.save(doc, p)
    r = crd.check_docx(p, min_words=10, rtype='equity_deep_8ch', trace_dir=empty_dir)
    expect(any('数字来源缺失' in e for e in r['errors']),
           '含估值数字而无算子输出文件应 FAIL: %s' % r['errors'])


def test_flow_log():
    import flow_log as flw
    os.makedirs(TMP, exist_ok=True)
    log = flw.FlowLog('自测-scope')
    import time as _t
    with log.step('数据抓取'):
        _t.sleep(0.05)
    log.event('估值', rounds=1, settled=3, backflow=0)
    sm = log.summary()
    expect(sm['n_steps'] == 1 and sm['steps'][0]['seconds'] >= 0.05, '步骤耗时应记录')
    expect(sm['events'][0]['settled'] == 3, '事件应记录')
    log.save(os.path.join(TMP, 'pipeline_log_test.json'))


def test_tree_diff_pdf_asof_error_patterns():
    import thesis_lib as tl
    import fetch_lib as fl
    import review_lib as rl
    import fitz
    os.makedirs(TMP, exist_ok=True)
    th = tl.build_thesis('X', '增持：区间10~14元',
                         pillars=[{'claim': 'EPS 2.6元', 'evidence': [{'chapter': 'ch4'}]},
                                  {'claim': '可比PE 10.5倍', 'evidence': [{'chapter': 'ch6'}]}])
    rec = {'conclusion': '增持：区间10~14元', 'pillars': ['EPS 2.6元', '行业格局改善']}
    d = tl.tree_diff(th, rec)
    expect(d['conclusion_match'] and len(d['matched']) == 1, '树对照应命中结论与一柱: %s' % d)
    expect(d['missing'] == ['可比PE 10.5倍'] and d['extra'] == ['行业格局改善'],
           '缺柱/多柱应被识别: %s' % d)
    pdf = os.path.join(TMP, 't.pdf')
    doc_pdf = fitz.open()
    page = doc_pdf.new_page()
    page.insert_text((72, 72), 'goodwill impairment total 3.2 bn')
    doc_pdf.save(pdf)
    doc_pdf.close()
    pages = fl.pdf_text(pdf)
    expect(pages and 'goodwill' in pages[0]['text'], 'PDF 文本提取应工作')
    expect(fl.pdf_text(pdf, keyword='notexist') == [], '关键词过滤应返回空')
    cache = os.path.join(TMP, 'results_x.json')
    fl.save_json({'v': 1}, cache, ttl_hours=24, scope='t', source='test')
    rows = fl.cache_meta_table([cache])
    expect(rows and rows[0][2] == '24', 'as-of 表应含 TTL: %s' % rows)
    doc2 = dh.new_document()
    dh.data_asof_table(doc2, rows)
    expect(len(doc2.tables) == 1, '数据截止表应可生成')
    saved_root = rl._find_project_root
    os.makedirs(os.path.join(TMP, '暂存区'), exist_ok=True)
    os.makedirs(os.path.join(TMP, '分类区'), exist_ok=True)
    rl._find_project_root = lambda: TMP
    try:
        ep = rl.error_patterns()
        expect('by_rating' in ep and 'overall' in ep, '错误模式聚合应可运行')
        expect(ep['overall']['hit'] + ep['overall']['miss'] >= 1, '应聚到测试档案的判定')
    finally:
        rl._find_project_root = saved_root


def test_update_report_derive():
    d = pl.derive(pl.load_profile('a_share_stock'), '更新报告')
    expect(d['blueprint']['id'] == 'update_report', '更新报告应匹配专属蓝图')
    ids = [s['id'] for s in d['blueprint']['sections']]
    expect('prior_review' in ids and 'valuation_update' in ids,
           '更新蓝图应含复盘与估值更新章')
    expect(d['blueprint']['flow'] == 'standard', '更新报告应为 standard 流程')




def test_dump_doc_text():
    os.makedirs(TMP, exist_ok=True)
    doc = dh.new_document()
    dh.para(doc, '一、投资要点')
    dh.para(doc, '2028年预测EPS 2.6元（估）')
    dh.add_table(doc, ['指标', '值'], [['EPS', '2.6'], ['PE', '10.5']])
    p = os.path.join(TMP, 'draft.docx')
    dh.save(doc, p)
    txt = dh.dump_doc_text(p, os.path.join(TMP, 'draft.txt'))
    content = open(txt, encoding='utf-8').read()
    expect('2028年预测EPS' in content, '文本导出应含段落')
    expect('2.6\t10.5' in content or 'EPS\t2.6' in content, '文本导出应含表格行')
    expect(dh.dump_doc_text(doc, txt) == txt, '应支持直接传 Document 对象')


def test_report_depth_v2():
    import check_report_depth as crd
    os.makedirs(TMP, exist_ok=True)
    res = os.path.join(TMP, 'results_v2t.json')
    json.dump({'eps': 2.6, 'low': 10.2, 'central': 12.4, 'high': 14.8},
              open(res, 'w', encoding='utf-8'))
    p = os.path.join(TMP, 'trace.docx')
    doc = dh.new_document()
    dh.para(doc, '一、正文')
    dh.para(doc, '调研过程与盲点已列明。未查到项写明原因。' * 10)
    dh.para(doc, '假设有效性：失效信号与发生概率齐备。' * 10)
    dh.para(doc, '发散检验：历史类比/反事实/机会成本。' * 10)
    dh.add_table(doc, ['指标', '值'], [['EPS', '2.6'], ['中枢', '12.4'], ['杜撰', '999.7']])
    dh.save(doc, p)
    tr = crd.trace_numbers(['2.6', '12.4', '999.7'], TMP)
    expect(tr is not None and tr['hit_rate'] >= 0.6, '溯源命中率应≥0.6: %s' % tr)
    expect(not crd._pool_matches(999.7, {2.6, 10.2, 12.4, 14.8}), '杜撰数字不应命中')
    r = crd.check_docx(p, min_words=10, rtype='equity_deep_8ch')
    expect(any('盈利预测' in e for e in r['errors']), 'equity 蓝图应强制盈利预测章: %s' % r['errors'])


# ==================== v3.0：工作区/brief/技法/PUA/单次审计/ACH/基础比率 ====================

def test_workspace_registry():
    import workspace_lib as wl
    root = os.path.join(TMP, 'wsroot')
    os.makedirs(os.path.join(root, '.opencode'), exist_ok=True)
    wl.set_root(root)
    try:
        e1 = wl.init_workspace('自测资产A')
        e2 = wl.init_workspace('自测资产B')
        expect(e1['no'] == 1 and e2['no'] == 2, '编号应从 1 连续分配')
        expect(os.path.isfile(wl.brief_path(1)) is False, 'brief 由 grill 后创建')
        for sd in wl.SUBDIRS:
            expect(os.path.isdir(os.path.join(e1['dir'], sd)), '子目录缺失 %s' % sd)
        expect(os.path.isfile(os.path.join(e1['dir'], 'WORKSPACE.md')), 'WORKSPACE.md 应生成')
        p = os.path.join(e1['dir'], '20_forecast', 'forecast.json')
        json.dump({'v': 1}, open(p, 'w', encoding='utf-8'))
        wl.register_file(1, p, kind='forecast', desc='预测输出')
        expect(wl.locate('1')['no'] == 1 and wl.locate('自测资产B')['no'] == 2,
               'locate 应支持编号与主题名')
        wl.blocked(2, '数据源全挂', resume_hint='/report resume 2')
        expect(wl.locate(2)['status'] == 'blocked', 'blocked 态应可读')
        legacy = os.path.join(root, 'data', 'tcm_industry_202609')
        os.makedirs(legacy, exist_ok=True)
        el = wl.assign_legacy(legacy, subject='中药行业(旧)')
        expect(el['legacy'] is True and el['no'] >= 3, '旧报告应懒分配编号且标记 legacy')
        expect(wl.assign_legacy(legacy)['no'] == el['no'], '同路径重复懒登记应幂等')
    finally:
        wl.set_root(None)


def test_save_stage_report_no():
    import datetime
    import workspace_lib as wl
    import docx_helpers as dh2
    root = os.path.join(TMP, 'wsroot')
    wl.set_root(root)
    try:
        e = wl.init_workspace('双写资产')
        no = e['no']
        doc = dh2.new_document()
        dh2.para(doc, 'x')
        hist = dh2.save_stage(doc, '双写资产深度研究报告_20261003.docx', report_no=no)
        ent = wl.locate(no)
        expect(ent['status'] == 'delivered', '交付后注册表应置 delivered')
        expect(os.path.exists(ent['deliverable']), '所有报告/ 最新版双写缺失')
        expect(ent['deliverable'].endswith('%d_%s' % (no, '双写资产深度研究报告.docx')),
               '最新版命名应为 {编号}_{报告名}.docx: %s' % ent['deliverable'])
        expect(os.path.basename(hist).startswith(datetime.date.today().strftime('%Y%m%d')),
               '历史版本应带日期前缀')
        import check_delivery as cd2
        expect(cd2.main() == 0, 'check_delivery 对合法双写应 0 错误')
    finally:
        wl.set_root(None)


def test_brief_lib():
    import brief_lib as blf
    b = blf.new_brief('自测', report_no=1)
    qs = [{'id': 'q%d' % i, 'q': '问题%d' % i, 'options': ['A', 'B']} for i in range(5)]
    try:
        blf.record_wave(b, qs[:3], [], decisions=[])
        raise AssertionError('<5 问应报错')
    except ValueError:
        pass
    blf.record_wave(b, qs, [{'question_id': 'q1', 'answer': '深度研究'}],
                    decisions=[{'field': 'report_type', 'value': '深度研究'}])
    expect(blf.vague_hits('再深度一点，差不多就行') != [], '模糊词应被检出')
    stop, why = blf.termination_check(b)
    expect(stop and '单波' in why, '单波协议问完即止: %s' % why)
    try:
        blf.record_wave(b, qs, [], decisions=[])
        raise AssertionError('第二波应报错（单波协议）')
    except ValueError:
        pass
    ok, missing = blf.validate_brief(b)
    expect(not ok and '读者' in ';'.join(missing), '缺必填字段应被列出')
    try:
        blf.approve(b)
        raise AssertionError('不完整 brief 批准应报错')
    except ValueError:
        pass
    for field, val in [('reader', '自己决策'), ('purpose', '买入决策'),
                       ('key_concerns', ['估值是否偏高', '增长可持续性', '风险点']),
                       ('failure_criteria', '评级方向错误即失败'),
                       ('time_range', '3年'), ('length_pref', '标准篇幅'),
                       ('language', '中文'), ('flow_level', 'full')]:
        b['fields'][field] = val
    ok, missing = blf.validate_brief(b)
    expect(ok, '补全后应通过: %s' % missing)
    blf.approve(b)
    expect(b['approval']['approved'], '批准态应记录')
    expect('需求摘要' in blf.summary(b), '摘要应可生成')


def test_technique_lib():
    import technique_lib as tcl
    import flow_log as flw
    p = pl.load_profile('a_share_stock')
    cands = tcl.recommend(p, stage='预测前', blueprint_id='equity_deep_8ch', flow_level='full')
    ids = [c['id'] for c in cands]
    expect('premortem' in ids, 'full 级预测前应含 premortem')
    pm = next(c for c in cands if c['id'] == 'premortem')
    expect(pm['always_on'] is True, 'premortem 对 full 应强制')
    cands_std = tcl.recommend(p, stage='假设校验', flow_level='standard')
    br = next(c for c in cands_std if c['id'] == 'base_rate_outside_view')
    expect(br['always_on'] is True, 'base_rate 对 standard 应强制')
    cands_min = tcl.recommend(p, stage='假设校验', flow_level='minimal')
    expect(all(not c['always_on'] for c in cands_min), 'minimal 级无强制技法')
    fq = tcl.recommend(p, stage='财务质量')
    expect('piotroski_fscore' in [c['id'] for c in fq], 'A股财务质量挂点应含 F-Score')
    hand = tcl.recommend(pl.load_profile('collectible'), stage='财务质量')
    expect('piotroski_fscore' not in [c['id'] for c in hand], '手办（cf=无）不应出财务质量技法')

    log = flw.FlowLog('technique-test')
    tcl.activate(log, 'premortem', reason='full 级强制')
    tcl.activate(log, 'moat_scoring', reason='护城河柱需结构化评级')
    tcl.activate(log, 'inversion', reason='风险章反向清单预检', stage='预测前')
    try:
        tcl.activate(log, 'delphi_estimate', reason='超限测试', stage='预测前')
        raise AssertionError('同一挂点 >3 激活应报错')
    except ValueError:
        pass

    tpath = os.path.join(TMP, 'techniques_test.json')
    shutil.copyfile(tcl.TECHNIQUES_PATH, tpath)
    try:
        tcl.propose_auto({'id': 'no_src', 'name': 'X', 'stage': '风险',
                          'trigger': 't', 'protocol': 'p'}, path=tpath)
        raise AssertionError('无来源提案应报错')
    except ValueError:
        pass
    tcl.propose_auto({'id': 'test_auto_tech', 'name': '测试技法', 'stage': '风险',
                      'trigger': '触发', 'protocol': '协议', 'applies': 'true',
                      'sources': [{'tier': '教材·论文', 'cite': 'Test Book 2026'}]},
                     path=tpath)
    with open(tpath, 'r', encoding='utf-8') as f:
        d = json.load(f)
    expect(len(d['auto']) == 1 and d['auto'][0]['origin'] == 'auto', 'auto 区应写入')
    auto_cands = tcl.recommend(p, stage='风险', path=tpath)
    expect('test_auto_tech' in [c['id'] for c in auto_cands], 'auto 技法应可被推荐')


def test_ach_matrix():
    m = pl.ach_matrix(['估值抬升=盈利驱动', '估值抬升=流动性驱动'],
                      [{'desc': '可比盈利上修', 'source': 'a.json',
                        'scores': {'估值抬升=盈利驱动': '一致', '估值抬升=流动性驱动': '无关'}},
                       {'desc': '利率下行', 'source': 'b.json',
                        'scores': {'估值抬升=盈利驱动': '无关', '估值抬升=流动性驱动': '一致'}},
                       {'desc': '盈利与估值同涨（两读法均一致）', 'source': 'c.json',
                        'scores': {'估值抬升=盈利驱动': '一致', '估值抬升=流动性驱动': '一致'}}])
    expect(m['ranking'][0] == '估值抬升=盈利驱动', '最少不一致应排第一: %s' % m['ranking'])
    expect(len(m['diagnostic_evidence']) == 0, '本例无区分性证据（全部单向一致/无关）')
    m2 = pl.ach_matrix(['A', 'B'], [{'desc': '反A', 'source': 'x',
                                     'scores': {'A': '不一致', 'B': '一致'}}])
    expect(m2['inconsistency']['A'] == 1 and m2['diagnostic_evidence'] == ['反A'],
           '不一致证据应有区分力')


def test_base_rate_downgrade():
    import forecast_lib as fcl
    a_g = fcl.Assumption(0.12, basis='行业8%+份额提升', tag='[推断]', probability=0.6)
    fc = fcl.build_equity_forecast(
        years=[2026], segments=[{'name': '主业', 'method': 'growth', 'base': 100.0,
                                 'assumptions': {'growth': a_g}}],
        gross_margin=fcl.Assumption(0.32, basis='历史中枢', tag='[实证]', probability=0.7),
        opex_ratio=fcl.Assumption(0.12, basis='稳定', tag='[实证]', probability=0.7),
        tax_rate=fcl.Assumption(0.15, basis='高新税率', tag='[实证]', probability=0.9),
        shares=12.5, equity_base=90.0)
    expect(fc['base_rate_downgrades'], '[推断] 增长假设缺 base_rate_ref 应记录降级')
    expect(fc['segments'][0]['assumptions']['growth']['tag'] == '[观点]',
           '缺基础比率的假设应降级 [观点]')
    a_g2 = fcl.Assumption(0.12, basis='行业8%+份额提升', tag='[推断]', probability=0.6,
                          base_rate_ref='data/industry_growth.json:P25~P75')
    fc2 = fcl.build_equity_forecast(
        years=[2026], segments=[{'name': '主业', 'method': 'growth', 'base': 100.0,
                                 'assumptions': {'growth': a_g2}}],
        gross_margin=fcl.Assumption(0.32, basis='历史中枢', tag='[实证]', probability=0.7),
        opex_ratio=fcl.Assumption(0.12, basis='稳定', tag='[实证]', probability=0.7),
        tax_rate=fcl.Assumption(0.15, basis='高新税率', tag='[实证]', probability=0.9),
        shares=12.5, equity_base=90.0)
    expect(not fc2['base_rate_downgrades'], '带 base_rate_ref 不应降级')


def test_self_grill_brief():
    import brief_lib as blf
    b = blf.new_brief('XX股份能买吗', report_no=9, mode='self')
    expect(b['mode'] == 'self', 'self 模式应记录')
    qs = [{'id': 'q%d' % i, 'q': '问题%d' % i, 'options': ['A', 'B']} for i in range(5)]
    blf.record_wave(b, qs,
                    [{'question_id': 'q1', 'answer': '买入决策', 'strength': '[代理推断·强]'}],
                    decisions=[{'field': 'purpose', 'value': '买入决策'}], actor='self')
    expect(b['waves'][0]['actor'] == 'self', 'self 波次应带 actor 标记')
    try:
        blf.self_approve(b)
        raise AssertionError('不完整 self brief 应拒绝自动批准')
    except ValueError:
        pass
    for field, val in [('report_type', '决策测算'), ('reader', '自己决策'),
                       ('key_concerns', ['方向结论', '风险点', '触发条件']),
                       ('failure_criteria', '方向错误即失败'), ('time_range', '1年'),
                       ('length_pref', '标准'), ('language', '中文'), ('flow_level', 'full')]:
        b['fields'][field] = val
    ap = blf.self_approve(b)
    expect(ap['approved'] and ap.get('auto') is True, 'self_approve 应自动批准')
    expect('self-grill' in ap.get('disclaimer', ''), '自动批准须带免责标注')
    s = blf.summary(b)
    expect('⚠' in s and '代理推导' in s, 'summary 应附免责头')
    b2 = blf.new_brief('普通路线', mode='user')
    try:
        blf.self_approve(b2)
        raise AssertionError('user 模式 brief 应拒绝 self_approve')
    except ValueError:
        pass


# ==================== 联网（--offline 跳过） ====================

def test_net_damodaran():
    import fetch_method_signals as fms
    d = fms.fetch_damodaran()
    expect('data_date' in d, 'Damodaran 数据日期缺失')
    print('  Damodaran 数据日期:', d.get('data_date'), 'riskfree:', d.get('riskfree_rate'))


def test_net_research_list():
    import fetch_method_signals as fms
    rows = fms.fetch_research_reports()
    expect(len(rows) > 0, '研报列表为空')
    expect(all('title' in r and 'infoCode' in r for r in rows[:3]), '研报字段缺失')
    print('  研报元数据 %d 条，示例: %s' % (len(rows), rows[0]['title'][:30]))


def test_net_usage_probe_small():
    import fetch_method_signals as fms
    rows = fms.fetch_research_reports()
    signals = {'research_reports': {'ok': True, 'data': rows}}
    from usage_probe import pick_reports, KEYWORDS
    reps = pick_reports(signals, 3, 15)
    expect(len(reps) > 0, '深度研报抽样为空')
    print('  抽样 %d 份（页数≥15），关键词定义 %d 组' % (len(reps), len(KEYWORDS)))


# ==================== 主流程 ====================

def main():
    shutil.rmtree(TMP, ignore_errors=True)
    os.makedirs(TMP, exist_ok=True)

    doc_tests = [test_new_document, test_cover_and_structure, test_para_heading_styles,
                 test_table_callout_img, test_setup_page, test_save_stage, test_save_json_meta,
                 test_plain_layout_elements, test_fig_table_numbering]
    chart_tests = [test_charts, test_diagram]
    pred_tests = [test_eval_pred_basic, test_profile_from_answers]
    derive_tests = [test_derive_a_share, test_derive_real_estate, test_derive_crypto,
                    test_derive_collectible, test_derive_unknown_profile,
                    test_dispute_trigger, test_dispute_consensus,
                    test_dispute_penalty_excluded, test_dispute_few_methods]
    lib_tests = [test_library_integrity, test_stats_baseline_universal]
    ops_tests = [test_cache_status, test_check_storage, test_check_delivery,
                 test_check_report_depth, test_depth_plain_checks]
    fc_tests = [test_forecast_equity, test_forecast_rental_and_balance]
    val_tests = [test_valuation_operators, test_valuation_crosscheck_flip]
    rev_tests = [test_review_dossier]
    thesis_tests = [test_thesis_lib, test_weighted_synthesis,
                    test_dossier_code_key_and_judgment, test_dump_markers, test_flow_log,
                    test_tree_diff_pdf_asof_error_patterns, test_update_report_derive]
    v2_tests = [test_report_depth_v2, test_dump_doc_text, test_trace_missing_files_fail]
    v3_tests = [test_workspace_registry, test_save_stage_report_no, test_brief_lib,
                test_technique_lib, test_ach_matrix, test_base_rate_downgrade,
                test_self_grill_brief]
    net_tests = [test_net_damodaran, test_net_research_list, test_net_usage_probe_small]

    groups = [
        ('docx_helpers', doc_tests),
        ('chart_helpers', chart_tests),
        ('profile_lib: 谓词', pred_tests),
        ('profile_lib: 推导', derive_tests),
        ('规则库完整性', lib_tests),
        ('缓存/防堆积/交付', ops_tests),
        ('forecast_lib: 盈利预测', fc_tests),
        ('valuation_lib: 估值算子', val_tests),
        ('review_lib: 复盘档案', rev_tests),
        ('thesis_lib/合成/导出', thesis_tests),
        ('check_report_depth v2', v2_tests),
        ('工作区/brief/技法', v3_tests),
    ]
    for title, tests in groups:
        print('== %s ==' % title)
        for t in tests:
            check(t.__name__, t)
    if not OFFLINE:
        print('== 联网（方法信号/取证） ==')
        for t in net_tests:
            check(t.__name__, t)
    else:
        print('== 联网（方法信号/取证） == SKIPPED (--offline)')

    print('\n== 结果：%d 通过，%d 失败 ==' % (len(PASSED), len(FAILED)))
    for name, err in FAILED:
        print('  失败项 %s: %s' % (name, err))
    shutil.rmtree(TMP, ignore_errors=True)
    sys.exit(1 if FAILED else 0)


if __name__ == '__main__':
    main()
