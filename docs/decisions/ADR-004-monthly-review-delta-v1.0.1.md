# ADR-004 采纳 CampaignLab SDD v1.0.1「全行月报」增量契约

- 状态：ACCEPTED
- 日期：2026-11-12（Asia/Shanghai）
- 裁定人：项目负责人（以补丁包 `CampaignLab-SDD-Patch-v1.0.1-Monthly-Review-Delta` 为裁定载体）
- 关联：CR-001、ADR-001（批准范围）、ADR-002（实施细节）、ADR-003（前端设计基线）

## 背景
v1.0 交付两条端到端流程（满额赠券规则验证、远程回拨策略复盘）。补丁新增第三条流程「全行月报」：
月度快照接入、三月交集与共同范围、参与度与重复触达、渠道容量与客群产能、总分行去重、
月报报告与签认、补采更正与下期观察，并附 12 条验收（AC-MR-01..12）、页面说明与合成样例。

## 决策
1. 补丁包按字节入库为**第三份不可变基线** `spec/CampaignLab-SDD-Patch-v1.0.1-Monthly-Review-Delta/`
   （22 个文件；`DELTA-SHA256SUMS` 21 项校验 OK；源 ZIP SHA256 `13b1be8c…`）。
2. 补齐手册第 7 节要求而 wave0 遗漏的**活契约目录** `contracts/`，初始为 v1.0 基线的逐字节副本，
   并附 `contracts/PROVENANCE.md` 溯源。
3. 契约合入一律走补丁自带 `tools/monthly_delta.py`：先只读预检分类（ADD/ALREADY/UPDATE/KEEP/CONFLICT），
   再用 `--stage` 生成候选，最后由编排器覆盖活契约。**禁止手工编辑大 JSON**。
4. 全部差异登记 `contracts/CHANGES.json`，新增 CI 门禁 `scripts/check_contracts.py check`
   强制「实测结构差异 ⇄ 登记项」一一对应，且每项必须有真实存在的 CR 与 ADR 文件。
5. 验收基线由 **35 条扩为 47 条**（新增 AC-MR-01..12）；交付计划插入 6 个 P 任务
   （M0-P01、M1-P01、M3-P01、M3-P02、M4-P01、M5-P01），依赖见 `docs/delivery/MONTHLY-DELTA-PLAN.md`。

## 备选方案与拒绝理由
| 备选 | 结论 |
|---|---|
| 直接手改 `contracts/openapi.json` 加节点 | 拒绝：430KB 文件手改不可审计，易漏 `required`/`$ref` 一致性 |
| 把月报内容写回 `spec/CampaignLab-SDD-v1.0/` | 拒绝：破坏基线 SHA256 可验性与「基线不可变」不变量 |
| 只留补丁包、不建活契约 | 拒绝：实现无唯一契约真值，前后端会各自解释，且 CI 无从守漂移 |

## 影响
- 活契约 `info.version` = 1.0.1；前端类型客户端必须重新生成（M0-03 门禁：openapi-typescript 产物 diff 为空）。
- M1 需支持月报输入与 `DISTINCT_CUSTOMER`、扩展粒度、等价 CSV；M3 需实现三月交集、两种覆盖率、
  容量/客均、客群与总分行互斥集合；M4 需支持 PARTIAL_DRAFT、补采签认、更正与下期观察；M5 增加第三条走查。
- 新增合成样例（source-01..04、monthly-golden、map-monthly、csv-equivalent）进入 fixtures 使用范围，
  仍属合成数据，不触碰真实银行数据不变量。

## 未决（不阻塞开发）
- 行内真实分母、口径归属、客户键、容量定义：沿用 BLK-04 与 SRC-1 的 `PENDING_OWNER` 机制，
  合成语义先行验证「待补分支」，实际取数依赖保留在待办中。