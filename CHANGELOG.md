# CHANGELOG

## v2.5（2026-08-30）可改进点修正批

- **P1 执行可见性**：`flow_log.py`（流水线每步耗时/事件审计，报告 meta 记生成成本）；crux/note 质量启发式（防敷衍）；settled 清单标准载体写进两会话模板；两模板补 few-shot 范例；`thesis_lib.tree_diff`（建树 vs 审核员重建树结构化对照）
- **P2 流程经济学**：蓝图新增 `flow` 分级（full/standard/minimal——深度/资产/租金走全流程，量化走校对会话，手册/科普/决策仅 QA）；新增 `update_report` 更新报告类型（复用档案可继承资产，只重估变化，8000 字下限）；min_words 按蓝图差异化（20000/15000/10000/8000）
- **P3 工具链**：`fetch_lib.pdf_text`（公告 PDF→文本，关键词过滤页）；`fetch_lib.cache_meta_table` + `docx_helpers.data_asof_table`（附录数据截止时间表）；`img(source=...)` 图注自动追加资料来源（QA 检查）
- **P4 学习闭环**：`review_lib.error_patterns`（跨档案按评级聚合失误，失误样本清单）
- **P5 文档**：docx-conventions.md 增附录自动表格节与差异化字数；library README 手办示例对齐 asset_research v2

## v2.4（2026-08-30）原子化根治 + H1-H8

- thesis_lib 论点树贯穿全流程（结论→承重柱→证据映射）；审核员改两阶段通读（重建树→全局问题→pillar 级攻击，撤机械初审）；dump_doc_text 结构标记；联合脆弱质询类型
- H1 质询修正回流（assumption_ref+revised_assumption_claims）；H2 溯源静默失效改 FAIL；H3 溯源抽查覆盖正文证据句；H4 weighted_synthesis 合成算子；H5 dossier 代码主键+别名迁移；H6 两会话落盘；H7 revision_checklist；H8 suggest_judgment 量化判定

## v2.3（2026-08-30）解读对抗

- 校对环节从数字核对升级为解读对抗：替代解读/隐含前提（必填 crux，仅区分性新证据可裁决）；双方武装抓数（每轮 ≤3）；defend 必填理由；背反自动记录；"同一数字的两种读法"进反方章节

## v2.2（2026-08-30）校对环节

- 新增第 10 步报告校对质询（挑刺审核员→双方苏格拉底→草稿循环后终稿）；dump_doc_text；附录质询统计表

## v2.1（2026-08-30）六蓝图重构 + 预测估值双引擎 + 记忆层 + QA v2

- blueprints v2：equity_deep_8ch（盈利预测独立成章/护城河/杜邦/风险独立成章）、asset_research 供需平衡表、rental NOI 预测、theme_quant 逻辑/基准/失效边界、手册风控红线、决策不可逆性；章节 spec 改证据对象枚举
- forecast_lib（盈利/NOI/供需三模型，Assumption 证据链强制）；valuation_lib（19 算子，derive 分派，crosscheck，flip_point，provenance）
- socratic_lib 质询引擎（准入三规则/四层基岩/背反检测/停滞判定）+ 两模板；review_lib 复盘闭环（档案/save_stage 自动落档/校准率）
- check_report_depth v2（证据对象计数/溯源抽查/蓝图必备章）；fetch_lib 三新源（巨潮/现货/宏观）；render_check；目录卫生（data 历史迁移归档）
- 硬编码参数清除（算子缺参即报错，methods.json 参数改信号锚指引）

## v2.0（2026-08 之前）

- 8 维画像推导、JSON 规则库、dispute 分歧检测、usage_probe 业界取证、缓存治理、docx 统一样式库（沿用的原始基线）
