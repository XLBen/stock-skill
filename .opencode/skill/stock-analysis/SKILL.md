---
name: stock-analysis
description: 泛金融报告分析全流程 skill（v3.1 全自治流水线 + self-grill）。凡用户要求写/出/修改任何报告（投资研究/个股深度/资产研究/估值分析/财报解读/回测/总结报告，股票/基金/利率/地产/加密/收藏品等任意对象）即使用本 skill；亦覆盖行情/财务/研报数据抓取、网格/定投回测、板块筛选、商誉减值、指增/红利/AH 溢价研究与 Word（.docx）报告生成，及 /ask 随手一问的 self-grill 零人工路线。核心：grill 多波次需求拷问（唯一人工门）→ 8 维画像推导方法集与报告蓝图 → 分析技法注册表按需激活 → 盈利预测与估值确定性算子（数字由代码算）→ PUA 管理员逐章审问 → 单次审计（两会话合一，四道防掉队闸）→ 编号存档与 /drill 追问复盘闭环。
---

# 股票分析（Stock Analysis）v3.1 · 全自治流水线

泛金融报告 skill：**北极星是一份可用的报告**。用户只在 grill 时在场一次（批准 brief），之后流水线无人值守直到交付；/ask 路线连这一次也省——两个子代理自我拷问推导需求。任何对象（A股/房价/比特币/手办）先 grill 需求拷问 + 8 维画像，规则库（reference/library/，JSON 数据驱动）推导方法集/数据源/报告蓝图；**预测与估值数字由算子库计算，叙事由 LLM 写**；写作过程受 PUA 管理员逐章审问，终稿经**单次审计**（两会话合一，严格度不降级）；结论按**报告编号**自动存档，`/drill 编号` 随时回溯拷问，第 N 份报告站在第 N-1 份肩上。

## 命令（项目级 .opencode/command/）

| 命令 | 模式 | 说明 |
|---|---|---|
| `/ask 一句话问题` | self-grill | **零人工路线**：拷问者×应答者双子代理对谈（≤6 波）推导 brief → `self_approve` 自动批准（免责标注）→ 直接走 full 级流水线至 docx 交付 |
| `/grill [主题\|编号]` | 询问 | 多波次批量刨根（首波 ≥5 问）→ brief.json → 请求批准（**唯一人工门**）。已有 brief/已交付 → 提示改用 /drill |
| `/report [编号\|主题\|resume 编号]` | 执行 | 无 brief 先触发 /grill；有已批准 brief → 全自治流水线至交付 |
| `/drill [编号]` | 追问 | prompt 与询问不同：draft → 需求变更重审（变更须重新过人工门）；delivered → 回溯拷问（"你都写了啥"+承重柱检验+命中/失误判定+five_whys 归因）。self-grill 报告的 brief 修正亦走此门 |
| （PUA 无命令） | 自动 | desk_chief 逐章审问，工作流内自动执行 |

### self-grill（/ask）零人工路线

用户一句"XX能买吗"→ 编排器派两个互不可见子代理（`templates/self_grill_interviewer.md` 拷问者 + `templates/self_grill_responder.md` 应答者）按 grill 同款波次协议对谈：应答者每答标 **[代理推断·强/中/弱]** 或"中性·不确定"（禁编造用户私有信息，缺依据进盲区），拷问者对弱推断与模糊答必派生追问。产物 brief（`mode='self'`，waves 带 actor）→ `brief_lib.self_approve()` 自动批准（approval 带 auto+免责）→ **flow_level 锁 full、门禁不降级**（蓝图章节仍按 report_type 推导）→ 10 步流水线至 docx 双写。报告封面 meta+首页脚注必须标注"⚠ 需求由 self-grill 代理推导，未经用户确认"；完成摘要高亮 Top3 代理推断；波次耗尽仍有必填缺失时按务实偏好兜底填充（标弱推断）再批，禁止 blocked 悬停。事后修正：`/drill 编号`（模式A）→ `/report resume 编号`。

