# -*- coding: utf-8 -*-
"""流水线执行审计（flow_log）——协议遵守情况与成本的可见性。

记录：每步耗时、质询轮数、回流次数、驳回数、子代理调用数、新抓取数。
落盘 data/pipeline_log_{scope}.json（_meta 缓存约定）；报告 meta 引用 summary。

用法：
    from flow_log import FlowLog
    log = FlowLog('600754-深度研究')          # 第 1 步建
    with log.step('数据抓取'):
        ...                                   # 耗时自动记录
    log.event('质询', rounds=3, settled=4, rejected=2, backflow=1)
    log.save()                                # 第 11 步存；summary() 进报告附录/meta
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_lib import save_json  # noqa: E402


class _Step(object):
    def __init__(self, log, name):
        self.log, self.name = log, name

    def __enter__(self):
        self.t0 = time.time()
        return self

    def __exit__(self, exc_type, exc, tb):
        dt = round(time.time() - self.t0, 2)
        entry = {'step': self.name, 'seconds': dt}
        if exc_type is not None:
            entry['error'] = repr(exc)[:200]
        self.log.steps.append(entry)
        if exc_type is None:
            print('  [flow] %s %.1fs' % (self.name, dt))
        return False


class FlowLog(object):
    def __init__(self, scope):
        self.scope = scope
        self.steps = []
        self.events = []
        self.t_start = time.time()

    def step(self, name):
        return _Step(self, name)

    def event(self, name, **kw):
        self.events.append(dict(kw, event=name))

    def summary(self):
        return {'scope': self.scope,
                'total_seconds': round(time.time() - self.t_start, 1),
                'n_steps': len(self.steps),
                'n_events': len(self.events),
                'steps': self.steps, 'events': self.events}

    def save(self, path=None):
        path = path or os.path.join('data', 'pipeline_log_%s.json' % self.scope)
        return save_json(self.summary(), path, ttl_hours=None,
                         scope=self.scope, source='flow_log')
