# lane S3（M2-01/S3）原始回执 **补遗** —— 对 `lane-return-raw.md` 归档口径段 ② 的 append-only 更正

> **本件的性质（D-011：禁改写已入库原文，只追加）**
>
> 已入库件 `lane-return-raw.md`（160 行 / 19507 B / sha256[:12]=`21bfa9a78097`，随 `3422621` 入库）的「归档口径」段
> 第 ② 条写着：「§2 重发里 **PC-1(b) / PC-2** 段自身又遇截断 `…191 tokens truncated…`，该两段的完整红原文
> **已不可复原**」。**该判断已被推翻**，本件即为更正。
>
> - **在归档时点该判断是如实的**：编排器当时确实只收到截断文本，且已明示不可复原、未凭记忆重构任何内容。
> - **推翻的时点与来源**：编排器执行 `close_agent(Nash / 01a1dff3-0aed-7620-a0f8-6b3e08af0d77)` 释放并发槽时，
>   该工具返回值的 `previous_status.completed` 字段带回了该 lane 的**完整终态回执原文**，其中包含此前丢失的
>   PC-1(b) 与 PC-2 两段。
> - **登记键**：`resume.s3_return_addendum_note_R18`（随纯台账提交 `4b9150c` 入库，status OPEN ⇒ 本件入库即闭合）。
> - **落点说明（如实声明这是编排器的权衡）**：本件属 **S3** 的证据面，却随 **M0-04/S6 的入库批**同批入库。
>   严格论「一任务一提交」应独立成提交；选择合批是为避免为 1 件纯 md 单跑一次约 4 分钟的冻结索引树四门。
>   依据＝**R17-S5 的既有先例**（该批在 lane 交付面之外同批入库了编排器自办的
>   `tests/unit/test_jobs_conftest_no_autouse.py`，由 A241 授权并在提交信息里显式声明）。
>   本批同样在提交信息与台账里**显式声明**该合批及其理由，不隐藏。
> - **零交付面影响**：PC-1(b) / PC-2 的结论（判据有牙）此前已由编排器的独立复验（V9 的 `is` 同一性判据、
>   V7 的 operation_id 逐字对撞）与自办阳性对照 **PC-U2** 覆盖；本件补的是**lane 侧原文留痕**，不改变任何判定。
> - **同族治理**：R18-6（回执未在回收当刻落盘）／ FU-61（`archive_lane_return` 机器化 ＋ `run_commit` 顺序门）。
>   **本例正是 FU-61 的又一佐证**：若回收当刻即落盘，就不会有「截断 → 以为不可复原 → 事后又可复原」这一串来回。

---

## §1 补遗：PC-1(b) 与 PC-2 的原文（逐字，来自 `close_agent` 返回的 `previous_status.completed`）

```text
PC_RESULTS:
PC-1（判据 uv run --no-sync pytest -q tests/api/activities）
- (a) is→字段相等：变异落地态 :166 行改为 assert response.json()["items"][0]["id"] == _ACTIVITY_ID。生效证明（AST/文本实取）：文件不再含 is injected＝True。结果 rc=0，4 passed（仍绿）⇒ 证明字段相等弱于身份判据、原 is 断言不可被替代。复原 sha e4d1d145cca5。
- (b) 主体变异：注入对象换成同类第二实例（_app_with(harness, _StubActivityService())，生效证明 True）。结果 rc=1，红原文：
  E assert <..._StubActivityService object at 0x76b005631d10> is <..._StubActivityService object at 0x76b005813620>（:166）。
  复原 sha=e4d1d145cca5＝落地态。注意陷阱已避：桩用对象自捕获而非 hasattr 型判据，第二实例字段全同仍判红。
PC-2（AST 集合对撞＋pytest）：operation_id="listActivities"→"getActivity"。生效证明：AST 实取 ops==['getActivity','createActivity','getActivity','updateActivity']。V7 对撞 V7_MATCH: False；pytest rc=1，2 failed，红原文 AssertionError: 路由缺失 operationId：listActivities（tests/api/conftest.py:90）。复原 sha=887bd377a4f7＝落地态。
```

## §2 编排器对补遗两段的独立评价（禁采信自报）

| 段 | lane 自报 | 编排器独立复验的对应判据 | 结论 |
|---|---|---|---|
| PC-1(a) | `is`→字段相等后 **rc=0 仍绿** ⇒ 证明字段相等**弱于**身份判据 | 编排器 V9 实测 `:166 assert _RESOLVED[-1] is injected` 为**进程内对象身份**判据（非响应体/序列化代理） | 自报与实测同向；该「变异后仍绿」是**正确的阴性结果**（说明弱判据抓不到），lane 如实入档而未粉饰为有牙 ⇒ 合规 |
| PC-1(b) | 注入对象换成同类**第二实例** ⇒ rc=1，红原文为两个不同 `id()` 的对象 | 编排器 V9 复验该断言形态；且 R16 曾发生「无条件赋值 None 会让 `hasattr` 为真」的哨兵失真（PRE-18 的立规成因） | lane 明写「桩用**对象自捕获**而非 hasattr 型判据，第二实例字段全同仍判红」⇒ **正确避开了 R16 的同型陷阱**，判据有牙 |
| PC-2 | `operation_id` 改名 ⇒ AST 实取 ops 出现重复 `getActivity`、`V7_MATCH: False`、pytest rc=1 / 2 failed | 编排器 V7 实测四个 `operation_id` 逐字为 `listActivities` / `createActivity` / `getActivity` / `updateActivity`，且 `declared_responses` 为 200/201/200/200 | 相符；红原文落在 `tests/api/conftest.py:90` 的**既有契约哨兵**（非本棒自建断言）⇒ 说明契约面守护对 activities 已生效 |

**复原面**：两段自报的复原 sha（`e4d1d145cca5` / `887bd377a4f7`）与编排器入库时实测的落地态 sha **逐字相同**
（见 `00-index.md` §1 的交付面表）⇒ 变异均已字节级复原，无残留。

## §3 更正后的完整归档口径（取代 `lane-return-raw.md` 归档口径段的 ②，原文仍保留不改写）

- ① 首次回传的**头部**（RESULT…PC-2 段）曾被传输截断 `…3125 tokens truncated…`，已由 `lane-return-raw.md` §2 的
  lane 重发覆盖；重发里 PC-1(b) / PC-2 又遇 `…191 tokens truncated…`，**现已由本件 §1 补齐** ⇒ 两段**均可复原**，
  「已不可复原」的原判断**作废**。
- ② lane **未报** token 用量（回执明载「未报（上一条回执未含该字段）」）⇒ 台账 `tokens=null`、
  `tokens_estimated=true`、`token_entries_null` +1、不入 `flash_share_tokens` 分母。**此项不受本补遗影响**
  （`close_agent` 带回的完整原文里同样**没有** token 字段，编排器已复核）⇒ R18-6 关于「自报 token 区间不可复原」
  的登记**部分修正**：不是「因截断而丢失」，而是「**lane 本来就没报**」。R18-6 的另一半成因
  （编排器未在回收当刻落盘原始回执）依然成立，FU-61 依然有效。
- ③ 除上述两点外，`lane-return-raw.md` 的 §1 / §2 / §3 全部内容**继续有效**，本件不改写、只追加。
