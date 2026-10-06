# -*- coding: utf-8 -*-
"""报告深度与证据质检 v2：从"数字数 lint"升级为"数证据对象"。

用法：
    python scripts/check_report_depth.py <报告.docx> [--type 蓝图id] [--min N] [--trace-dir 数据目录]

检查项：
[错误] 空章节：标题后无正文/表格/图片（标题紧跟标题）
[错误] 字数不足：低于 min_words（默认 8000；--min/--type 可覆盖）。字数不足的解法是
       补新论点+新数据源，禁止扩写现有文本注水（见输出提示）
[错误] 强制章节缺失：调研过程与方法 / 关键假设有效性评估 / 发散检验
[错误] 蓝图必备章缺失：--type 指定时按蓝图检查核心章（如 equity_deep_8ch 的"盈利预测"）
[错误] 数字溯源不通过：--trace-dir 下 results_*/forecast_* 数字池可用时，
       报告表格关键数字命中率 <35%
[警告] 图表未被引用：文档中的图未被正文"图N"引用
[警告] 证据标签缺失：投资类报告 [实证]/[推断]/[观点] 标签总数 <5
[警告] 数字密度低：含具体数字的正文段落占比 <40%
[警告] 裸（估）过多：>10 处（估）且无'概率依据/历史频率/发生概率'字样
[警告] 缺盲点清单 / 缺基准·机会成本 / 缺反方章节关键词
[错误] 通俗层数字与专业层不一致（v3.2）：白话解读/所以呢/小白问框内数字
       未出现在正文或表格——通俗只是专业深度的外挂，无权引入新数字
[警告] 缺速读页"30秒速读" / 通俗覆盖不足（方法卡/白话注/FAQ 数量低于阈值，
       v3.2 layout_rules 要求；minimal 级无 PUA 由本检查兜底）
[信息] 各章节字数分布（定位薄弱章节：补新论点，不是扩写）

min_words 来源：--type 蓝图 id > --min 显式值 > 默认 8000。退出码：错误=1，仅警告=0。
"""
import glob
import json
import math
import os
import re
import sys

HEAD_RE = re.compile(r'^(第[一二三四五六七八九十]+[章节]|[一二三四五六七八九十]+[、\.]|\d+(\.\d+)*[、\.\s])')
# v3.2 通俗外挂层标记（与 docx_helpers.PLAIN_MARKS 同源）
PLAIN_MARKS = ('白话解读｜', '所以呢｜', '小白问：', '看表先读：', '方法卡｜')
DEFAULT_MIN_WORDS = 8000
LIB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'reference', 'library', 'blueprints.json')
REQUIRED = {
    'research_process': ['调研过程', '调研源清单', '盲点', '未查到'],
    'assumption_validity': ['假设有效性', '失效信号', '发生概率'],
    'divergent_views': ['历史类比', '反事实', '机会成本'],
}
REQUIRED_BY_TYPE = {
    'equity_deep_8ch': [('盈利预测', ['盈利预测', 'EPS 预测', '预测汇总']),
                        ('风险提示', ['风险提示', '风险因素']),
                        ('反方论点', ['反方论点', '最强看空', '质询'])],
    'asset_research': [('供需平衡', ['供需平衡', '供给增量']),
                       ('风险提示', ['风险提示', '风险因素']),
                       ('反方论点', ['反方论点', '最强看空', '质询'])],
    'rental_asset': [('NOI预测', ['NOI', '租金.*预测', '净运营收益']),
                     ('风险提示', ['风险提示', '风险因素']),
                     ('反方论点', ['反方论点', '最强看空', '质询'])],
    'theme_quant': [('策略逻辑', ['为什么有效', '策略逻辑', '经济逻辑']),
                    ('基准对比', ['基准', '买入持有', '对比']),
                    ('失效边界', ['失效', '适用条件'])],
    'decision_report': [('不可逆性', ['不可逆', '可撤回', '可逆'])],
}
INVESTMENT_TYPES = ('equity_deep_8ch', 'asset_research', 'rental_asset', 'theme_quant')
NUM_RE = re.compile(r'\d+(?:\.\d+)?')


def _iter_items(doc):
    from docx.oxml.ns import qn
    body = doc.element.body
    for el in body.iterchildren():
        tag = el.tag.split('}')[-1]
        if tag == 'p':
            text = ''.join((t.text or '') for t in el.iter(qn('w:t'))).strip()
            yield 'p', text
        elif tag == 'tbl':
            yield 'tbl', ''
        elif tag == 'sectPr':
            yield 'sect', ''


def _is_head(text):
    if not text or len(text) > 45:
        return False
    return bool(HEAD_RE.match(text)) or text.startswith(('★ ', '⚠ '))


