# CHANGELOG

## v3.0（2026-10-03）全自治流水线重构

- **grill 双模式**：`brief_lib`（多波次批量刨根：首波 ≥5 问、模糊词强制派生追问、终止三条件、批准=唯一人工门）；询问（grill_interviewer.md → /grill）与追问（drill_interrogator.md → /drill）prompt 分离，以 brief.json 文件为状态
- **编号存档制**（废暂存区）：`workspace_lib`（reports/{编号}_{主题}/ 工作区 + WORKSPACE.md 索引导航 + 所有报告/ word 汇集 + _registry.json 账本 + 旧报告懒分配）；`save_stage(report_no=)` 双写交付；`check_delivery` v3 校验双写与注册表一致性
- **技法注册表**：`techniques.json`（core 20 项，来源三级标注 机构>教材·论文>GitHub）+ `technique_lib`（recommend/activate 每挂点 ≤3 必填理由/propose_auto 自动扩充 auto 区上限 20）；`analysis-techniques.md` 协议正文；forecast_lib `base_rate_ref` 基础比率强制（缺→[推断]降级[观点]）
- **PUA 管理员**（自动、非命令）：desk_chief.md（P7/P9 分级，≤3 问）+ `manager_log`（逐章 checkpoint、同章驳回 ≤1 次、二次转审计）；附录 manager_stats_table
- **单次审计**（两会话合一）：socratic_lib `mode='single_audit'`（硬上限 2 轮 R1攻防+R2核验，H1 回流保留）；四道防掉队闸：audit_readiness（火力下限）/audit_coverage（覆盖度量+exempt_pillar）/audit_gate（高严重度无归宿禁终稿）/audit_checklist；single_auditor.md 合并旧两模板（已删）
- **子代理防火墙**：subagent-protocol.md（输入包 3~8 文件路径、FACTS 冻结、侦察兵不知论点、写手禁抓数、技法分析师并行互不可见、审计员唯一全稿对抗视角）；主上下文纯编排
- **ACH**：profile_lib.ach_matrix（按最少不一致排序，诊断性证据标注）
- **命令**：/grill /report（resume/blocked）/drill（.opencode/command/）
- 依附更新：thesis_lib 单会话化、review_lib report_no+根定位回退、flow_log 事件（technique_activated/pua_checkpoint 由调用方记录）、SKILL.md v3 全重写、blueprints v3 spec、selftest v3 组 8 用例

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
