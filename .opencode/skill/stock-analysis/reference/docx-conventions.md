# Word 报告规范

`scripts/docx_helpers.py` 全局强制, 禁内联样式; 经济学人黑白红风。

## 样式令牌
| 元素 | 规范 |
|---|---|
| 配色 | INK `1A1A1A`(标题/表头/色带), SCARLET `E3120B`(装饰条/所以呢), HAIRLINE `BFBFBF`, CREAM `F7F7F7`, ZEBRA `F2F2F2`, DARK `262626`, RED `C0504D` |
| 注块底 | WARN_FILL `FBE9E9`, NOTE_FILL `F5F5F5`, SOWHAT_FILL `FCEBE9` |
| 别名 | NAVY/STEEL/MAROON/GOLD/BLUE/BLUE2=INK/SCARLET; SAND_HEX=SCARLET_HEX |
| 正文 | 宋体 10.5~11pt+Times New Roman; 行距 1.35; 首行缩进 0.74cm; 段后 8pt |
| 标题 | H1 黑体 15pt 粗 INK+左 3pt SCARLET 条(`w:pBdr` sz=22)+底 HAIRLINE 0.8pt(sz=6); H2 12.5pt+红条 sz=10; H3 11pt 灰+灰条 sz=6 `8C8C8C` |
| 表格 | `Table Grid` 居中; 表头 INK 底白字 9~9.5pt 粗, 行高≥0.55cm; 奇行 ZEBRA; 首列粗深灰; 内边距 0.08/0.12cm; 列宽 Cm |
| 图 | 居中宽 16cm(13.5~16); 图注灰 9pt; 主色 INK/灰, 强调/负值 SCARLET |
| 封面 | INK 色带(12pt 白字)→28pt INK 标题→SCARLET 线→14pt 灰副题→CREAM 元信息→砖红免责 |
| 页眉脚 | `setup_page(doc,标题,日期)`: 页眉 INK 8pt 灰标题(右日期)+SCARLET 线; 页脚居中 `— N —`(PAGE 域 9pt 灰); 首页跳过; 边距上下 2.4/2.2cm, 左右 2.4cm; 章间 `add_page_break()` |

## 通俗层(layout_rules)
- 文风: 结论先行/短句/主动语态/一段一个意思; 正文不堆 `[实证]/[推断]/[观点]`(只进假设表与溯源表); 禁 AI 腔(综上所述/值得注意的是/赋能/助力)
- priority 能图不表, 能表不文字墙; 定性逻辑用 `diagram`(note"仅为逻辑示意"); 图库 `chart_helpers`: line_chart/bar_chart/hbar/heatmap/boxplot/twin_bar_line/waterfall/diagram
- 承重段(≥3 行)后挂 `plain_note`(`analogy=True` 附"※仅为助记"); 每章 ≥1 `so_what`; 全报告 ≥1 `faq_box`(PUA 自审或写作时预判)
- 估值/技法首现挂 `method_card(name,what,why,how_to_read)`; 表前 `table_intro`; 正文表 >10 行转图(`bar_chart`/`hbar`/`heatmap`)移附录, 正文 ≤8 行
- `img`/`add_table` caption 自动"图N/表N"; 每图前 `fig_intro`"看图先读: 这张图看什么/说明什么结论", 图注来源由 `img(source=...)` 自动追加; `fig_table_list` 附录清单; 封面后 `speedread_page` 30 秒速读(结论+理由+数字表+主图+多空); 通俗层数字须与专业层一致(QA 硬检), 判断权归专业层; 速读页+方法卡≥2/白话&所以呢≥5/FAQ≥1

## 报告结构(蓝图驱动, 禁手写章节)
`blueprints.json` 按画像推导; `optional_sections.dispute` trigger=true 必含: 分歧摘要表→正反论据→敏感性拆解→裁决, 未触发标"多方法一致性 N/M"。

## QA
1. `check_delivery` 0 错误; `cache_status --strict`; stale 标截止日期; 章与蓝图一致(缺章 FAIL); 图编号连续; 禁区方法(地产 PE 分位, 加密 DCF)FAIL; 估算标(估)
2. `check_report_depth --type 蓝图id --trace-dir 工作区` 0 错误: 空章/字数下限(full 8000, standard 6000, minimal 4000, update 3000 字符)/强制章/数字溯源/图注来源/证据标签; 强制章节 `research_process`/`assumption_validity`/`divergent_views` 齐全; 关键数字可复算; 通俗层数字在正文

## 交付
`save_stage(doc,文件名,subject,review,report_no)` 双写归档; 命名 `{主题}投资研究报告_YYYYMMDD.docx`(特殊类型可后缀, 禁 `_` 双分隔); 暂存区 `暂存区/`, 确认后移动至 `分类区/{主题}/`, PNG/JSON 随档。

## 附录表
`provenance_table` 溯源, `socratic_stats_table` 审计统计, `manager_stats_table` 审问统计, `data_asof_table` 数据截止(`fetch_lib.cache_meta_table`), `fig_table_list` 图表清单, `img(doc,path,caption,source=…)` 图注编号+来源; 常用 `new_document`, `cover`, `para`, `dump_doc_text`, `diagram`。