def _level(text):
    """标题级数：0=分组级（第一节，不参与空章节判定），1=一级，2=二级，3=三级。"""
    if re.match(r'^第[一二三四五六七八九十]+节', text):
        return 0
    if re.match(r'^\d+\.\d+\.\d+', text):
        return 3
    if re.match(r'^\d+\.\d+', text):
        return 2
    if re.match(r'^(第[一二三四五六七八九十]+[章节]|[一二三四五六七八九十]+[、\.]|\d+[、\.])', text):
        return 1
    return 2


def _count_images(doc):
    from docx.oxml.ns import qn
    return sum(1 for el in doc.element.body.iter() if el.tag.split('}')[-1] == 'drawing')


def _blueprint_min_words(blp_id):
    try:
        with open(LIB_PATH, 'r', encoding='utf-8') as f:
            lib = json.load(f)
        for b in lib.get('blueprints', []):
            if b.get('id') == blp_id:
                return b.get('min_words') or DEFAULT_MIN_WORDS
    except Exception:
        pass
    return DEFAULT_MIN_WORDS


# ==================== 数字溯源 ====================

def _pool_from_file(path, pool, depth=0):
    """递归收集数值叶子 → 数字池（含 ×100 / ÷100 变体，容纳百分比口径）。"""
    if depth > 6:
        return
    try:
        with open(path, 'r', encoding='utf-8') as f:
            obj = json.load(f)
    except Exception:
        return
    stack = [obj]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            stack.extend(cur.values())
        elif isinstance(cur, list):
            stack.extend(cur)
        elif isinstance(cur, bool):
            continue
        elif isinstance(cur, (int, float)) and math.isfinite(cur) and abs(cur) >= 0.01:
            pool.add(round(float(cur), 4))
            pool.add(round(float(cur) * 100, 4))
            pool.add(round(float(cur) / 100.0, 4))


def _pool_matches(value, pool):
    for p in pool:
        tol = max(0.051, abs(p) * 0.008)
        if abs(value - p) <= tol:
            return True
    return False


def trace_numbers(texts, trace_dir):
    """报告关键数字（表格行+正文证据句）vs results_*/forecast_* 数字池 → {hit_rate, unmatched}。"""
    files = []
    for pat in ('results_*.json', 'forecast_*.json'):
        files.extend(glob.glob(os.path.join(trace_dir, pat)))
    if not files:
        return None
    pool = set()
    for fp in files:
        _pool_from_file(fp, pool)
    if not pool:
        return None
    nums = []
    for text in texts:
        for m in NUM_RE.findall(text):
            try:
                v = float(m)
            except ValueError:
                continue
            if v >= 0.01:
                nums.append(v)
    if not nums:
        return None
    unmatched = [v for v in nums if not _pool_matches(v, pool)]
    hit_rate = 1.0 - len(unmatched) / len(nums)
    return {'pool_size': len(pool), 'n': len(nums), 'hit_rate': round(hit_rate, 4),
            'unmatched_sample': sorted(set(unmatched), reverse=True)[:5]}


def _evidence_sentences(paras, limit=40):
    """正文证据句抽样：含数字且带计量单位的句子（纯年份剔除——那是日期不是证据）。"""
    out = []
    for t in paras:
        if len(t) < 10 or not re.search(r'\d', t):
            continue
        if not any(u in t for u in ('亿', '万', '倍', '%', '元')):
            continue
        cleaned = re.sub(r'(19|20)\d{2}', ' ', t)
        if re.search(r'\d', cleaned):
            out.append(cleaned)
        if len(out) >= limit:
            break
    return out


def _has_valuation_numbers(full):
    """报告是否含估值/预测特征数字（用于'无算子输出文件'违规判定）。"""
    return bool(re.search(r'\d', full)) and any(
        k in full for k in ('中枢', '区间', '目标价', '合理价', '估值'))


def _table_texts(doc):
    out = []
    for tbl in doc.tables:
        for row in tbl.rows:
            for cell in row.cells:
                out.append(cell.text or '')
    return out


# ==================== 主检查 ====================

