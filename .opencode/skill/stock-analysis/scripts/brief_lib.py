# -*- coding: utf-8 -*-
"""需求书引擎（brief_lib）——单波问询的落盘载体。

/grill 与 /ask 都只问一波：
- 一次 question 调用批量 5~6 问（每问 2~4 选项），覆盖全部必填字段
- 模糊答案 / 缺字段由编排器按务实偏好兜底，并写入盲区（不再追问第二波）
- 结束后输出决策摘要：/grill 请用户批准（唯一人工门）；/ask 自动批准（带免责）

用法：
    from brief_lib import new_brief, record_wave, validate_brief, approve
    b = new_brief('中药行业', report_no=7)
    record_wave(b, questions=[{'id': 'q1', 'q': '报告类型？', 'options': [...]}, ...],
                answers=[{'question_id': 'q1', 'answer': '深度研究'}],
                decisions=[{'field': 'report_type', 'value': '深度研究'}])
    ok, missing = validate_brief(b)
    approve(b)
"""
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_lib import save_json, load_json  # noqa: E402

MAX_WAVES = 1
MIN_FIRST_WAVE = 5

REQUIRED_FIELDS = ('report_type', 'reader', 'purpose', 'key_concerns',
                   'failure_criteria', 'time_range', 'length_pref',
                   'language', 'flow_level')

FIELD_LABELS = {
    'report_type': '报告类型', 'reader': '读者', 'purpose': '用途',
    'key_concerns': '重点关切（≥3 条）', 'failure_criteria': '失败标准（这份报告怎样算没用）',
    'time_range': '时间范围', 'length_pref': '篇幅偏好', 'language': '语言',
    'flow_level': '流程级别（full/standard/minimal）',
    'rating_framework': '评级框架', 'forbidden': '禁写区', 'must_include': '必须包含',
    'report_name_hint': '报告名建议', 'update_of': '更新对象（编号或档案）',
}

VAGUE_WORDS = ('深度', '差不多', '尽量', '大概', '可能吧', '看着办', '随便',
               '好一点', '专业一点', '再看看', '都行', '你定', '标准')

SELF_DISCLAIMER = '需求由 self-grill 代理推导，未经用户确认'


def new_brief(subject, report_no=None, mode='user'):
    """mode='user'：真人对谈（/grill，批准=唯一人工门）；
    mode='self'：主上下文自推导（/ask，self_approve 自动批准+免责标注）。"""
    return {'subject': subject, 'report_no': report_no, 'mode': mode,
            'fields': {k: None for k in FIELD_LABELS},
            'waves': [], 'approval': None,
            'created': datetime.datetime.now().isoformat(timespec='seconds')}


def vague_hits(text):
    """检测答案中的模糊词（命中 → 编排列入盲区并按务实偏好兜底，不再追问）。"""
    t = str(text or '')
    return [w for w in VAGUE_WORDS if w in t]


def record_wave(brief, questions, answers, decisions=None, actor='user'):
    """记录唯一一波问答与由此固化的决策。

    questions: [{'id', 'q', 'options': [...]}]
    answers:   [{'question_id', 'answer'}]（answer 可为选项 label 或自定义文本）
    decisions: [{'field', 'value'}] 本波固化的需求决策（写入 brief.fields）
    actor:     'user'（/grill 真人）或 'self'（/ask 自推导）
    """
    if len(brief['waves']) >= MAX_WAVES:
        raise ValueError('单波协议：brief 已记录 1 波，不再接受第二波（模糊/缺字段请兜底并标盲区）')
    if len(questions or []) < MIN_FIRST_WAVE:
        raise ValueError('至少 %d 问（一次覆盖全部必填字段），当前 %d'
                         % (MIN_FIRST_WAVE, len(questions or [])))
    for d in decisions or []:
        if d['field'] not in FIELD_LABELS:
            raise ValueError('未知需求字段 %r（可用 %s）' % (d['field'], sorted(FIELD_LABELS)))
        brief['fields'][d['field']] = d['value']
    brief['waves'].append({'wave': 1, 'questions': questions or [],
                           'answers': answers or [],
                           'decisions': decisions or [],
                           'actor': actor})
    return brief['waves'][-1]


