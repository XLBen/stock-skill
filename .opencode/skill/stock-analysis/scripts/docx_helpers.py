# -*- coding: utf-8 -*-
"""统一 Word 投资报告样式库（v3.2 深蓝投行风：海军蓝+钢蓝+浅蓝灰，通俗外挂层）。

用法：
    from docx_helpers import *
    doc = new_document()
    setup_page(doc, 'XX股份投资研究报告', '2026-08-20')   # 页眉+页码（首页自动跳过）
    cover(doc, 'XX股份（600000.SH）投资研究报告', subtitle='—— 副标题 ——',
          meta=['报告日期：2026年8月20日', '数据来源：...'], badge='个股深度研究')
    speedread_page(doc, headline='XX股份', rating_line='评级：增持｜现价 10.2｜区间 11~14 元',
                   reasons=['理由一…', '理由二…'], key_numbers=(['指标','值'], [['EPS','2.6']]),
                   fig_path='fig1.png', risks='最大风险…', bull='多头最强…', bear='空头最强…')
    h1(doc, '一、核心结论')
    para(doc, '专业论述段……', indent=True)
    plain_note(doc, '白话解读：这段说的是……', analogy=True)   # 【外挂】通俗层·逐段挂
    so_what(doc, '所以呢：这意味着……')                        # 【外挂】决策含义框
    faq_box(doc, '小白问：PE 是什么？', '答：市场愿意为 1 元年利润付多少钱…')
    method_card(doc, 'DCF 现金流折现', what='…', why='…', how_to_read='…')  # 三段式方法卡
    table_intro(doc, '这张表想说明：营收增速快于行业')          # 表前导语
    add_table(doc, ['列A', '列B'], [['v1', 'v2']], col_widths=[6, 6], font_size=9.5,
              caption='关键数据速览')                            # 自动编号 表N
    img(doc, 'fig1.png', width_cm=16, caption='营收趋势', source='公司公告')  # 自动编号 图N
    fig_table_list(doc)                                         # 附录·图表清单
    callout(doc, '评级：买入', color=MAROON)          # ★ 结论（浅蓝灰底+深蓝条）
    callout(doc, '风险提示', color=RED)               # ⚠ 风险（淡红底+红条）
    pagebreak(doc)
    save_stage(doc, '报告名_20260820.docx')           # 统一交付（禁止硬编码路径）

样式约定（v3.2 深蓝投行风，高盛/大摩参照）：
- 配色：海军蓝 NAVY 14315C（标题/表头/色带）、钢蓝 STEEL 5B87C6（装饰线）、
        浅蓝灰 CREAM EEF2F8（callout/元信息底）、ZEBRA EDF1F7（斑马纹）、
        正文 DARK 262626、风险 RED C0504D、沙金点缀 B08D4F（所以呢框/封面线）
- 通俗外挂层（v3.2）：plain_note 白话注块（浅蓝底+钢蓝条）、so_what 所以呢框（沙金底）、
        faq_box 小白问答框（白底虚线）、method_card 三段式方法卡（是什么/为什么/怎么读）、
        table_intro 表前导语；通俗层只是专业深度的外挂解释，判断权归专业层
- 正文：宋体 10.5~11pt + Times New Roman，行距 1.35，首行缩进 0.74cm，段后 8pt
- 标题：黑体加粗海军蓝，一级左侧 3pt 色条+底部钢蓝线，二级左侧细条
- 封面：顶部深蓝色带（徽章）+ 标题 + 钢蓝线 + 浅蓝灰元信息块 + 红色免责
- 表格：深蓝表头白字加粗、浅蓝灰斑马纹、首列加粗、cell 内边距、表头行高
- callout：单格着色表格 + 左侧色条 + 图标符号（★ 结论 / ⚠ 风险）
- 图片：居中 16cm，灰色 9pt 图注；图/表自动连续编号（图N/表N）+ 附录图表清单
"""
import math
import os
import re
from docx import Document
from docx.shared import Pt, Cm, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# ---- 深蓝投行配色（v3.2：高盛/大摩风） ----
NAVY = RGBColor(0x14, 0x31, 0x5C)   # 海军蓝：标题/表头/色带（原酒红位）
STEEL = RGBColor(0x5B, 0x87, 0xC6)  # 钢蓝：装饰线/次级点缀（原金位）
NAVY_HEX = '14315C'
STEEL_HEX = '5B87C6'
SAND_HEX = 'B08D4F'                 # 沙金：所以呢框条/封面装饰线（深蓝报告的暖点缀）
RED = RGBColor(0xC0, 0x50, 0x4D)    # 风险/免责
GREY = RGBColor(0x59, 0x59, 0x59)   # 次要信息
DARK = RGBColor(0x26, 0x26, 0x26)   # 正文近黑
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

