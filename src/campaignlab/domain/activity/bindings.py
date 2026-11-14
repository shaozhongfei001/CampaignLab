"""活动绑定的有效期区间代数（M2-01 · S2a；design §3.4）。

``Binding`` 没有状态列，但**区间语义必须冻结**，否则「同一策略在这一天生效的是哪一条」
不可判定，AC-002 的「缺绑定」判定随之失效。本文件冻结四条判定与它们的顺序：

① 空区间 → ② 重复键 → ③ 相交 → ④ 证据未登记（裁定 **A198**）。

区间是 ``[valid_from, valid_until)``：**起日包含、截止日排除**（``DOMAIN.md``「绑定使用生效
起日包含、截止日排除」）。故 ``valid_until == valid_from`` 是空区间，切片 ``ddl.activity_bindings``
的 ``CHECK(valid_until>valid_from)`` 也会拒 —— 领域侧必须**先**判，否则数据库的完整性错误
会被兜成 500。

裁定 **A198**：同一 ``strategy_id`` 的绑定区间**部分重叠即拒**（取更严的「相交即拒」而非
「仅完全相同才拒」），故 ``intervals_intersect`` 是「起含止排」的标准相交式，**单独导出**
供测试直接打表。

``BindingDraft`` 是领域侧形态（``valid_*`` 为 ``datetime.date``，对齐契约 ``format=date``）；
``Binding`` 契约 DTO 住 ``api/common.py``（design §2.1 / §11.2），二者字段一一对应、
都**没有 ``id``** —— ``Binding`` 的身份是 ``(strategy_id, source_version, valid_from)``
（切片 ``ddl.activity_bindings`` 的主键去掉 ``workspace_id`` / ``activity_id``），
DTO 里发明一个 ``id`` 会被 ``additionalProperties: false`` 当场判红。

本文件不含 SQL 文本、不开事务、不取系统时间；``registered_evidence_ids`` 由调用方从
``evidence`` 表只读查出后注入（切片有 ``(workspace_id, evidence_id)`` 的外键，且
``Binding.evidence_id`` **非空**）。
"""

from __future__ import annotations

from collections.abc import Callable, Collection, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Final

from campaignlab.domain.activity.clauses import GateIssue

__all__ = [
    "BINDING_ISSUE_CODES",
    "BINDING_SORT_KEY",
    "BindingDraft",
    "intervals_intersect",
    "validate_bindings",
]

#: 本文件产出的全部 ``Issue.code`` 标签（design §3.4，裁定 A198：**禁另编**）。
#: 与 ``Problem.code`` 的 20 码注册表是两个面；四条都落在 422 上
#: （前三条 ``VALIDATION_ERROR``，第四条 ``EVIDENCE_REQUIRED``，见 design §6.4）。
BINDING_ISSUE_CODES: Final[tuple[str, ...]] = (
    "BINDING_EMPTY_INTERVAL",
    "BINDING_OVERLAP",
    "BINDING_DUPLICATE_KEY",
    "BINDING_EVIDENCE_UNREGISTERED",
)


@dataclass(frozen=True, slots=True)
class BindingDraft:
    """一条待校验的绑定（5 字段全必填，无 ``id``）。

    ``valid_from`` / ``valid_until`` 是 ``datetime.date``（契约 ``format=date``，**日期**而非时刻；
    落库为 TEXT）。``evidence_id`` **非空**（契约与 DDL 双向要求）。
    """

    strategy_id: str
    source_version: str
    valid_from: date
    valid_until: date
    evidence_id: str


def _sort_key(draft: BindingDraft) -> tuple[date, str, str]:
    return (draft.valid_from, draft.strategy_id, draft.source_version)


#: design §7.4 冻结的 ``Activity.bindings`` 数组顺序：
#: ``valid_from ASC, strategy_id ASC, source_version ASC``（**禁各处不一**）。
#: 做成可直接喂给 ``sorted(..., key=BINDING_SORT_KEY)`` 的常量。
BINDING_SORT_KEY: Final[Callable[[BindingDraft], tuple[date, str, str]]] = _sort_key


def intervals_intersect(a: BindingDraft, b: BindingDraft) -> bool:
    """「起含止排」的标准相交式（裁定 A198）：``a.from < b.until AND b.from < a.until``。

    **部分重叠返回 ``True``**（不是「仅完全相同才相交」）。两条推论：

    - 空区间（``until <= from``）与任何区间都不相交 —— 故 ``validate_bindings`` 必须
      **先**判空区间，否则一个空区间会静默通过唯一性判定；
    - 端点相接（``a.until == b.from``）**不**相交：``[1,5)`` 与 ``[5,9)`` 是两条可以共存的
      权威绑定，这正是「止日排除」的意义所在。
    """
    return a.valid_from < b.valid_until and b.valid_from < a.valid_until


