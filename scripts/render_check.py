# -*- coding: utf-8 -*-
"""渲染自查：docx → PDF → 图片，供 Read 工具目检排版（仿官方 docx skill 渲染闭环）。

用法：
    python scripts/render_check.py <报告.docx> [--pages 1,2,3] [--out 渲染目录]

流程：soffice --headless 转 PDF → PyMuPDF 逐页转 PNG → 输出图片路径清单。
环境无 soffice/LibreOffice 时打印 SKIP 提示并以退出码 0 结束（可选步骤）。
生成的 PNG 用 Read 工具查看：重点检查封面元素、表格宽度溢出、图片缩放、callout 底色。
"""
import os
import shutil
import subprocess
import sys


def find_soffice():
    for cand in ('soffice', 'soffice.exe',
                 r'C:\Program Files\LibreOffice\program\soffice.exe',
                 r'C:\Program Files (x86)\LibreOffice\program\soffice.exe'):
        p = shutil.which(cand) if not os.path.isabs(cand) else (cand if os.path.exists(cand) else None)
        if p:
            return p
    return None


def render(docx_path, pages=None, out_dir=None):
    soffice = find_soffice()
    if not soffice:
        print('SKIP: 未找到 soffice/LibreOffice，渲染自查不可用（可选步骤，直接通过）')
        print('      安装 LibreOffice 后本步骤自动启用')
        return []
    base = os.path.abspath(docx_path)
    out_dir = out_dir or os.path.join(os.path.dirname(base), 'render_check')
    os.makedirs(out_dir, exist_ok=True)
    subprocess.run([soffice, '--headless', '--convert-to', 'pdf',
                    '--outdir', out_dir, base],
                   capture_output=True, timeout=180)
    pdf = os.path.join(out_dir, os.path.splitext(os.path.basename(base))[0] + '.pdf')
    if not os.path.exists(pdf):
        print('FAIL: PDF 转换失败（soffice 输出目录无产物）')
        return None
    import fitz  # PyMuPDF
    doc = fitz.open(pdf)
    idxs = pages if pages else list(range(min(4, doc.page_count)))
    pngs = []
    for i in idxs:
        if not (0 <= int(i) < doc.page_count):
            continue
        pix = doc.load_page(int(i)).get_pixmap(dpi=110)
        png = os.path.join(out_dir, 'page_%02d.png' % (int(i) + 1))
        pix.save(png)
        pngs.append(png)
    print('PDF:', pdf, '| pages:', doc.page_count)
    print('PNG（用 Read 工具目检）:')
    for p in pngs:
        print('  ', p)
    return pngs


def main():
    if len(sys.argv) < 2:
        print('用法: python render_check.py <报告.docx> [--pages 1,2,3] [--out 目录]')
        return 2
    pages = None
    if '--pages' in sys.argv:
        pages = [int(x) for x in sys.argv[sys.argv.index('--pages') + 1].split(',') if x.strip()]
    out_dir = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else None
    pngs = render(sys.argv[1], pages, out_dir)
    if pngs is None:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