def check_docx(path, min_words=None, rtype=None, trace_dir=None):
    from docx import Document
    doc = Document(path)
    items = list(_iter_items(doc))
    paras = [t for kind, t in items if kind == 'p' and t]

    total = sum(len(t) for t in paras)
    heads = [(i, t) for i, (kind, t) in enumerate(items) if kind == 'p' and _is_head(t)]

    errors, warns = [], []
    per_section = []
    for idx, (i, t) in enumerate(heads):
        nxt = heads[idx + 1][0] if idx + 1 < len(heads) else len(items)
        words = sum(len(tt) for kind, tt in items[i + 1:nxt] if kind == 'p')
        per_section.append((t, words))

    # 1. 空章节
    empty = []
    for idx, (i, t) in enumerate(heads):
        lv = _level(t)
        if lv == 0:
            continue
        j = i + 1
        has_content = False
        while j < len(items):
            kind, tt = items[j]
            if kind == 'p' and tt and _is_head(tt) and _level(tt) <= lv:
                break
            if kind in ('p', 'tbl') and (kind != 'p' or tt):
                has_content = True
                break
            j += 1
        if not has_content:
            empty.append(t)
    if empty:
        errors.append('空章节: %s' % ' | '.join(empty[:8]))

    # 2. 字数（不足 → 补新论点+新数据源，不是扩写）
    minw = min_words or (_blueprint_min_words(rtype) if rtype else DEFAULT_MIN_WORDS)
    if total < minw:
        errors.append('字数不足: %d < %d —— 解法：为新章节/薄弱章节补新论点+新数据源'
                      '（新抓取/新视角/新对比），禁止扩写现有文本注水' % (total, minw))

    full = '\n'.join(paras)

    # 3. 强制章节
    for key, kws in REQUIRED.items():
        if not any(k in full for k in kws):
            errors.append('强制章节缺失: %s（需含 %s）' % (key, '/'.join(kws)))

    # 4. 蓝图必备章（--type 时）
    if rtype and rtype in REQUIRED_BY_TYPE:
        for name, kws in REQUIRED_BY_TYPE[rtype]:
            if not any(re.search(k, full) for k in kws):
                errors.append('蓝图必备章缺失: %s（需含 %s）' % (name, '/'.join(kws)))

    # 5. 数字溯源（表格+正文证据句 vs results/forecast 池）
    if trace_dir:
        tr = trace_numbers(_table_texts(doc) + _evidence_sentences(paras), trace_dir)
        if tr:
            if tr['hit_rate'] < 0.35:
                errors.append('数字溯源不通过: 关键数字命中率 %.0f%% < 35%%'
                              '（数字池 %d 个，未命中样例 %s）——报告数字必须出自算子/预测输出'
                              % (tr['hit_rate'] * 100, tr['pool_size'], tr['unmatched_sample']))
            elif tr['hit_rate'] < 0.60:
                warns.append('数字溯源偏弱: 命中率 %.0f%%（未命中样例 %s）'
                             % (tr['hit_rate'] * 100, tr['unmatched_sample']))
        elif rtype in INVESTMENT_TYPES and _has_valuation_numbers(full):
            errors.append('数字来源缺失: 报告含估值/预测特征数字，但 %s 无 results_*/forecast_* '
                          '算子输出文件——禁止凭空写数字（先跑 forecast_lib/valuation_lib 落盘）'
                          % trace_dir)

    # 6. 图表引用（每个图被正文"图N"引用）+ 图注资料来源
    n_img = _count_images(doc)
    cited = set()
    for m in re.findall(r'图\s*(\d+)', full):
        cited.add(int(m))
    if n_img and len(cited) < n_img:
        warns.append('图表未被正文引用: 共 %d 图，仅 %d 个图号被引用（图注编号需被正文提及）'
                     % (n_img, len(cited)))
    captions = [t for t in paras if re.match(r'^图\s*\d+', t)]
    no_src = [c for c in captions if '来源' not in c]
    if captions and len(no_src) == len(captions):
        warns.append('图注全部缺资料来源（img(source=...) 自动追加，专业研报惯例）')

    # 7. 证据标签（投资类）
    n_tags = sum(full.count(t) for t in ('[实证]', '[推断]', '[观点]', '（实证）', '（推断）', '（观点）'))
    if rtype in INVESTMENT_TYPES and n_tags < 5:
        warns.append('证据标签过少: %d 处 [实证]/[推断]/[观点]（投资类建议 ≥5，关键假设必须标注）' % n_tags)

    # 8. 数字密度
    body_paras = [t for t in paras if not _is_head(t) and len(t) >= 20]
    with_num = [t for t in body_paras if re.search(r'\d+(?:\.\d+)?', t)]
    density = len(with_num) / len(body_paras) if body_paras else 0.0
    if body_paras and density < 0.40:
        warns.append('数字密度低: %d%% 段落含具体数字（低于40%%，论点缺数据支撑——补数据而非补字）'
                     % round(density * 100))

    # 9. 裸（估）
    n_gu = full.count('（估）') + full.count('(估)')
    has_prob = any(k in full for k in ('概率依据', '历史频率', '发生概率', '概率约', '概率加权'))
    if n_gu > 10 and not has_prob:
        warns.append('裸（估）%d 处且无概率依据字样' % n_gu)

    # 10. 盲点 / 基准 / 反方
    if not any(k in full for k in ('盲点', '未查到')):
        warns.append('缺盲点/未查到清单')
    if not any(k in full for k in ('机会成本', '相对基准', '与同期', '对比表')):
        warns.append('缺相对基准/机会成本对比')
    if rtype in INVESTMENT_TYPES and not any(k in full for k in ('反方', '看空', '质询')):
        warns.append('缺反方论点/质询记录（应由苏格拉底质询记录驱动，禁止自写自答）')

    # 11. 通俗外挂层（v3.2）：通俗层数字必须与专业层一致（通俗无权引入新数字）
    all_texts = paras + _table_texts(doc)
    plain_texts = [t for t in all_texts if any(m in t for m in PLAIN_MARKS)]
    body_texts = [t for t in all_texts if not any(m in t for m in PLAIN_MARKS)]
    body_nums = set()
    for t in body_texts:
        for m in NUM_RE.findall(re.sub(r'(19|20)\d{2}', ' ', t)):
            try:
                v = float(m)
            except ValueError:
                continue
            if v >= 0.01:
                body_nums.add(round(v, 2))
    unmatched = []
    for t in plain_texts:
        if '秒' in t[:12]:   # "30秒速读"类框题不算数字载体
            continue
        for m in NUM_RE.findall(re.sub(r'(19|20)\d{2}', ' ', t)):
            try:
                v = float(m)
            except ValueError:
                continue
            if v < 0.01:
                continue
            if not any(abs(v - b) <= max(0.051, abs(b) * 0.008) for b in body_nums):
                unmatched.append((t[:24], m))
    if unmatched:
        errors.append('通俗层数字与专业层不一致: %d 处（白话/所以呢/小白问框内数字'
                      '必须出自正文或表格，通俗层无权引入新数字）样例: %s'
                      % (len(unmatched), unmatched[:3]))

    # 12. 速读页与通俗覆盖（v3.2 排版件；minimal 级无 PUA，由本检查兜底）
    if '30秒速读' not in full:
        warns.append('缺速读页：封面后第一页应有"30秒速读"一页纸（speedread_page）')
    n_cards = full.count('方法卡｜')
    n_notes = sum(full.count(m) for m in ('白话解读｜', '所以呢｜'))
    n_faq = full.count('小白问：')
    if rtype in INVESTMENT_TYPES and (n_cards < 2 or n_notes < 5):
        warns.append('通俗覆盖不足: 方法卡 %d 张（建议≥2，每个激活技法首现处挂卡）、'
                     '白话/所以呢 %d 条（建议≥5，承重论述段逐段外挂）——技法全保留，'
                     '呈现按 layout_rules' % (n_cards, n_notes))
    if rtype in INVESTMENT_TYPES and n_faq < 1:
        warns.append('缺 FAQ 小白问答框（管理员扮问产出，每报告≥1）')

    return {'total_chars': total, 'tables': len(doc.tables),
            'images': n_img, 'empty': empty, 'per_section': per_section,
            'tag_count': n_tags, 'digit_density': round(density, 4),
            'plain_blocks': {'method_cards': n_cards, 'plain_notes': n_notes,
                             'faq': n_faq, 'plain_texts': len(plain_texts)},
            'errors': errors, 'warns': warns}