# 兼容别名（v3.1 经典研报风名，值已并入深蓝系；新代码请用 NAVY/STEEL）
MAROON = NAVY
GOLD = STEEL
BLUE = NAVY
BLUE2 = STEEL

CREAM = 'EEF2F8'      # callout/元信息底（浅蓝灰）
ZEBRA = 'EDF1F7'      # 浅蓝灰斑马纹
WARN_FILL = 'FBE9E9'  # 风险 callout 底
NOTE_FILL = 'F0F4FA'  # 白话注块底
SOWHAT_FILL = 'FBF2DC'  # 所以呢框底（浅沙金）

PROJECT_ROOT = None


def _find_project_root():
    """自本文件向上定位项目根（.opencode/ 目录优先；兼容旧 暂存区+分类区 标记）。"""
    d = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    while True:
        parent = os.path.dirname(d)
        if parent == d:
            return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(d))))
        if os.path.isdir(os.path.join(d, '.opencode')):
            return d
        if os.path.isdir(os.path.join(d, '暂存区')) and os.path.isdir(os.path.join(d, '分类区')):
            return d
        d = parent


def project_root():
    """项目根目录（缓存）。"""
    global PROJECT_ROOT
    if PROJECT_ROOT is None:
        PROJECT_ROOT = _find_project_root()
    return PROJECT_ROOT


def stage_dir():
    """根暂存区目录（自动创建）。"""
    d = os.path.join(project_root(), '暂存区')
    os.makedirs(d, exist_ok=True)
    return d


def save_stage(doc, filename, subject=None, review=None, report_no=None):
    """统一交付。

    report_no（v3.0 推荐）：编号交付——保存 70_delivered 历史版本并双写
    reports/所有报告/{编号}_{名}.docx（最新版），注册表置 delivered。
    report_no 为空：兼容旧行为，写入项目根 暂存区/（存量流程兼容）。
    subject+review（结论 entry，字段见 review_lib.record）同时给出时自动落档资产档案。
    """
    base = os.path.basename(filename)
    if base != filename:
        raise ValueError('save_stage: filename 只接受文件名，不接受路径: %r' % filename)
    if report_no is not None:
        import workspace_lib
        hist = workspace_lib.history_path(report_no, base)
        os.makedirs(os.path.dirname(hist), exist_ok=True)
        doc.save(hist)
        latest = workspace_lib.deliver(report_no, hist, report_name=base)
        print('saved:', hist)
        print('delivered:', latest)
        if subject and review:
            try:
                import review_lib
                review_lib.record(subject, review, report_file=os.path.basename(latest),
                                  report_no=report_no)
                print('dossier updated:', subject)
            except Exception as e:
                print('warn: 档案落档失败（报告已保存）:', e)
        return hist
    path = os.path.join(stage_dir(), base)
    doc.save(path)
    print('saved:', path)
    if subject and review:
        try:
            import review_lib
            review_lib.record(subject, review, report_file=base)
            print('dossier updated:', subject)
        except Exception as e:
            print('warn: 档案落档失败（报告已保存）:', e)
    return path


def provenance_table(doc, results, font_size=8.5):
    """附录·数字溯源表：由 valuation_lib 结果自动生成（方法|区间/中枢|来源文件|字段|抓取时间）。"""
    rows = []
    for r in results:
        provs = r.get('provenance') or []
        if provs:
            for pv in provs:
                rows.append([r.get('method', '?'),
                             '%.4g~%.4g（中 %.4g）' % (r.get('low', 0), r.get('high', 0), r.get('central', 0)),
                             pv.get('file', ''), pv.get('field', ''), pv.get('fetched_at', '')])
        else:
            rows.append([r.get('method', '?'),
                         '%.4g~%.4g（中 %.4g）' % (r.get('low', 0), r.get('high', 0), r.get('central', 0)),
                         '（未登记来源）', '', ''])
    add_table(doc, ['方法', '区间（中枢）', '来源文件', '字段', '抓取时间'],
              rows, col_widths=[3.2, 4.2, 4.2, 2.2, 2.2], font_size=font_size)