def termination_check(brief):
    """单波协议：问完即止。返回 (stop: bool, reason: str)。"""
    if brief.get('approval', {}) and brief['approval'].get('approved'):
        return True, 'brief 已批准'
    if not brief['waves']:
        return False, '尚未提问'
    return True, '单波问询已完成'


def validate_brief(brief):
    """完整性校验：必填字段全非空 + 重点关切 ≥3 条 + 失败标准非空。"""
    f = brief.get('fields') or {}
    missing = []
    for k in REQUIRED_FIELDS:
        v = f.get(k)
        if v is None or (isinstance(v, str) and not v.strip()) \
                or (isinstance(v, list) and not v):
            missing.append(FIELD_LABELS.get(k, k))
    kc = f.get('key_concerns') or []
    if isinstance(kc, list) and 0 < len(kc) < 3:
        missing.append('重点关切不足 3 条（当前 %d）' % len(kc))
    return (not missing), missing


def approve(brief, note=''):
    if brief.get('approval') and brief['approval'].get('approved'):
        return brief['approval']
    ok, missing = validate_brief(brief)
    if not ok:
        raise ValueError('brief 未通过完整性校验，缺: %s' % '; '.join(missing))
    brief['approval'] = {'approved': True,
                         'at': datetime.datetime.now().isoformat(timespec='seconds'),
                         'note': note}
    return brief['approval']


def self_approve(brief, note=''):
    """self-grill 自动批准（/ask 零人工路线）：完整性校验通过后自动放行，
    approval 带 auto=True 与免责标注——报告封面/首页必须同步声明。"""
    if brief.get('mode') != 'self':
        raise ValueError("self_approve 仅用于 mode='self' 的 brief（/ask 路线）")
    approval = approve(brief, note=note or SELF_DISCLAIMER)
    approval['auto'] = True
    approval['disclaimer'] = SELF_DISCLAIMER
    return approval


def summary(brief):
    """全部决策摘要（批准前展示 / self-grill 完成摘要引用）。"""
    lines = ['## 需求摘要 · %s' % brief.get('subject'), '']
    if brief.get('mode') == 'self':
        lines.append('> ⚠ %s' % SELF_DISCLAIMER)
        lines.append('')
    for k, label in FIELD_LABELS.items():
        v = (brief.get('fields') or {}).get(k)
        if v is None:
            continue
        if isinstance(v, list):
            v = '；'.join(str(x) for x in v)
        lines.append('- **%s**: %s' % (label, v))
    lines.append('- **问询**: %d 波，共 %d 问%s'
                 % (len(brief.get('waves') or []),
                    sum(len(w.get('questions') or []) for w in brief.get('waves') or []),
                    '（self-grill 自推导）' if brief.get('mode') == 'self' else ''))
    vh = []
    for w in brief.get('waves') or []:
        for a in w.get('answers', []):
            for hit in vague_hits(a.get('answer')):
                vh.append('"%s"（%s）' % (hit, a.get('question_id')))
    if vh:
        lines.append('- **模糊答案（已按务实偏好兜底，写入盲区）**: %s' % '；'.join(vh[:6]))
    return '\n'.join(lines)


def save_brief(brief, path):
    return save_json(brief, path, ttl_hours=None,
                     scope=str(brief.get('subject') or '') + '-brief', source='brief_lib')


def load_brief(path):
    return load_json(path)


if __name__ == '__main__':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    b = new_brief('自测')
    qs = [{'id': 'q%d' % i, 'q': '问题%d' % i, 'options': ['A', 'B']} for i in range(5)]
    record_wave(b, qs, [{'question_id': 'q1', 'answer': '深度研究'}],
                decisions=[{'field': 'report_type', 'value': '深度研究'}])
    print(termination_check(b))
