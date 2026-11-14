"""``compareRules`` 的字段差异（M2-01 · S2a；design §6.5）。

裁定 **A201**：活契约 ``components.schemas.Problem`` 只有 7 个属性且
``additionalProperties: false`` ⇒ 409 的响应体里**不存在也不允许**出现 ``diff`` 字段。
「差异」因此分成两处**都存在**的口径：409 侧走 ``Problem.issues[]``（code ＋ location），
``compareRules`` 侧走 ``RuleDiff.changes[].path`` —— 本文件只管后者。

冻结的 ``path`` 取值域**只有四类**（禁发明第五类）：``/label``、``/source_rule_version``、
``/content/<字段名>``、``/terms/<key>`` 与 ``/terms/<key>/<字段名>``。条款用**键名**而非数组
下标（条款的身份是 ``key``，下标会随客户端顺序漂移；``bindings`` 侧才用下标，design §5.3 末条）。

**只比较参与摘要的投影 ＋ ``label``**（design §4.6）：``id`` / ``revision`` / ``created_at`` /
``confirmed_at`` / ``confirmation`` / ``state`` / ``activity_id`` / ``parent_rule_id`` **不进**
``changes`` —— 它们不是「候选字段变化」（``RULES.md``「候选字段变化可在草稿中比较」）。
故本函数的两个入参就是 ``digests.digest_projection(...)`` 的信封再挂一个 ``label`` 键。

``before`` / ``after`` 的契约类型是 ``string | null``（0–1000），**不是**任意 JSON ⇒
一切取值先经 ``render_scalar`` 字符串化；条款整条新增／删除时用调用方注入的 ``canonicalize``
（＝``api/common.py::canonical_json``）渲染整条，与摘要同一份规范化实现。

本文件不含 SQL 文本、不开事务、不取系统时间。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any, Final

from campaignlab.domain.errors import InternalFailure

__all__ = [
    "DIFF_PATH_CONTENT_PREFIX",
    "DIFF_PATH_LABEL",
    "DIFF_PATH_SOURCE_VERSION",
    "DIFF_PATH_TERMS_PREFIX",
    "FIELD_CHANGE_MAX_LENGTH",
    "FieldChangeDraft",
    "field_changes",
    "render_scalar",
]

#: 四类 path（design §6.5）。前两个是完整 path，后两个是**前缀**（后面还要接字段名／键名）。
DIFF_PATH_LABEL: Final = "/label"
DIFF_PATH_SOURCE_VERSION: Final = "/source_rule_version"
DIFF_PATH_CONTENT_PREFIX: Final = "/content/"
DIFF_PATH_TERMS_PREFIX: Final = "/terms/"

#: ``FieldChange.before`` / ``.after`` 的 maxLength。真值来源＝
#: ``components.schemas.FieldChange.properties.before.maxLength``（实测 1000）。
#: 超限**不截断**（截断会破坏可复查性）⇒ 抛 500 ``INTERNAL_ERROR``（design §6.5）。
FIELD_CHANGE_MAX_LENGTH: Final = 1000


@dataclass(frozen=True, slots=True)
class FieldChangeDraft:
    """一条字段差异的领域侧形态（api 层直接搬进契约 ``FieldChange``）。

    ``path`` **只准**是上面四类之一；``before`` / ``after`` 是 ``render_scalar`` 之后的
    字符串或 ``None``（``None`` 渲染成 JSON ``null``，表示「这一侧没有该字段／该条款」）。
    """

    path: str
    before: str | None
    after: str | None


def render_scalar(value: object) -> str | None:
    """design §6.5 的字符串化口径：整数十进制、布尔 ``true``/``false``、时刻 ISO、
    ``None`` 保持 ``None``。

    判定顺序**不可调**：``bool`` 是 ``int`` 的子类，先判 ``int`` 会把 ``True`` 渲染成 ``"1"``；
    ``datetime`` 是 ``date`` 的子类，故一个 ``isinstance(value, date)`` 分支同时覆盖两者，
    且 ``isoformat()`` 按实际类型分派（时刻带偏移、日期只有年月日）。

    字符串原样返回（``model_dump(mode="json")`` 已把时刻变成 ISO 串，无需二次处理）。
    投影里只会出现标量；万一出现别的类型，退化为 ``str(value)`` 以保持**纯函数不抛**
    （可复跑性优先于「早炸」——长度上限另有 ``FIELD_CHANGE_MAX_LENGTH`` 兜底）。
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        return value
    return str(value)