def main():
    if len(sys.argv) < 2:
        print('用法: python check_report_depth.py <报告.docx> [--min N] [--type T] [--trace-dir D]')
        return 2
    path = sys.argv[1]
    minw = int(sys.argv[sys.argv.index('--min') + 1]) if '--min' in sys.argv else None
    rtype = sys.argv[sys.argv.index('--type') + 1] if '--type' in sys.argv else None
    trace_dir = sys.argv[sys.argv.index('--trace-dir') + 1] if '--trace-dir' in sys.argv else None
    r = check_docx(path, minw, rtype, trace_dir)
    print('== %s ==' % os.path.basename(path))
    print('   字数=%d 表=%d 图=%d 证据标签=%d 数字密度=%.0f%% 空章节=%s 通俗件=%s'
          % (r['total_chars'], r['tables'], r['images'], r['tag_count'],
             (r['digit_density'] or 0) * 100, r['empty'] or '无',
             r.get('plain_blocks', {})))
    print('   章节字数分布（薄弱章节→补新论点+新数据源，非扩写）:')
    for t, w in r['per_section']:
        flag = '  <-- 薄' if 0 < w < 600 else ''
        print('     %-40s %5d%s' % (t[:38], w, flag))
    for e in r['errors']:
        print('  FAIL:', e)
    for w in r['warns']:
        print('  WARN:', w)
    print('== 深度质检: %d 错误, %d 警告 ==' % (len(r['errors']), len(r['warns'])))
    return 1 if r['errors'] else 0


if __name__ == '__main__':
    sys.exit(main())