## 流程分级（按蓝图 flow 字段，拒绝过度流程）

| 级别 | 蓝图 | 流程 |
|---|---|---|
| full | equity_deep_8ch / asset_research / rental_asset | 单次审计 + PUA(P9 三问) + premortem/base_rate 强制 + 技法挂点开放 |
| standard | theme_quant / update_report | 单次审计 + PUA(P7 两问) + base_rate 强制 |
| minimal | strategy_manual / educational / decision_report | 仅基础分析→报告→QA（无审计无 PUA） |

## 全自治流水线（10 步；brief 批准后无人值守，异常走自动归宿表绝不悬停）

1. **grill 需求拷问**（用户在场，唯一人工门）：`brief_lib` 批量波次——每波 5~8 问（question 工具，每问 2~4 选项），波次序：需求根因→标的范围→深度方法→交付形态→约束禁写→验证复述；模糊词/新变量/自定义输入必派生 ≥2 追问；终止=连续两波无新决策变量/"够了"/完整性校验通过（上限 6 波）；批准后 `workspace_lib.init_workspace` 已建编号工作区，brief 落 `reports/{编号}_{主题}/brief.json`。**grill 以文件为状态：无 brief=询问，有 brief=追问（/drill，另一套 prompt）**。
2. **画像/推导/技法候选**：`profile_lib.derive(画像, brief.report_type)` → 方法集/源集/蓝图/QA；同资产先 `review_lib.load_dossier()` 复盘前次（更新报告复用 inherited，禁全量重跑）。`workspace_lib` 各挂点调 `technique_lib.recommend(profile, stage)`，编排器自主激活（每挂点 ≤3，必填理由 `activate(flow_log,…)`；always_on 如 full 级 premortem 不可跳过；无合适技法 → `propose_auto` 按证据门槛扩注册表）。建 `flow_log.FlowLog(scope=编号)`。
3. **数据抓取【侦察兵子代理】**：全新上下文 Task，**不知论点**，按推导源集用 fetch_lib（缓存优先，`save_json` 带 _meta），落工作区 `00_cache/`；同时产 `10_facts/FACTS.md`（中性事实清单：指标|数值|口径|asof|来源，**禁解读**，随后**冻结**——防"带着结果找答案"）。子代理输入包只传 3~8 个已登记文件路径（见 reference/subagent-protocol.md）。
4. **基础分析 + Premortem**（技法挂点"预测前"）：行业/业务/财务质量论断配可溯源数字；full 级强制事前验尸（"12 个月后被打脸的死因清单"）喂风险章与假设有效性表。
5. **预测建模**（心脏，LLM 禁手算）：`forecast_lib.build_equity_forecast / build_rental_forecast / build_supply_demand_balance`；每项假设 `Assumption(value, basis, tag, probability, base_rate_ref)`——增长类 [推断] 假设缺基础比率锚自动降级 [观点]（base_rate_downgrades 落盘）；技法分析师子代理可并行（互不可见）。
6. **估值**：`valuation_lib.run_derived` + `weighted_synthesis`（权重给理由，中枢禁手算）+ `crosscheck`（>1% 说明取舍）+ `flip_point`；分歧触发时 `profile_lib.ach_matrix`（按最少不一致排序）；情景挂点可激活 scenario_2x2/tornado。
7. **论点树 + 顺序分章写作 + PUA 逐章审问**：`thesis_lib.build_thesis`（结论→3~5 承重柱→证据映射）落 `40_thesis/`；章节写手子代理**严格顺序**写作（禁自行抓数，只消费 FACTS+算子输出；输入包=章节spec+树+相关数据文件）落 `60_draft/`；**每章交付后自动 desk_chief.md 审问**（P7/P9 分级，≤3 问：数字哪来的/So what/删了这章结论还立得住吗）→ `manager_log.ManagerLog.checkpoint` 落 `50_sessions/manager_log.json`；驳回自动重写（同章 ≤1 次），二次驳回转审计未决。
8. **单次审计（两会话合一，硬上限 2 轮）**：`dump_doc_text` 全文 → single_auditor.md 子代理（**全新上下文，唯一看全稿的对抗角色**；承重论点=树承重柱+核心结论，从 thesis.json 取不手挑；火力对齐 brief.failure_criteria）→ `socratic_lib.new_session(mode='single_audit')`；R1 攻防（受理质询+defend data/revise/unknown，revise 带 assumption_ref 触发 **H1 回流**：重跑 forecast→估值→更新树）→ R2 只核验修改处与未决。**四道防掉队闸（QA 硬检查）**：`audit_readiness`（R1 ≥4 条 full/≥3 条 standard，full 必含替代解读或隐含前提类）/ `audit_coverage`（每承重柱 ≥1 受理质询或 `exempt_pillar` 书面免检）/ `audit_gate`（高严重度质询无四归宿 → 禁止终稿）/ `audit_checklist` 自检进附录。会话落 `50_sessions/`。
9. **QA 质检**（0 错误才通过）：`check_report_depth`（含 brief.key_concerns 必须被回答）/ `usage_probe` / `cache_status --strict` / `check_delivery`（编号双写+注册表一致性）/ `render_check`；附录=溯源表+审计统计（含三闸自检）+管理员审问统计+数据截止表+新引入技法标注（`technique_lib.techniques_used`）。
10. **编号归档 + 完成摘要**：`save_stage(doc, 报告名, subject, review, report_no=编号)`——历史版落 `70_delivered/{日期}_{编号}_{名}.docx` + 最新版双写 `reports/所有报告/{编号}_{报告名}.docx`，注册表置 delivered，review 自动落 dossier；`flow_log.save(workspace_lib.flow_log_path(编号))`；输出完成摘要（编号/评级区间/审计统计/PUA 统计/生成成本/新引入技法//drill 提示）。**异常归宿**：轮次/预算超限 → `workspace_lib.blocked(编号, 卡点, '/report resume 编号')`，绝不悬停等人。