def socratic_stats_table(doc, stats, font_size=9):
    """附录·审计统计表（单次审计）：stats={rounds, total, settled, revised, unknown, antinomy, rejected...}。"""
    rows = [
        ['审计轮数（上限 2）', str(stats.get('rounds', 0))],
        ['质询总数', str(stats.get('total', 0))],
        ['数据裁决（[实证]）', str(stats.get('settled', 0))],
        ['立论修正', str(stats.get('revised', 0))],
        ['留白（已知未知）', str(stats.get('unknown', 0))],
        ['二律背反记录', str(stats.get('antinomy', 0))],
        ['驳回（不合准入）', str(stats.get('rejected', 0))],
    ]
    if stats.get('readiness_issues'):
        rows.append(['火力下限', '；'.join(stats['readiness_issues'])])
    if stats.get('coverage_missing'):
        rows.append(['覆盖缺口', '；'.join(str(x) for x in stats['coverage_missing'])])
    add_table(doc, ['审计指标', '数量/说明'], rows, col_widths=[6, 4], font_size=font_size)


def manager_stats_table(doc, stats, font_size=9):
    """附录·管理员审问统计表（PUA 逐章"你都写了啥"，manager_log.stats() 输出）。"""
    rows = [
        ['审问人设', str(stats.get('persona', 'P7'))],
        ['审过章节', str(stats.get('sections', 0))],
        ['审问次数', str(stats.get('checkpoints', 0))],
        ['追问总数', str(stats.get('questions', 0))],
        ['过关', str((stats.get('by_verdict') or {}).get('过关', 0))],
        ['补证据', str((stats.get('by_verdict') or {}).get('补证据', 0))],
        ['驳回重写', str((stats.get('by_verdict') or {}).get('驳回重写', 0))],
        ['转审计未决', str(stats.get('escalated', 0))],
    ]
    add_table(doc, ['管理员审问', '统计'], rows, col_widths=[6, 4], font_size=font_size)


def _head_marker(text):
    """导出文本的标题级别标记（与 check_report_depth 的标题识别同源）。"""
    if re.match(r'^第[一二三四五六七八九十]+章', text):
        return 'H1'
    if re.match(r'^第[一二三四五六七八九十]+节', text):
        return 'H2'
    if re.match(r'^\d+\.\d+\.\d+', text):
        return 'H3'
    if re.match(r'^\d+\.\d+', text):
        return 'H2'
    if re.match(r'^(第[一二三四五六七八九十]+[章节]|[一二三四五六七八九十]+[、\.]|\d+[、\.])', text):
        return 'H1'
    if text.startswith(('★ ', '⚠ ')):
        return 'CALLOUT'
    return None


PLAIN_MARKS = ('白话解读｜', '所以呢｜', '小白问：', '看表先读：', '方法卡｜')


def _plain_marker(text):
    """v3.2 通俗外挂层标记识别（dump/QA 同源）。"""
    return any(text.startswith(m) or (m in text[:8]) for m in PLAIN_MARKS)


def dump_doc_text(doc_or_path, out_path):
    """docx → 带结构标记的纯文本（供校对质询子代理 Read，看得见文档骨架）。

    标记：【H1】【H2】【H3】标题、【CALLOUT】结论/风险块、【表】表格行、【图注】图注行。
    doc_or_path: Document 对象或 .docx 路径。返回 out_path。
    """
    if hasattr(doc_or_path, 'tables'):
        doc = doc_or_path
    else:
        from docx import Document
        doc = Document(doc_or_path)
    lines = []
    from docx.oxml.ns import qn
    body = doc.element.body
    for el in body.iterchildren():
        tag = el.tag.split('}')[-1]
        if tag == 'p':
            text = ''.join((t.text or '') for t in el.iter(qn('w:t'))).strip()
            if not text:
                continue
            mark = _head_marker(text)
            if re.match(r'^图\s*\d+', text) or re.match(r'^表\s*\d+', text):
                lines.append('【图注】' + text)
            elif _plain_marker(text):
                lines.append('【外挂】' + text)
            elif mark:
                lines.append('【%s】%s' % (mark, text))
            else:
                lines.append(text)
        elif tag == 'tbl':
            from docx.table import Table
            tbl = Table(el, doc)
            for row in tbl.rows:
                cells = [(c.text or '').strip().replace('\n', ' ') for c in row.cells]
                lines.append('【表】' + '\t'.join(cells))
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    return out_path


# ==================== 底层工具 ====================

def set_cn(run, font='宋体', size=11, bold=False, color=None, italic=False):
    """设置 run 字体：西文+中文字体、字号、加粗、斜体、颜色。"""
    run.font.name = font
    run._element.rPr.rFonts.set(qn('w:eastAsia'), font)
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    if color is not None:
        run.font.color.rgb = color
    return run


