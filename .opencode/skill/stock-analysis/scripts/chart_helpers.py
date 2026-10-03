# -*- coding: utf-8 -*-
"""统一图表工具（matplotlib Agg + 微软雅黑）。

用法：
    from chart_helpers import setup_cn, line_chart, bar_chart, heatmap, boxplot, hbar
    setup_cn()
    line_chart(df, x='date', y='close', title='…', path='fig1_price.png')
    bar_chart(categories, values, path='fig2_amp.png', figsize=(9, 5))
    heatmap(df_pivot, title='…', cmap='RdYlGn', path='fig3_heat.png')
    boxplot(list_of_arrays, labels=[...], path='fig4_box.png')
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

CN_FONTS = ['Microsoft YaHei', 'SimHei', 'PingFang SC']


def setup_cn():
    """中文字体 + 负号 + 全局样式。脚本开头调用一次。"""
    from matplotlib import font_manager
    for f in CN_FONTS:
        try:
            font_manager.findfont(f, fallback_to_default=False)
            plt.rcParams['font.sans-serif'] = [f] + list(plt.rcParams['font.sans-serif'])
            break
        except Exception:
            continue
    plt.rcParams['axes.unicode_minus'] = False
    plt.rcParams['figure.dpi'] = 110
    plt.rcParams['axes.grid'] = True
    plt.rcParams['grid.alpha'] = 0.3


def _save(fig, path, tight=True):
    if tight:
        fig.tight_layout()
    fig.savefig(path, bbox_inches='tight')
    plt.close(fig)
    print('saved:', path)


def line_chart(x, y, title='', xlabel='', ylabel='', path='fig_line.png',
               figsize=(11, 5), color='#1F3B73', linewidth=1.5, second=None):
    """单/双轴折线图。second=(y2, label) 时画右轴。"""
    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(x, y, color=color, linewidth=linewidth)
    ax.set_title(title, fontsize=13, fontweight='bold')
    ax.set_xlabel(xlabel); ax.set_ylabel(ylabel)
    if second:
        ax2 = ax.twinx()
        ax2.plot(x, second[0], color='#C0504D', linewidth=1.2, linestyle='--')
        ax2.set_ylabel(second[1])
    _save(fig, path)


def bar_chart(categories, values, title='', path='fig_bar.png',
              figsize=(11, 5), color='#2E5FA3', labels=None,
              value_fmt='{}', rot=30, ylabel=''):
    """柱状图（可叠数值标签）。"""
    fig, ax = plt.subplots(figsize=figsize)
    bars = ax.bar(categories, values, color=color)
    if labels:
        for b, v in zip(bars, labels):
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() * 1.01,
                    value_fmt.format(v), ha='center', fontsize=9)
    ax.set_title(title, fontsize=13, fontweight='bold')
    ax.set_ylabel(ylabel)
    plt.setp(ax.get_xticklabels(), rotation=rot, ha='right')
    _save(fig, path)


def hbar(categories, values, title='', path='fig_hbar.png', figsize=(9, 6),
         color='#2E5FA3', labels=None, value_fmt='{}'):
    """横向柱状图（适合长标签，第一个类别显示在最上方）。"""
    fig, ax = plt.subplots(figsize=figsize)
    y = np.arange(len(categories))
    ax.barh(y[::-1], values, color=color)
    ax.set_yticks(y); ax.set_yticklabels(categories)
    if labels:
        for yi, v in zip(y[::-1], labels):
            ax.text(v * 1.01, yi, value_fmt.format(v), va='center', fontsize=9)
    ax.set_title(title, fontsize=13, fontweight='bold')
    ax.margins(x=0.15)
    _save(fig, path)


def heatmap(df, title='', path='fig_heat.png', cmap='RdYlGn', fmt='.0f',
            annot=True, figsize=(10, 6)):
    """参数扫描热力图（网格回测等）。df: 行/列为参数，值为结果。"""
    fig, ax = plt.subplots(figsize=figsize)
    im = ax.imshow(df.values, cmap=cmap)
    ax.set_xticks(range(len(df.columns))); ax.set_xticklabels(df.columns)
    ax.set_yticks(range(len(df.index))); ax.set_yticklabels(df.index)
    if annot:
        for i in range(len(df.index)):
            for j in range(len(df.columns)):
                ax.text(j, i, fmt.format(df.values[i, j]), ha='center', va='center',
                        fontsize=8)
    ax.set_title(title, fontsize=13, fontweight='bold')
    ax.set_xlabel(df.columns.name or ''); ax.set_ylabel(df.index.name or '')
    fig.colorbar(im, ax=ax, shrink=0.85)
    _save(fig, path)


def boxplot(groups, labels=None, title='', path='fig_box.png',
            ylabel='', figsize=(9, 5)):
    """分组箱线图（蒙特卡洛超额收益分布等）。groups: 数组列表。"""
    fig, ax = plt.subplots(figsize=figsize)
    ax.boxplot(groups, labels=labels, patch_artist=True,
               medianprops={'color': '#1F3B73', 'linewidth': 1.5})
    ax.axhline(0, color='#C0504D', linestyle='--', linewidth=1)
    ax.set_title(title, fontsize=13, fontweight='bold')
    ax.set_ylabel(ylabel)
    _save(fig, path)


def twin_bar_line(x, bars, bar_label, line, line_label, title='',
                  path='fig_twin.png', bar_color='#2E5FA3',
                  line_color='#C0504D', figsize=(11, 5)):
    """柱状+折线双轴图（商誉/占比、收入/增速等）。"""
    fig, ax = plt.subplots(figsize=figsize)
    ax.bar(x, bars, color=bar_color, alpha=0.85, label=bar_label)
    ax2 = ax.twinx()
    ax2.plot(x, line, color=line_color, marker='o', linewidth=1.5, label=line_label)
    ax.set_title(title, fontsize=13, fontweight='bold')
    lines1, lab1 = ax.get_legend_handles_labels()
    lines2, lab2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, lab1 + lab2, loc='best', fontsize=9)
    plt.setp(ax.get_xticklabels(), rotation=30, ha='right')
    _save(fig, path)


def waterfall(x, changes, totals=None, title='', path='fig_water.png',
              figsize=(11, 5)):
    """瀑布图（商誉增减桥等）。changes: 每步变动，totals: 每步累计（缺省自动）。"""
    if totals is None:
        totals = np.cumsum([0] + list(changes))
    fig, ax = plt.subplots(figsize=figsize)
    n = len(changes)
    for i in range(n):
        bottom = min(totals[i], totals[i + 1])
        height = abs(changes[i])
        color = '#C0504D' if changes[i] < 0 else '#2E5FA3'
        ax.bar(i, height, bottom=bottom, color=color)
    ax.set_xticks(range(n)); ax.set_xticklabels(x, rotation=30, ha='right')
    ax.set_title(title, fontsize=13, fontweight='bold')
    _save(fig, path)