def validate_bindings(
    *,
    drafts: Sequence[BindingDraft],
    registered_evidence_ids: Collection[str],
) -> tuple[GateIssue, ...]:
    """按 A198 的四条顺序收集**全部**违例（不是首错即返），四项一律 ``severity="ERROR"``。

    ``location`` 用**数组下标**（``/bindings/<i>/…``）而不是键名：``Binding`` 没有身份键
    （design §5.3 末条明确这个差异是刻意的，禁与 ``/terms/<key>`` 统一）。

    - ① 空区间：``/bindings/<i>/valid_until``、``BINDING_EMPTY_INTERVAL``
      → 422 ``VALIDATION_ERROR``；
    - ② 重复键：``(strategy_id, source_version, valid_from)`` 重复会撞主键，
      ``/bindings/<i>``、``BINDING_DUPLICATE_KEY`` → 422 ``VALIDATION_ERROR``
      （禁让完整性错误冒到 500）；
    - ③ 相交：同 ``strategy_id`` 且区间相交，**同时**给出两条的 location
      （``/bindings/<i>/valid_from`` 与 ``/bindings/<j>/valid_from``）、``BINDING_OVERLAP``
      → 422 ``VALIDATION_ERROR``；
    - ④ 证据未登记：``/bindings/<i>/evidence_id``、``BINDING_EVIDENCE_UNREGISTERED``
      → 422 ``EVIDENCE_REQUIRED``（design §6.4）。

    ``message`` 里**不回显** ``evidence_id``（未登记的 ID 回显出去就是一个探测面）；
    ``strategy_id`` 与 ``bank_id`` 同理是客户端自己刚提交的值，回显用于「明确定位」
    （design §6.4 的 ``DUPLICATE_EXTERNAL_ACTIVITY`` 同一尺度）。
    """
    issues: list[GateIssue] = []

    # ① 空区间（起含止排 ⇒ until <= from 即空）。
    for index, draft in enumerate(drafts):
        if draft.valid_until <= draft.valid_from:
            issues.append(
                GateIssue(
                    code="BINDING_EMPTY_INTERVAL",
                    location=f"/bindings/{index}/valid_until",
                    message=(
                        f"绑定 {index} 的有效期为空区间"
                        f"（{draft.valid_from.isoformat()} 起含止排，截止日必须晚于起日）"
                    ),
                    severity="ERROR",
                )
            )

    # ② 重复键（撞主键的三元组）。
    first_seen: dict[tuple[str, str, date], int] = {}
    for index, draft in enumerate(drafts):
        key = (draft.strategy_id, draft.source_version, draft.valid_from)
        previous = first_seen.get(key)
        if previous is None:
            first_seen[key] = index
            continue
        issues.append(
            GateIssue(
                code="BINDING_DUPLICATE_KEY",
                location=f"/bindings/{index}",
                message=(
                    f"绑定 {index} 与绑定 {previous} 的策略、源版本与生效起日完全相同"
                    f"（策略 {draft.strategy_id}）"
                ),
                severity="ERROR",
            )
        )

    # ③ 同策略区间相交（部分重叠即拒，A198）。
    for left in range(len(drafts)):
        for right in range(left + 1, len(drafts)):
            first, second = drafts[left], drafts[right]
            if first.strategy_id != second.strategy_id:
                continue
            if not intervals_intersect(first, second):
                continue
            message = (
                f"同一策略 {first.strategy_id} 下绑定 {left} 与绑定 {right} 的有效期相交，"
                "该策略在该日生效的是哪一条不可判定"
            )
            issues.append(
                GateIssue(
                    code="BINDING_OVERLAP",
                    location=f"/bindings/{left}/valid_from",
                    message=message,
                    severity="ERROR",
                )
            )
            issues.append(
                GateIssue(
                    code="BINDING_OVERLAP",
                    location=f"/bindings/{right}/valid_from",
                    message=message,
                    severity="ERROR",
                )
            )

    # ④ 证据未登记（切片有外键，但领域侧先判以便给出字段级 location）。
    for index, draft in enumerate(drafts):
        if draft.evidence_id not in registered_evidence_ids:
            issues.append(
                GateIssue(
                    code="BINDING_EVIDENCE_UNREGISTERED",
                    location=f"/bindings/{index}/evidence_id",
                    message=f"绑定 {index} 的来源未登记（本工作区内查无此证据行）",
                    severity="ERROR",
                )
            )

    return tuple(issues)
