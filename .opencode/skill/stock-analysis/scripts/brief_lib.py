# -*- coding: utf-8 -*-
"""需求书引擎（brief_lib）——多波次刨根 grill 的落盘载体。

grill 以文件为状态：工作区 brief.json 即 grill 痕迹。
- 无 brief 文件 → 询问模式（/grill）：多波次批量提问，生成新 brief
- 有 brief 文件 → 追问模式（/drill）：另一套 prompt，重审需求或回溯拷问报告

波次协议（批量波次）：
- 每波一次 question 调用批量 5~8 问（每问 2~4 选项），首波 ≥5 问
- 钻取规则：答案含模糊词 / 引入新决策变量 / 自定义输入 → 下一波必须派生 ≥2 追问
- 终止三条件（任一即停）：连续两波无新决策变量 / 用户答"够了" / brief 完整性校验通过
- 安全上限 6 波；结束后输出全部决策摘要请用户批准（唯一人工门）

用法：
    from brief_lib import new_brief, record_wave, termination_check, validate_brief, approve
    b = new_brief('中药行业', report_no=7)
    record_wave(b, questions=[{'id': 'q1', 'q': '报告类型？', 'options': [...]}, ...],
                answers=[{'question_id': 'q1', 'answer': '深度研究'}],
                decisions=[{'field': 'report_type', 'value': '深度研究'}])
    stop, why = termination_check(b)
    ok, missing = validate_brief(b)
    approve(b)
"""
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_lib import save_json, load_json  # noqa: E402

MAX_WAVES = 6
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
ENOUGH_MARKS = ('够了', '不用问了', '就这些', '停止提问')


def new_brief(subject, report_no=None):
    return {'subject': subject, 'report_no': report_no,
            'fields': {k: None for k in FIELD_LABELS},
            'waves': [], 'followups': [], 'approval': None,
            'created': datetime.datetime.now().isoformat(timespec='seconds')}


def vague_hits(text):
    """检测答案中的模糊词（命中 → 下一波强制派生追问）。"""
    t = str(text or '')
    return [w for w in VAGUE_WORDS if w in t]


def said_enough(answers):
    for a in answers or []:
        if any(m in str(a.get('answer', '')) for m in ENOUGH_MARKS):
            return True
    return False


def record_wave(brief, questions, answers, decisions=None, followups=None):
    """记录一波问答与由此固化的决策。

    questions: [{'id', 'q', 'options': [...]}]
    answers:   [{'question_id', 'answer'}]（answer 可为选项 label 或自定义文本）
    decisions: [{'field', 'value'}] 本波固化的需求决策（写入 brief.fields）
    followups: 本波识别出的待深挖点（模糊词/新变量/自定义输入），下一波必须覆盖
    """
    if len(brief['waves']) == 0 and len(questions or []) < MIN_FIRST_WAVE:
        raise ValueError('首波至少 %d 问（批量波次协议），当前 %d'
                         % (MIN_FIRST_WAVE, len(questions or [])))
    wave_no = len(brief['waves']) + 1
    if wave_no > MAX_WAVES:
        raise ValueError('波次超过安全上限 %d——必须出决策摘要请求批准' % MAX_WAVES)
    for d in decisions or []:
        if d['field'] not in FIELD_LABELS:
            raise ValueError('未知需求字段 %r（可用 %s）' % (d['field'], sorted(FIELD_LABELS)))
        brief['fields'][d['field']] = d['value']
    brief['waves'].append({'wave': wave_no, 'questions': questions or [],
                           'answers': answers or [],
                           'decisions': decisions or [],
                           'followups': followups or []})
    brief.pop('_derived_followups', None)
    return brief['waves'][-1]


def open_followups(brief):
    """待深挖点 = 最后一波未消化的 followups + 全部答案中的模糊词命中。"""
    out = list(brief.get('followups') or [])
    for w in brief['waves']:
        for a in w.get('answers', []):
            for hit in vague_hits(a.get('answer')):
                out.append('波%d·%s 答案含模糊词"%s"' % (w['wave'], a.get('question_id'), hit))
    if brief['waves']:
        out.extend(brief['waves'][-1].get('followups') or [])
    seen, uniq = set(), []
    for x in out:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq


def _new_decision_count(wave):
    return len(wave.get('decisions') or [])


def termination_check(brief):
    """终止三条件（任一即停）。返回 (stop: bool, reason: str)。"""
    if brief.get('approval', {}) and brief['approval'].get('approved'):
        return True, 'brief 已批准'
    waves = brief['waves']
    if not waves:
        return False, '尚未开始'
    if said_enough(waves[-1].get('answers')):
        return True, '用户表示"够了"'
    if len(waves) >= 2 and _new_decision_count(waves[-1]) == 0 \
            and _new_decision_count(waves[-2]) == 0:
        return True, '连续两波无新决策变量'
    ok, _missing = validate_brief(brief)
    if ok and not open_followups(brief):
        return True, 'brief 完整性校验通过且无待深挖点'
    if len(waves) >= MAX_WAVES:
        return True, '波次达安全上限 %d' % MAX_WAVES
    return False, '继续第 %d 波（待深挖点 %d 个）' % (len(waves) + 1, len(open_followups(brief)))


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


def summary(brief):
    """全部决策摘要（批准前展示）。"""
    lines = ['## 需求摘要 · %s' % brief.get('subject'), '']
    for k, label in FIELD_LABELS.items():
        v = (brief.get('fields') or {}).get(k)
        if v is None:
            continue
        if isinstance(v, list):
            v = '；'.join(str(x) for x in v)
        lines.append('- **%s**: %s' % (label, v))
    lines.append('- **波次**: %d 波，共 %d 问'
                 % (len(brief.get('waves') or []),
                    sum(len(w.get('questions') or []) for w in brief.get('waves') or [])))
    fp = open_followups(brief)
    if fp:
        lines.append('- **仍未查明（将写入盲区）**: %s' % '；'.join(fp[:5]))
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
