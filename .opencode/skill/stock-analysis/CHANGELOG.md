# CHANGELOG

## v3.2（2026-10-04）通俗外挂层 + 深蓝投行排版改版（grill 6 波批准）

- **设计哲学（铁律八）**：报告面向非专业金融从业者——**通俗只是专业深度的外挂解释层，判断权归专业层**；通俗层数字与专业层不一致 = QA FAIL；禁以"太通俗"降专业深度，也禁以"太专业"删通俗件；技法注册表 techniques.json 全保留，只是呈现更好读
- **docx_helpers 深蓝投行风**：酒红金米白 → 海军蓝 NAVY 14315C/钢蓝 STEEL 5B87C6/浅蓝灰/沙金点缀（高盛/大摩参照）；旧颜色名保留兼容别名；保守平板参数（图宽默认 16cm、段后 8pt、行距 1.35，字号不动）
- **通俗外挂层 API**：`plain_note`（逐段白话注块，analogy=True 自动带"※比喻仅为助记"免责）、`so_what`（所以呢框）、`faq_box`（小白问答，白底虚线）、`method_card`（三段式方法卡：是什么/为什么用它/结果怎么读）、`table_intro`（表前导语）、`speedread_page`（封面后 30秒速读一页纸：结论+理由速览+关键数字+主图+风险多空）
- **图表编号系统**：img/add_table caption 自动连续编号"图N/表N"（已带编号不重复），`fig_table_list` 附录图表清单；`dump_doc_text` 新增【外挂】【表注】标记
- **chart_helpers.diagram**：简洁逻辑示意图（几何+箭头+中文，深蓝系，note 标"仅为逻辑示意"）——业务链/竞争格局/方法论图解新能力
- **PUA 通俗两问**：desk_chief.md 新增 kind='plain' 通俗问 ≤2（比喻失真检验+扮小白 FAQ）；manager_log 上限 3→"专业≤3+通俗≤2 合计≤5"
- **blueprints v3**：顶层 `layout_rules`（能图不表优先级/逐段外挂/方法卡挂点/表前三规/>10行转图/图表编号/速读页），8 蓝图全插 speedread 章节；排版件全级别（full/standard/minimal）统一套用，minimal 无 PUA 由 QA 硬检兜底
- **check_report_depth v3.2**（只增不减）：[错误] 通俗层数字与专业层不一致；[警告] 缺速读页/通俗覆盖不足（方法卡≥2、白话注≥5、FAQ≥1）；输出 plain_blocks 统计
- **subagent-protocol.md**：写手排版件契约 8 条（输入包+layout_rules）
- **文档**：docx-conventions.md 深蓝令牌+新元素+QA 16/17 项；SKILL.md v3.2（分级表/铁律八/速读页/排版件示例）
- selftest 更新颜色断言 + 新增 4 用例（通俗件渲染/图表编号/diagram/通俗层 QA）

## v3.1（2026-10-03）self-grill（/ask）零人工路线

- **/ask 命令**：用户一句话提问 → 拷问者×应答者双子代理（互不可见，文件总线对谈）按 grill 同款波次协议自我拷问（≤6 波），推导 brief 后 `brief_lib.self_approve()` 自动批准（approval 带 auto+免责），直接走 full 级流水线至 docx 交付——全程零用户参与
- **新模板**：self_grill_interviewer.md（对代理答案的钻取规则：弱推断/中性必追问默认假设）/ self_grill_responder.md（推断强度分级 [代理推断·强/中/弱]、禁编造私有信息、务实偏好兜底）
- **brief_lib**：new_brief(mode='user'|'self')；record_wave 带 actor；self_approve 自动批准+免责字段；summary 对 self 模式附免责头
- **纪律**：self-grill 报告封面+首页脚注双重免责标注；完成摘要高亮 Top3 代理推断；事后 /drill（模式A）→ /report resume 修正重跑；波次耗尽按务实偏好兜底填充，禁止 blocked 悬停
- 子代理防火墙矩阵 +2 角色；SKILL.md 命令表与 self-grill 节；selftest +1 用例

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