def _p_border(p, side, sz, color, space=4, val='single'):
    """段落单边边框（side: left/right/top/bottom；sz 单位 1/8pt）。"""
    pPr = p._p.get_or_add_pPr()
    pbdr = pPr.find(qn('w:pBdr'))
    if pbdr is None:
        pbdr = OxmlElement('w:pBdr')
        pPr.append(pbdr)
    el = OxmlElement('w:' + side)
    el.set(qn('w:val'), val)
    el.set(qn('w:sz'), str(sz))
    el.set(qn('w:space'), str(space))
    el.set(qn('w:color'), color)
    pbdr.append(el)


def _cell_margins(cell, top=0.08, bottom=0.08, left=0.12, right=0.12):
    """单元格内边距（cm）。"""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for tag, cmv in (('top', top), ('bottom', bottom), ('start', left), ('end', right)):
        node = OxmlElement('w:' + tag)
        node.set(qn('w:w'), str(int(cmv * 567)))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)


def _row_min_height(row, cmv):
    """行最小高度（cm）。"""
    trPr = row._tr.get_or_add_trPr()
    trHeight = OxmlElement('w:trHeight')
    trHeight.set(qn('w:val'), str(int(cmv * 567)))
    trHeight.set(qn('w:hRule'), 'atLeast')
    trPr.append(trHeight)


def new_document(font_size=11, line=1.3, margins=(2.4, 2.4, 2.4, 2.2)):
    """新建文档并设置全局 Normal 样式与页边距。"""
    doc = Document()
    for s in doc.sections:
        s.left_margin = Cm(margins[0]); s.right_margin = Cm(margins[1])
        s.top_margin = Cm(margins[2]); s.bottom_margin = Cm(margins[3])
    normal = doc.styles['Normal']
    normal.font.name = 'Times New Roman'
    normal.element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
    normal.font.size = Pt(font_size)
    normal.paragraph_format.line_spacing = line
    return doc


def setup_page(doc, header_text='投资研究报告', footer_date=None, header_left=None):
    """页眉页脚：页眉=标题（黑 8pt 灰+酒红细线），页脚=居中页码 — N —。
    封面页（首页）自动不显示页眉页脚（different_first_page）。
    """
    sec = doc.sections[0]
    sec.different_first_page_header_footer = True
    # 页眉
    hdr = sec.header
    hp = hdr.paragraphs[0]
    hp.paragraph_format.tab_stops.add_tab_stop(Cm(16.2), WD_ALIGN_PARAGRAPH.RIGHT)
    r1 = hp.add_run(header_left or header_text)
    set_cn(r1, font='黑体', size=8, color=GREY)
    if footer_date:
        r2 = hp.add_run('\t' + footer_date)
        set_cn(r2, font='宋体', size=8, color=GREY)
    _p_border(hp, 'bottom', 6, NAVY_HEX, space=2)
    # 页脚页码域
    ftr = sec.footer
    fp = ftr.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = fp.add_run('— ')
    set_cn(run, size=9, color=GREY)
    r = fp.add_run()
    fld_begin = OxmlElement('w:fldChar'); fld_begin.set(qn('w:fldCharType'), 'begin')
    instr = OxmlElement('w:instrText'); instr.text = 'PAGE'
    fld_end = OxmlElement('w:fldChar'); fld_end.set(qn('w:fldCharType'), 'end')
    r._r.append(fld_begin); r._r.append(instr); r._r.append(fld_end)
    set_cn(r, size=9, color=GREY)
    run2 = fp.add_run(' —')
    set_cn(run2, size=9, color=GREY)
    return sec


def para(doc, text='', size=10.5, bold=False, color=None, align=None,
          indent=False, space_after=8, font='宋体', line=1.35):
    """正文段落。indent=True 时首行缩进 0.74cm。v3.2：段后 8pt/行距 1.35（平板友好）。"""
    p = doc.add_paragraph()
    if indent:
        p.paragraph_format.first_line_indent = Cm(0.74)
    if align:
        p.alignment = align
    pf = p.paragraph_format
    pf.line_spacing = line
    pf.space_after = Pt(space_after)
    r = p.add_run(text)
    set_cn(r, font=font, size=size, bold=bold, color=color)
    return p


def rich(doc, parts, size=10.5, indent=True):
    """多段混合格式段落：parts = [(text, bold, color), ...]"""
    p = doc.add_paragraph()
    if indent:
        p.paragraph_format.first_line_indent = Cm(0.74)
    for text, bold, color in parts:
        r = p.add_run(text)
        set_cn(r, size=size, bold=bold, color=color)
    return p


