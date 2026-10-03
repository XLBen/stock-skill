# -*- coding: utf-8 -*-
"""PUA 管理员审问记录（manager_log）——金融大厂管理员逐章"你都写了啥"。

工作流内自动执行（不设主动命令）：每章交付后 Task 子代理按 desk_chief.md 模板
审问写作代理，checkpoint() 落盘。裁决：过关 / 补证据 / 驳回重写。

规则：
- 每章每轮审问 ≤3 问（数字哪来的 / So what / 删掉这章结论还立得住吗）
- 驳回重写自动执行，同章最多 1 次；二次驳回挂 escalated 转单次审计未决（不悬停等人）
- stats() 输出进附录"管理员审问统计表"（docx_helpers.manager_stats_table）与完成摘要

用法：
    from manager_log import ManagerLog
    ml = ManagerLog(scope='7_中药行业')
    ml.checkpoint('ch3', summary='分业务量价拆分…', questions=[{'q': '营收拆分数字哪来的', 'a': 'fin_600085.json'}], verdict='过关')
    ml.checkpoint('ch3', summary='重写后…', questions=[...], verdict='驳回重写')
    print(ml.stats())
    ml.save(workspace_lib.sessions_dir(7) + '/manager_log.json')
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_lib import save_json, load_json  # noqa: E402

VERDICTS = ('过关', '补证据', '驳回重写')
MAX_QUESTIONS = 3
MAX_REWRITES = 1


class ManagerLog(object):
    def __init__(self, scope, persona='P7'):
        self.scope = scope
        self.persona = persona
        self.checkpoints = []

    def checkpoint(self, section, summary, questions, verdict, note=''):
        """记录一次审问。同章二次驳回自动转审计（escalated），流水线不悬停。"""
        if verdict not in VERDICTS:
            raise ValueError('verdict 必须是 %s' % (VERDICTS,))
        if len(questions or []) > MAX_QUESTIONS:
            raise ValueError('每章每轮审问 ≤%d 问（管理员不做深度对抗，那是审计的事）'
                             % MAX_QUESTIONS)
        if not (summary or '').strip():
            raise ValueError('summary 必填：写作代理须先复述本章核心论点+关键数字')
        rewrites = sum(1 for c in self.checkpoints
                       if c['section'] == section and c['verdict'].startswith('驳回'))
        escalated = False
        final_verdict = verdict
        if verdict == '驳回重写' and rewrites >= MAX_REWRITES:
            escalated = True
            final_verdict = '驳回重写(转审计)'
        cp = {'id': 'cp%02d' % (len(self.checkpoints) + 1),
              'section': section, 'summary': summary,
              'questions': questions or [], 'verdict': final_verdict,
              'note': note, 'persona': self.persona,
              'rewrite_of': self._last_cp_id(section) if rewrites else None,
              'escalated': escalated,
              'ts': datetime.datetime.now().isoformat(timespec='seconds')}
        self.checkpoints.append(cp)
        return cp

    def _last_cp_id(self, section):
        ids = [c['id'] for c in self.checkpoints if c['section'] == section]
        return ids[-1] if ids else None

    def escalated_sections(self):
        """转单次审计未决的章节清单（R1 必须覆盖）。"""
        return [c['section'] for c in self.checkpoints if c['escalated']]

    def stats(self):
        by_verdict = {}
        for c in self.checkpoints:
            by_verdict[c['verdict']] = by_verdict.get(c['verdict'], 0) + 1
        sections = {c['section'] for c in self.checkpoints}
        n_q = sum(len(c['questions']) for c in self.checkpoints)
        return {'scope': self.scope, 'persona': self.persona,
                'sections': len(sections), 'checkpoints': len(self.checkpoints),
                'questions': n_q, 'by_verdict': by_verdict,
                'escalated': len(self.escalated_sections())}

    def save(self, path):
        return save_json({'scope': self.scope, 'persona': self.persona,
                          'checkpoints': self.checkpoints},
                         path, ttl_hours=None, scope=self.scope,
                         source='manager_log')

    @classmethod
    def load(cls, path):
        d = load_json(path)
        ml = cls(d.get('scope', ''), persona=d.get('persona', 'P7'))
        ml.checkpoints = d.get('checkpoints', [])
        return ml