def _capped(rendered: str | None) -> str | None:
    """超契约上限即 500（design §6.5：**禁截断**，截断会让差异不可复查）。"""
    if rendered is not None and len(rendered) > FIELD_CHANGE_MAX_LENGTH:
        raise InternalFailure(f"字段差异渲染长度超出契约上限 {FIELD_CHANGE_MAX_LENGTH}")
    return rendered


def _as_mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _terms_by_key(value: object) -> dict[str, Mapping[str, Any]]:
    """把条款数组收成 ``{key: 条款}``（design §4.3 的 G3 已保证同键不重复）。"""
    if isinstance(value, str) or not isinstance(value, Sequence):
        return {}
    grouped: dict[str, Mapping[str, Any]] = {}
    for term in value:
        mapping = _as_mapping(term)
        grouped[str(mapping.get("key", ""))] = mapping
    return grouped


def field_changes(
    *,
    baseline: Mapping[str, Any],
    candidate: Mapping[str, Any],
    canonicalize: Callable[[object], str],
) -> tuple[FieldChangeDraft, ...]:
    """比较两个「投影信封 ＋ ``label``」，返回稳定排序后的差异数组。

    排序（design §6.5 冻结，S6 直接断言整个数组）：
    ``/label`` → ``/content/*`` 按字段名字典序 → ``/source_rule_version`` →
    ``/terms/*`` 按 ``key`` 字典序（同一 key 内再按字段名字典序）。

    条款整条新增／删除 ⇒ ``path="/terms/<key>"``，一侧为 ``None``、另一侧为
    ``canonicalize(条款)``；两侧都在 ⇒ 逐字段比较，``path="/terms/<key>/<字段名>"``。
    ``changes`` 为空是合法结果（无字段变化 ⇒ ``requires_rerun_case_ids`` 也直接为空，
    但那一步在 service 层，不在本函数）。
    """
    staged: list[tuple[int, str, str, FieldChangeDraft]] = []

    baseline_label = baseline.get("label")
    candidate_label = candidate.get("label")
    if baseline_label != candidate_label:
        staged.append(
            (
                0,
                "",
                "",
                FieldChangeDraft(
                    path=DIFF_PATH_LABEL,
                    before=_capped(render_scalar(baseline_label)),
                    after=_capped(render_scalar(candidate_label)),
                ),
            )
        )

    baseline_content = _as_mapping(baseline.get("content"))
    candidate_content = _as_mapping(candidate.get("content"))
    for field in sorted(set(baseline_content) | set(candidate_content)):
        before = baseline_content.get(field)
        after = candidate_content.get(field)
        if before == after:
            continue
        staged.append(
            (
                1,
                field,
                "",
                FieldChangeDraft(
                    path=DIFF_PATH_CONTENT_PREFIX + field,
                    before=_capped(render_scalar(before)),
                    after=_capped(render_scalar(after)),
                ),
            )
        )

    baseline_source = baseline.get("source_rule_version")
    candidate_source = candidate.get("source_rule_version")
    if baseline_source != candidate_source:
        staged.append(
            (
                2,
                "",
                "",
                FieldChangeDraft(
                    path=DIFF_PATH_SOURCE_VERSION,
                    before=_capped(render_scalar(baseline_source)),
                    after=_capped(render_scalar(candidate_source)),
                ),
            )
        )

    baseline_terms = _terms_by_key(baseline.get("terms"))
    candidate_terms = _terms_by_key(candidate.get("terms"))
    for key in sorted(set(baseline_terms) | set(candidate_terms)):
        before_term = baseline_terms.get(key)
        after_term = candidate_terms.get(key)
        if before_term is None or after_term is None:
            staged.append(
                (
                    3,
                    key,
                    "",
                    FieldChangeDraft(
                        path=DIFF_PATH_TERMS_PREFIX + key,
                        before=None if before_term is None else _capped(canonicalize(before_term)),
                        after=None if after_term is None else _capped(canonicalize(after_term)),
                    ),
                )
            )
            continue
        for field in sorted(set(before_term) | set(after_term)):
            before = before_term.get(field)
            after = after_term.get(field)
            if before == after:
                continue
            staged.append(
                (
                    3,
                    key,
                    field,
                    FieldChangeDraft(
                        path=f"{DIFF_PATH_TERMS_PREFIX}{key}/{field}",
                        before=_capped(render_scalar(before)),
                        after=_capped(render_scalar(after)),
                    ),
                )
            )

    staged.sort(key=lambda item: (item[0], item[1], item[2]))
    return tuple(item[3] for item in staged)
