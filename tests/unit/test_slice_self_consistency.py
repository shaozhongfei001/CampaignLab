"""D-036 回归：lane F 页面卡的契约切片必须自洽。

背景（D-036）：切片顶层 `pages[*].meta.operation_ids` 由
`scripts/contract_slice.py` 从 `spec/ui/INDEX.md` 与页面正文实抽，
而 `operations` 段完全由 `--ops` 入参决定。两者一旦不同步，切片就
自带矛盾：「页面要调这些 op，但它们的 DTO 不在包里」。任务卡又一律
禁止回读 443 KB 活契约（D-011／D-012），lane 只剩两条路 —— 自造
opId 或停摆。M2-04 的 U-1（BLOCKING，A125 重切）即此形态；Round 9
全量审计又查出 M4-03 同型缺 9 个 op。本文件把该不变量钉死。

口径边界（A127）：本不变量**只适用于 lane F（纯前端页面卡）**。
lane D／S 的后端卡其 `operations` 段语义是「本卡实现面」，切片里的
`pages` 段只是上下文参考，页面引用的他人 op 不必进 `operations`；
对后端卡套用本不变量会诱导实现方去实现不属于自己的 op（Round 9 曾
据此误重切 M1-P01／M3-P01／M4-02／M4-P01 四张后端卡，已回滚，
见自我更正 R9-2）。

钉住的不变量（只依赖文件字节与 state.json，任何人可复跑）：

1. 分母断言：lane F 且含 `pages` 的切片数 >= 下限（防 glob 扫空假绿）；
2. union(pages[*].meta.operation_ids) 是 operations 键集合的子集；
3. `truncated_schemas == []`（D-020：截断即 rc=2，禁静默）；
4. 无 `missing` 键（A18：断言键不存在，禁断言 `== []`）；
5. `source.openapi` 的 bytes／sha16 与磁盘活契约逐位一致（D-004）；
6. `spec_version` == 活契约 `info.version`（禁硬编码）。
"""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
STATE = REPO / "orchestrator" / "state.json"
HANDOFF = REPO / "orchestrator" / "handoff"
OPENAPI = REPO / "contracts" / "openapi.json"

FRONTEND_LANE = "F"
# 防 glob 扫空导致全绿（手册 15.4：守护测试必须自带分母断言）。
# 现值 = M0-03 / M1-04 / M2-04 / M3-04 / M4-03；补齐一张即须上调。
MIN_FRONTEND_PAGE_SLICES = 5


def _tasks() -> dict[str, Any]:
    raw: Any = json.loads(STATE.read_text(encoding="utf-8"))
    assert isinstance(raw, dict), f"state.json 顶层必须是对象；实测 {type(raw).__name__}"
    tasks: Any = raw.get("tasks")
    assert isinstance(tasks, dict), f"state.json.tasks 必须是 dict；实测 {type(tasks).__name__}"
    return tasks


def _frontend_ids() -> set[str]:
    return {tid for tid, task in _tasks().items() if task.get("lane") == FRONTEND_LANE}


def _owner_of(stem: str, ids: set[str]) -> str | None:
    """把 `<TASK>.slice` 与 `<TASK>-S3b.slice` 两种命名都归到任务 id。"""
    best: str | None = None
    for tid in ids:
        matched = stem == tid or stem.startswith(tid + "-")
        if matched and (best is None or len(tid) > len(best)):
            best = tid
    return best


def _frontend_page_slices() -> list[tuple[str, Path, Any]]:
    """lane F 且 pages 段非空的切片；返回 (task_id, path, data)。"""
    ids = _frontend_ids()
    out: list[tuple[str, Path, Any]] = []
    for path in sorted(HANDOFF.glob("*.slice.json")):
        tid = _owner_of(path.name[: -len(".slice.json")], ids)
        if tid is None:
            continue
        data: Any = json.loads(path.read_bytes())
        assert isinstance(data, dict), f"{path.name} 顶层必须是对象"
        if data.get("pages"):
            out.append((tid, path, data))
    return out


def _page_referenced_ops(data: Any) -> set[str]:
    ops: set[str] = set()
    pages: Any = data.get("pages")
    assert isinstance(pages, dict), "pages 段必须是 dict"
    for page in pages.values():
        assert isinstance(page, dict), "pages 的每一项必须是 dict"
        meta: Any = page.get("meta")
        assert isinstance(meta, dict), "pages[*].meta 必须是 dict"
        ids: Any = meta.get("operation_ids")
        assert isinstance(ids, list), "pages[*].meta.operation_ids 必须是 list"
        ops.update(str(i) for i in ids)
    return ops


def _live_openapi() -> dict[str, Any]:
    blob = OPENAPI.read_bytes()
    info: Any = json.loads(blob.decode("utf-8")).get("info") or {}
    return {
        "bytes": len(blob),
        "sha16": sha256(blob).hexdigest()[:16],
        "version": info.get("version"),
    }


def test_denominator_frontend_page_slices() -> None:
    found = _frontend_page_slices()
    names = sorted(p.name for _, p, _ in found)
    assert len(found) >= MIN_FRONTEND_PAGE_SLICES, (
        f"lane F 含页面的切片数异常（疑似 glob 扫空导致假绿）："
        f"实测 {len(found)} {names}，下限 {MIN_FRONTEND_PAGE_SLICES}"
    )


def test_page_referenced_ops_are_all_inside_slice() -> None:
    bad: list[tuple[str, list[str]]] = []
    for tid, path, data in _frontend_page_slices():
        body: Any = data.get("operations")
        assert isinstance(body, dict), f"{path.name} 缺 operations 段"
        gap = sorted(_page_referenced_ops(data) - set(body))
        if gap:
            bad.append((f"{tid}({path.name})", gap))
    assert not bad, (
        "页面引用的 operationId 不在切片 operations 段内（D-036 形态）："
        "lane 禁回读活契约（D-011／D-012），缺 op 即硬阻塞，必须重切 -> "
        f"{bad}"
    )


def test_no_truncated_schemas() -> None:
    bad = [
        (tid, data.get("truncated_schemas"))
        for tid, _, data in _frontend_page_slices()
        if data.get("truncated_schemas") != []
    ]
    assert not bad, f"切片存在被截断的 schema（D-020：须提高 --depth）：{bad}"


def test_missing_key_is_absent_not_empty() -> None:
    bad = [tid for tid, _, data in _frontend_page_slices() if "missing" in data]
    assert not bad, f"A18 口径：切片不得出现 missing 键（未命中一律 rc=2）：{bad}"


def test_source_openapi_matches_live_contract() -> None:
    live = _live_openapi()
    bad: list[tuple[str, Any]] = []
    for tid, _, data in _frontend_page_slices():
        src: Any = data.get("source") or {}
        got: Any = src.get("openapi") if isinstance(src, dict) else None
        pair = (got.get("bytes"), got.get("sha16")) if isinstance(got, dict) else None
        if pair != (live["bytes"], live["sha16"]):
            bad.append((tid, got))
    assert not bad, (
        f"切片 source.openapi 与磁盘活契约不一致（D-004：禁静默过期）："
        f"{bad} != bytes={live['bytes']} sha16={live['sha16']}"
    )


def test_spec_version_matches_live_contract() -> None:
    live = _live_openapi()
    bad = [
        (tid, data.get("spec_version"))
        for tid, _, data in _frontend_page_slices()
        if data.get("spec_version") != live["version"]
    ]
    assert not bad, f"切片 spec_version 与活契约 info.version 不一致：{bad} != {live['version']}"