def bullet(doc, text, bold_prefix=None, size=10.5):
    """项目符号段落，可选加粗前缀。"""
    p = doc.add_paragraph(style='List Bullet')
    if bold_prefix:
        r = p.add_run(bold_prefix)
        set_cn(r, size=size, bold=True, color=MAROON)
    r = p.add_run(text)
    set_cn(r, size=size)
    return p


def _heading_style(p, size, color, before, after):
    pf = p.paragraph_format
    pf.space_before = Pt(before); pf.space_after = Pt(after)
    pf.keep_with_next = True


def h1(doc, text, size=15):
    """一级标题：黑体酒红加粗，左侧 3pt 色条 + 底部金线。"""
    p = doc.add_paragraph()
    _heading_style(p, size, MAROON, 16, 10)
    _p_border(p, 'left', 22, NAVY_HEX, space=3)
    _p_border(p, 'bottom', 6, STEEL_HEX, space=2)
    r = p.add_run(text)
    set_cn(r, font='黑体', size=size, bold=True, color=MAROON)
    return p


def h2(doc, text, size=12.5):
    """二级标题：黑体酒红加粗，左侧细条。"""
    p = doc.add_paragraph()
    _heading_style(p, size, MAROON, 12, 8)
    _p_border(p, 'left', 10, NAVY_HEX, space=3)
    r = p.add_run(text)
    set_cn(r, font='黑体', size=size, bold=True, color=MAROON)
    return p


def h3(doc, text, size=11):
    """三级标题：黑体加粗深灰，左侧金线。"""
    p = doc.add_paragraph()
    _heading_style(p, size, DARK, 10, 5)
    _p_border(p, 'left', 6, STEEL_HEX, space=3)
    r = p.add_run(text)
    set_cn(r, font='黑体', size=size, bold=True, color=DARK)
    return p


def shade(cell, hexcolor):
    """单元格底纹。"""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear'); shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), hexcolor)
    tcPr.append(shd)