## 脚本使用（scripts/）

```python
# 1. 工作区/编号/brief（grill 与存档基座）
import workspace_lib as wl, brief_lib as blf
e = wl.init_workspace('中药行业'); no = e['no']
wl.register_file(no, path, kind='forecast', desc='3年盈利预测')   # WORKSPACE.md 自动更新
b = blf.new_brief('中药行业', report_no=no)
blf.record_wave(b, questions=[{'id':'q1','q':'报告类型？','options':['深度研究','主题量化']}]*5,
                answers=[{'question_id':'q1','answer':'深度研究'}]*5,
                decisions=[{'field':'report_type','value':'深度研究'}])
stop, why = blf.termination_check(b); ok, missing = blf.validate_brief(b)
blf.approve(b); blf.save_brief(b, wl.brief_path(no))

# 2. 技法注册表（按需激活 + 自动扩充）
import technique_lib as tcl
cands = tcl.recommend(profile, stage='预测前', blueprint_id='equity_deep_8ch', flow_level='full')
tcl.activate(flow_log, 'premortem', reason='full 级强制：估值前逼出失败路径')
tcl.propose_auto({'id':'my_tech','name':'…','stage':'风险','trigger':'…','protocol':'…',
                  'applies':'true','sources':[{'tier':'教材·论文','cite':'…'}]})

# 3. 盈利预测（base_rate_ref 外部视角）
from forecast_lib import Assumption, build_equity_forecast
a = Assumption(0.12, basis='行业8%+份额提升', tag='[推断]', probability=0.6,
               base_rate_ref='data/00_cache/industry_growth.json: 近10年行业增速分布 P25~P75')

# 4. 单次审计（mode='single_audit'，四道闸）
from socratic_lib import (new_session, submit_challenges, defend, should_continue,
                          revised_assumption_claims, exempt_pillar,
                          audit_readiness, audit_coverage, audit_gate, audit_checklist)
s = new_session('编号7·中药', load_bearing_claims=承重柱+核心结论, mode='single_audit')
adm = submit_challenges(s, challenges_json)
defend(s, adm[0]['id'], 'data', evidence_file='50_sessions/review_r1_01.json', note='…')
exempt_pillar(s, '行业格局稳定', reason='R1 已有两条柱级质询覆盖其证据链')  # 仅免检理由充分时
assert audit_readiness(s, 'full')['ok'] and audit_coverage(s, thesis)['ok'] and audit_gate(s)['pass']
if revised_assumption_claims(s): ...  # H1 回流：重跑预测估值再 R2 核验

# 5. PUA 管理员 / 交付
from manager_log import ManagerLog
ml = ManagerLog(scope='7_中药行业', persona='P9')
ml.checkpoint('ch3', summary='…', questions=[{'q':'数字哪来的','a':'00_cache/fin_x.json'}], verdict='过关')
dh.save_stage(doc, '中药行业深度研究报告.docx', subject='中药行业', review={...}, report_no=7)
```

## 关键经验（避免踩坑）

- **铁律零·唯一人工门**：用户只在 grill 批准时在场；此后一切异常走自动归宿（PUA 驳回自动重写/审计 revise 自动回流/数据失败降级标注/超限 blocked），悬停等人=违规
- **铁律一：数字由代码算**——预测/估值数字只出自 forecast_lib/valuation_lib；质询击穿假设必须回流（revised_assumption_claims 非空 → 重跑再估值）；QA 溯源：无算子输出而报告含估值数字 = FAIL
- **铁律二：先建树再写作**——thesis.json 贯穿写作与审计；审计员先通读重建树、pillar 级攻击，禁逐句扫描
- **铁律三：假设必带证据链+基础比率**——[实证]/[推断]/[观点]+依据+概率，裸（估）拦截；增长类 [推断] 缺 base_rate_ref 自动降级 [观点]
- **铁律四：反注水**——字数不足补新论点+新数据源，禁扩写旧文本
- **铁律五：审计简化不降级**——单次审计四道闸（火力/覆盖/门禁/自检）是硬检查，高严重度质询无归宿禁止终稿
- **铁律六：子代理防火墙**——主上下文纯编排不写分析文本；侦察兵不知论点、写手禁抓数、技法分析师并行互不可见、审计员全新上下文；输入包只传已登记文件路径
- **铁律七：文件即记忆**——一切产物落工作区并 register_file 登记；导航只读 _registry.json + WORKSPACE.md，禁全库扫描；跨工作区互读禁止（更新报告例外=inherited 显式指针）
- 方法必须来自推导：地产禁 PE 分位；比特币/手办禁 DCF/PE；无路可走 stats_baseline 标注"统计性描述"
- 技法不全部使用：每挂点 ≤3 且必填理由；always_on 不可跳过；注册表缺口走 propose_auto（机构方法论>教材·论文>GitHub≥100⭐）
- 东财批量 ≤100、腾讯 K 线 count≤800；抓取限速 0.3s、重试 3；缓存幂等覆盖
- 网格回测必须含 T+1、FIFO、免5 佣金、MC 多市况；报告数字口径估算标注（估）；stale 缓存标"数据截止日期"；图表全中文、img 带 source=

## 环境依赖

依赖见 `requirements.txt`。渲染自查需 LibreOffice（可选）。流程文档：`reference/subagent-protocol.md`（子代理输入包/FACTS 冻结/异常归宿）、`reference/analysis-techniques.md`（技法协议）、`reference/templates/`（grill·询问 / drill·追问 / desk_chief·PUA / single_auditor·审计 四模板）。

## 自测（修改 scripts/ 或规则库后必跑）

```bash
python scripts/selftest.py --offline   # 离线：画像/预测/算子/审计/工作区/brief/技法/PUA/QA 全套
python scripts/selftest.py             # 全量（含联网）
```

通过输出全部 PASS、退出码 0；任何失败退出码 1 并列出失败项。