def add_table(doc, headers, rows, col_widths=None, font_size=9.5,
              header_fill=None, zebra=True, aligns=None, caption=None):
    """标准表格：headers 列表 + rows 二维列表。
    - 表头深蓝底白字加粗 + 行高加宽
    - 奇数行浅蓝灰斑马纹；首列加粗深灰
    - cell 内边距；aligns：每列对齐（默认首列左对齐、其余居中）
    - caption：表题，自动编号"表N"（灰字居中，券商惯例）
    """
    if header_fill is None:
        header_fill = NAVY_HEX
    if not headers:
        raise ValueError('add_table: headers 不能为空')
    if aligns is not None:
        aligns = list(aligns) + [WD_ALIGN_PARAGRAPH.CENTER] * (len(headers) - len(aligns))
    t = doc.add_table(rows=len(rows) + 1, cols=len(headers))
    t.style = 'Table Grid'
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for j, htext in enumerate(headers):
        cell = t.cell(0, j); cell.text = ''
        _cell_margins(cell)
        p = cell.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(str(htext))
        set_cn(r, size=font_size, bold=True, color=WHITE)
        shade(cell, header_fill)
    _row_min_height(t.rows[0], 0.55)
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = t.cell(i + 1, j); cell.text = ''
            _cell_margins(cell)
            p = cell.paragraphs[0]
            if aligns:
                p.alignment = aligns[j]
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER if j > 0 else WD_ALIGN_PARAGRAPH.LEFT
            r = p.add_run(str(val))
            if j == 0:
                set_cn(r, size=font_size, bold=True, color=DARK)
            else:
                set_cn(r, size=font_size)
            if zebra and i % 2 == 1:
                shade(cell, ZEBRA)
    if col_widths:
        for j, w in enumerate(col_widths):
            for i in range(len(rows) + 1):
                t.cell(i, j).width = Cm(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    if caption:
        _register_table_caption(doc, caption)
    return t


def table_from(doc, df, headers=None, col_widths=None, font_size=9.5,
               header_fill=None, zebra=True, caption=None):
    """DataFrame 直接成表（NaN/None 显示为 —）。"""
    if headers is None:
        headers = list(df.columns)
    rows = []
    for r in df.itertuples(index=False):
        row = []
        for v in r:
            if v is None or (isinstance(v, float) and math.isnan(v)):
                row.append('—')
            else:
                row.append(v)
        rows.append(row)
    return add_table(doc, headers, rows, col_widths=col_widths,
                     font_size=font_size, header_fill=header_fill, zebra=zebra,
                     caption=caption)


def callout(doc, text, fill=None, color=None, bold=True, icon=True):
    """单格着色提示框：★ 结论（浅蓝灰底+深蓝条）/ ⚠ 风险（淡红底+红条）。

    color=RED 视为风险型；color=None 或 NAVY/MAROON 视为结论型；显式 fill 时尊重调用者。
    """
    is_risk = color is RED
    if fill is None:
        fill = WARN_FILL if is_risk else CREAM
    if color is None:
        color = RED if is_risk else MAROON
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = t.cell(0, 0); cell.text = ''
    _cell_margins(cell, 0.1, 0.1, 0.18, 0.18)
    p = cell.paragraphs[0]; p.paragraph_format.line_spacing = 1.3
    prefix = ('⚠ ' if is_risk else '★ ') if icon else ''
    r = p.add_run(prefix + text)
    set_cn(r, size=10.5, color=color, bold=bold)
    shade(cell, fill)
    # 左侧色条（cell 左边框加粗）
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = OxmlElement('w:tcBorders')
    left = OxmlElement('w:left')
    left.set(qn('w:val'), 'single'); left.set(qn('w:sz'), '24')
    left.set(qn('w:space'), '0')
    left.set(qn('w:color'), 'C0504D' if is_risk else NAVY_HEX)
    tcBorders.append(left)
    tcPr.append(tcBorders)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def img(doc, path, width_cm=16.0, caption=None, source=None):
    """居中插图 + 灰色 9pt 图注。source 传入时图注自动追加'资料来源'（专业研报惯例，QA 检查项）。
    v3.2：caption 自动连续编号"图N　…"（已是"图N"开头的题注不重复编号）。"""
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run()
    run.add_picture(path, width=Cm(width_cm))
    if caption:
        no = _claim_fig_no(doc, caption)
        if no is not None:
            caption = '图%d　%s' % (no, caption)
        if source:
            caption = '%s（资料来源：%s）' % (caption, source)
        c = doc.add_paragraph(); c.alignment = WD_ALIGN_PARAGRAPH.CENTER
        c.paragraph_format.space_after = Pt(10)
        r = c.add_run(caption)
        set_cn(r, size=9, color=GREY)


def data_asof_table(doc, rows, font_size=8.5):
    """附录·数据截止时间表：rows 来自 fetch_lib.cache_meta_table（文件|抓取时间|TTL|scope|source）。"""
    add_table(doc, ['数据文件', '抓取时间', 'TTL(h)', 'scope', '来源'],
              rows, col_widths=[4.6, 3.0, 1.4, 3.4, 2.6], font_size=font_size)


# ==================== v3.2 通俗外挂层 + 图表编号 ====================
# 设计原则（grill 2026-10-04 批准）：通俗只是专业深度的外挂解释层，
# 判断权归专业层；通俗层数字必须与专业层一致（QA 硬检查）。

_DOC_NO_STATE = {}   # id(doc) -> {'fig': n, 'tab': n, 'items': [(type, no, title)]}


def _no_state(doc):
    return _DOC_NO_STATE.setdefault(id(doc), {'fig': 0, 'tab': 0, 'items': []})


def reset_numbering(doc=None):
    """清除图表编号状态（同进程内新建文档前调用一次最稳）。"""
    if doc is None:
        _DOC_NO_STATE.clear()
    else:
        _DOC_NO_STATE.pop(id(doc), None)


def _claim_fig_no(doc, caption):
    """caption 未带"图N"时分配下一个图号；已带则同步计数器并返回 None。"""
    st = _no_state(doc)
    m = re.match(r'^图\s*(\d+)', caption or '')
    if m:
        no = int(m.group(1))
        st['fig'] = max(st['fig'], no)
        st['items'].append(('图', no, re.sub(r'^图\s*\d+[\s　]*', '', caption)))
        return None
    st['fig'] += 1
    st['items'].append(('图', st['fig'], caption))
    return st['fig']


def _register_table_caption(doc, caption):
    """表题登记 + 自动"表N"编号（灰字居中，券商惯例）。"""
    st = _no_state(doc)
    m = re.match(r'^表\s*(\d+)', caption or '')
    if m:
        no = int(m.group(1))
        st['tab'] = max(st['tab'], no)
        title = re.sub(r'^表\s*\d+[\s　]*', '', caption)
    else:
        st['tab'] += 1
        no = st['tab']
        title = caption
    st['items'].append(('表', no, title))
    c = doc.add_paragraph(); c.alignment = WD_ALIGN_PARAGRAPH.CENTER
    c.paragraph_format.space_after = Pt(8)
    r = c.add_run('表%d　%s' % (no, title))
    set_cn(r, size=9, color=GREY)


def fig_table_list(doc, font_size=9):
    """附录·图表清单：登记过的图/表汇总成表（券商标配，平板回翻友好）。"""
    items = _no_state(doc)['items']
    if not items:
        return None
    rows = [['%s%d' % (t, no), title, '数据图/表' if t == '表' else '图']
            for t, no, title in items]
    return add_table(doc, ['编号', '标题', '类型'],
                     [[r[0], r[1], r[2]] for r in rows],
                     col_widths=[2.2, 10.6, 3.0], font_size=font_size)


def _plain_box(doc, prefix, text, fill, bar_hex, size=9.5, color=None,
               bold_prefix=True, extra_runs=None, dashed=False):
    """通俗外挂层通用底座：单格着色表格 + 左侧色条 + 加粗前缀。"""
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = t.cell(0, 0); cell.text = ''
    _cell_margins(cell, 0.08, 0.08, 0.15, 0.15)
    p = cell.paragraphs[0]; p.paragraph_format.line_spacing = 1.3
    r1 = p.add_run(prefix)
    set_cn(r1, size=size, bold=bold_prefix, color=color or NAVY)
    r2 = p.add_run(text)
    set_cn(r2, size=size, bold=False, color=DARK)
    if extra_runs:
        for txt, sz, clr in extra_runs:
            rr = p.add_run(txt)
            set_cn(rr, size=sz, bold=False, color=clr)
    shade(cell, fill)
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = OxmlElement('w:tcBorders')
    for side in ('left', 'top', 'bottom', 'right'):
        el = OxmlElement('w:' + side)
        if dashed and side != 'left':
            el.set(qn('w:val'), 'dashed'); el.set(qn('w:sz'), '6')
            el.set(qn('w:color'), STEEL_HEX)
        else:
            el.set(qn('w:val'), 'single')
            el.set(qn('w:sz'), '24' if side == 'left' else '4')
            el.set(qn('w:color'), bar_hex if side == 'left' else
                   ('FFFFFF' if not dashed else STEEL_HEX))
        el.set(qn('w:space'), '0')
        tcBorders.append(el)
    tcPr.append(tcBorders)
    doc.add_paragraph().paragraph_format.space_after = Pt(3)
    return t


def plain_note(doc, text, analogy=False):
    """【白话解读】注块：专业论述段后紧跟的通俗解释（逐段外挂，v3.2 排版件）。
    analogy=True 表示含生活化比喻，自动追加免责小字（比喻仅为助记，严格定义见方法卡）。"""
    extra = [('　※ 比喻仅为助记，严格定义见方法卡/术语注', 8.5, GREY)] if analogy else None
    return _plain_box(doc, '白话解读｜', text, NOTE_FILL, STEEL_HEX,
                      extra_runs=extra)


def so_what(doc, text):
    """【所以呢】框：关键结论/数字对读者钱袋意味着什么（决策含义，沙金底）。"""
    return _plain_box(doc, '所以呢｜', text, SOWHAT_FILL, SAND_HEX,
                      bold_prefix=True, color=RGBColor(0x8A, 0x66, 0x1F))


def faq_box(doc, question, answer):
    """【小白问】自问答框：白底虚线，预判非专业读者的典型疑问（管理员扮问产出）。"""
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = t.cell(0, 0); cell.text = ''
    _cell_margins(cell, 0.08, 0.08, 0.15, 0.15)
    p1 = cell.paragraphs[0]; p1.paragraph_format.line_spacing = 1.3
    r = p1.add_run('小白问：'); set_cn(r, size=9.5, bold=True, color=NAVY)
    r = p1.add_run(question); set_cn(r, size=9.5, bold=True, color=DARK)
    p2 = cell.add_paragraph(); p2.paragraph_format.line_spacing = 1.3
    r = p2.add_run('答：'); set_cn(r, size=9.5, bold=True, color=STEEL)
    r = p2.add_run(answer); set_cn(r, size=9.5, bold=False, color=DARK)
    shade(cell, 'FFFFFF')
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = OxmlElement('w:tcBorders')
    for side in ('top', 'bottom', 'left', 'right'):
        el = OxmlElement('w:' + side)
        el.set(qn('w:val'), 'dashed' if side != 'left' else 'single')
        el.set(qn('w:sz'), '6' if side != 'left' else '18')
        el.set(qn('w:space'), '0')
        el.set(qn('w:color'), STEEL_HEX)
        tcBorders.append(el)
    tcPr.append(tcBorders)
    doc.add_paragraph().paragraph_format.space_after = Pt(3)
    return t


def table_intro(doc, text):
    """表前导语：每张表前一句"这张表想说明什么"（反表格轰炸排版件）。"""
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(3)
    r = p.add_run('看表先读：')
    set_cn(r, size=9.5, bold=True, italic=True, color=GREY)
    r = p.add_run(text)
    set_cn(r, size=9.5, italic=True, color=GREY)
    return p


def method_card(doc, name, what, why, how_to_read, font_size=9.5):
    """三段式方法卡：每个估值方法/技法首次出现处挂"是什么/为什么用它/结果怎么读"。
    技法本身仍按注册表协议执行——本卡只负责让非专业读者看懂它在干什么。"""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(3)
    r = p.add_run('方法卡｜%s' % name)
    set_cn(r, font='黑体', size=10, bold=True, color=NAVY)
    return add_table(doc, ['方法卡', name],
                     [['是什么', what], ['为什么用它', why], ['结果怎么读', how_to_read]],
                     col_widths=[3.2, 12.6], font_size=font_size)


def speedread_page(doc, headline, rating_line, reasons, key_numbers=None,
                   fig_path=None, fig_caption=None, risks=None, bull=None,
                   bear=None, footer_note='详细论证见后文各章', fig_width_cm=13.0):
    """30秒速读一页纸（封面后第一页，晨报纪要风）：
    结论区（评级 callout）+ 理由速览（论点树承重柱一句话版）+ 关键数字小表
    + 主图 + 风险与多空各一条。一页放完。"""
    h1(doc, '30秒速读｜%s' % headline)
    if rating_line:
        callout(doc, rating_line)
    if reasons:
        h3(doc, '为什么？核心理由')
        for i, r in enumerate(reasons, 1):
            bullet(doc, r, bold_prefix='理由%d：' % i, size=9.5)
    if key_numbers is not None:
        headers, rows = key_numbers
        table_intro(doc, '关键数字一览（口径与来源见附录溯源表）')
        add_table(doc, headers, rows, font_size=9, caption='速读关键数字')
    if fig_path:
        img(doc, fig_path, width_cm=fig_width_cm,
            caption=fig_caption or '%s一览' % headline)
    if risks or bull or bear:
        h3(doc, '风险与多空')
        for label, txt, clr in (('最大风险：', risks, RED),
                                ('多头最强论点：', bull, NAVY),
                                ('空头最强论点：', bear, RED)):
            if txt:
                rich(doc, [(label, True, clr), (txt, False, DARK)], indent=False)
    if footer_note:
        p = para(doc, footer_note, size=8.5, color=GREY, align=WD_ALIGN_PARAGRAPH.RIGHT)
        p.paragraph_format.space_before = Pt(4)
    pagebreak(doc)


def cover(doc, title, subtitle=None, meta=None, disclaim=None, badge=None,
          title_size=28, subtitle_size=13):
    """深蓝投行封面：顶部深蓝色带（徽章）→ 标题 → 钢蓝线 → 副标题
    → 浅蓝灰元信息块 → 红色免责声明。"""
    band = doc.add_table(rows=1, cols=1)
    band.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = band.cell(0, 0); cell.text = ''
    p = cell.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(badge or '投 资 研 究 报 告')
    set_cn(r, font='黑体', size=12, bold=True, color=WHITE)
    shade(cell, NAVY_HEX)
    _row_min_height(band.rows[0], 0.9)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    for _ in range(4):
        doc.add_paragraph()
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_cn(p.add_run(title), font='黑体', size=title_size, bold=True, color=NAVY)
    _p_border(p, 'bottom', 10, STEEL_HEX, space=6)
    doc.add_paragraph()
    if subtitle:
        p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        set_cn(p.add_run(subtitle), font='微软雅黑', size=subtitle_size, color=GREY)
    for _ in range(2):
        doc.add_paragraph()
    if meta:
        mt = doc.add_table(rows=len(meta), cols=1)
        mt.alignment = WD_TABLE_ALIGNMENT.CENTER
        for i, line in enumerate(meta):
            c = mt.cell(i, 0); c.text = ''
            _cell_margins(c, 0.07, 0.07, 0.15, 0.15)
            cp = c.paragraphs[0]; cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            set_cn(cp.add_run(line), size=10.5, color=GREY)
            shade(c, CREAM)
    for _ in range(4):
        doc.add_paragraph()
    if disclaim:
        p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        set_cn(p.add_run(disclaim), size=10, color=RED)
    pagebreak(doc)


def pagebreak(doc):
    doc.add_page_break()


def spacer(doc, size=6):
    """小号空行，用于表格间留白。"""
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(size)


def save(doc, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    doc.save(path)
    print('saved:', path)
