"""S2b-1：M2-01 应用层／仓储层／提供器面的静态守护（符号面一律实取对撞，A115）。

钉住派单文 §5.7 与 §5.8 的六件事：

1. ``infra/db/repositories.py`` 的公开面是**纯追加**：既有名一个不少，新增名恰为
   design §11.3 第二条的 3 个 Record ＋ 3 个 Repository；私有行映射不进 ``__all__``
   （体例＝既有 ``_workspace_of`` / ``_job_of``）；
2. ``api/deps.py`` 的公开面同理：既有 3 Protocol ＋ 6 提供器一个不少，新增恰为 4 名；
3. 两个新 Protocol 的成员面与 ``application/activity_service.py`` 两个实现类的公开方法面
   **逐字相等**（``inspect`` 实取 ↔ 实取对撞，不抄字面量计数）；
4. ``api/deps.py`` 的私有取值助手**只有一个** ``_state_service``，两个新提供器都调它
   （design §11.10 的方案 A；复制出第二个私有助手即红 —— 派单文 §6②）；
5. 游标密钥与 ``BAD_CURSOR_DETAIL`` **复用** ``workspace_service`` 的那一份，本模块不出现
   第二把密钥／第二句 detail（派单文 §6③）；
6. ``application/activity_service.py`` 里**零** SQL 写点（A81）；扫描器带正向对照
   （在 ``tmp_path`` 造违规探针，断言抓得到）。

另附「零新增」断言：``PROBLEM_CODES`` 与 ``DomainError`` 子类的面与 S2a 入库时点一致
（design §11.2 已冻结，本棒无写权）。计数型断言一律写成集合对撞，本文件不出现
``len(...) == <字面量>``（A115）。
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine

import campaignlab.api.common as common
import campaignlab.application.activity_service as activity_service
import campaignlab.application.workspace_service as workspace_service
import campaignlab.domain.errors as domain_errors
import campaignlab.infra.db.repositories as repositories
from campaignlab.api import deps
from campaignlab.clock import Clock, FixedClock
from campaignlab.config import AppConfig, load_config
from campaignlab.infra.db.engine import make_engine

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "src" / "campaignlab"
ACTIVITY_SERVICE_PY = SRC / "application" / "activity_service.py"
REPOSITORIES_PY = SRC / "infra" / "db" / "repositories.py"
DEPS_PY = SRC / "api" / "deps.py"
T0 = datetime(2026, 11, 15, 1, 0, 0, tzinfo=UTC)

#: S2b-1 开工时点 ``repositories.__all__`` 的既有面（派单文 §3 冻结表实测值）。
REPOSITORIES_PREEXISTING = frozenset(
    {
        "ArtifactRecord",
        "ArtifactRepository",
        "AuditRecord",
        "AuditRepository",
        "IdempotencyRecord",
        "IdempotencyRepository",
        "JobRecord",
        "JobRepository",
        "WorkspaceRepository",
        "job_from_row",
    }
)
#: design §11.3 第二条要求本棒追加的 6 个公开名（3 Record ＋ 3 Repository）。
REPOSITORIES_ADDED = frozenset(
    {
        "ActivityBindingRepository",
        "ActivityRecord",
        "ActivityRepository",
        "BindingRecord",
        "RuleVersionRecord",
        "RuleVersionRepository",
    }
)
#: 开工时点 ``api/deps.__all__`` 的既有面（派单文 §3 冻结表实测值）。
DEPS_PREEXISTING = frozenset(
    {
        "HealthService",
        "SessionService",
        "WorkspaceService",
        "get_clock",
        "get_config",
        "get_health_service",
        "get_session_service",
        "get_workspace_service",
        "require_session",
    }
)
#: design §11.3 第三条要求本棒追加的 4 个名（2 Protocol ＋ 2 提供器）。
DEPS_ADDED = frozenset(
    {"ActivityService", "RuleService", "get_activity_service", "get_rule_service"}
)
ACTIVITY_REPOSITORY_METHODS = frozenset(
    {
        "find_by_external",
        "get",
        "insert",
        "list_page",
        "list_receipt_ids",
        "list_rule_ids",
        "set_current_rule",
        "update_fields",
    }
)
BINDING_REPOSITORY_METHODS = frozenset(
    {"evidence_exists", "list_for_activities", "list_for_activity", "replace_set"}
)
RULE_REPOSITORY_METHODS = frozenset(
    {
        "confirm",
        "get",
        "insert",
        "list_confirmed_case_ids",
        "list_confirmed_siblings",
        "list_page",
        "update_draft",
    }
)
#: 列序＝design §2.4 的落库映射（与 ``contracts/sqlite-v1.sql`` 同源），顺序也要钉住。
ACTIVITY_RECORD_FIELDS = (
    "workspace_id",
    "id",
    "name",
    "bank_id",
    "external_activity_id",
    "description",
    "status",
    "current_rule_id",
    "revision",
    "created_at",
)
BINDING_RECORD_FIELDS = (
    "workspace_id",
    "activity_id",
    "strategy_id",
    "source_version",
    "valid_from",
    "valid_until",
    "evidence_id",
)
RULE_VERSION_RECORD_FIELDS = (
    "workspace_id",
    "id",
    "activity_id",
    "parent_rule_id",
    "label",
    "template",
    "source_rule_version",
    "state",
    "revision",
    "content_json",
    "terms_json",
    "digest",
    "created_at",
    "confirmed_at",
    "confirmation",
)
#: design §7.3 的审计 action 字面值（落进 ``audit.action`` 列，是对外可见值）。
AUDIT_ACTIONS = {
    "ACTION_ACTIVITY_CREATED": "ACTIVITY_CREATED",
    "ACTION_ACTIVITY_UPDATED": "ACTIVITY_UPDATED",
    "ACTION_ACTIVITY_ARCHIVED": "ACTIVITY_ARCHIVED",
    "ACTION_RULE_DRAFT_CREATED": "RULE_DRAFT_CREATED",
    "ACTION_RULE_SUCCESSOR_DRAFT_CREATED": "RULE_SUCCESSOR_DRAFT_CREATED",
    "ACTION_RULE_CONTENT_UPDATED": "RULE_CONTENT_UPDATED",
    "ACTION_RULE_LABEL_UPDATED": "RULE_LABEL_UPDATED",
    "ACTION_RULE_CONFIRMED": "RULE_CONFIRMED",
}
AUDIT_TARGET_KINDS = {
    "TARGET_KIND_ACTIVITY": "activity",
    "TARGET_KIND_RULE": "rule",
}
#: design §11.3 第一条的 6 个 detail 常量名（一律固定中文短句，禁调用点现编）。
DETAIL_CONSTANTS = frozenset(
    {
        "ARCHIVED_DETAIL",
        "DIGEST_MISMATCH_DETAIL",
        "DUPLICATE_EXTERNAL_DETAIL",
        "EMPTY_PATCH_DETAIL",
        "IMMUTABLE_DETAIL",
        "NOTE_REQUIRED_DETAIL",
    }
)
#: design §11.3 第一条枚举的全部 26 个公开名（8 action ＋ 2 target ＋ 2 前缀 ＋ 6 detail
#: ＋ 3 Outcome ＋ 2 service ＋ 3 游标面）。
SERVICE_PUBLIC_SURFACE = (
    DETAIL_CONSTANTS
    | frozenset(AUDIT_ACTIONS)
    | frozenset(AUDIT_TARGET_KINDS)
    | frozenset(
        {
            "ACTIVITY_ID_PREFIX",
            "RULE_ID_PREFIX",
            "ActivityCreateOutcome",
            "ActivityService",
            "ActivityWriteOutcome",
            "RuleService",
            "RuleWriteOutcome",
            "ACTIVITIES_CURSOR_VERSION",
            "activity_query_digest",
            "rule_query_digest",
        }
    )
)
#: design §11.2 冻结的错误面：本棒**零新增** ``Problem.code`` 与 ``DomainError`` 子类。
PROBLEM_CODES_FROZEN = frozenset(
    {
        "ACCESS_DENIED",
        "ACTION_REVIEW_REQUIRED",
        "BAD_CURSOR",
        "BAD_REQUEST",
        "EVIDENCE_REQUIRED",
        "IDEMPOTENCY_CONFLICT",
        "INPUT_TOO_LARGE",
        "INTERNAL_ERROR",
        "INVALID_SCOPE",
        "JOB_CAPACITY",
        "ORIGIN_DENIED",
        "PRECONDITION_REQUIRED",
        "RESOURCE_NOT_FOUND",
        "REVISION_CONFLICT",
        "SESSION_EXPIRED",
        "SNAPSHOT_CONFLICT",
        "STALE_CANDIDATE",
        "STATE_CONFLICT",
        "VALIDATION_ERROR",
        "VERSION_MISMATCH",
    }
)
DOMAIN_ERRORS_FROZEN = frozenset(
    {
        "AccessDenied",
        "ArtifactCommitFailed",
        "IdempotencyConflict",
        "InputTooLarge",
        "InternalFailure",
        "InvalidScope",
        "JobCapacity",
        "OriginDenied",
        "PreconditionRequired",
        "ResourceNotFound",
        "RevisionConflict",
        "SessionInvalid",
        "StateConflict",
        "ValidationFailure",
    }
)

_SQL_SHAPE = re.compile(
    r"\b(SELECT\b[\s\S]*?\bFROM\b|INSERT\s+INTO\b|UPDATE\s+\w+\s+SET\b"
    r"|DELETE\s+FROM\b|CREATE\s+TABLE\b|DROP\s+TABLE\b|ALTER\s+TABLE\b)",
    re.IGNORECASE,
)


def _read(path: Path) -> str:
    assert path.is_file(), f"被测源文件读不到：{path}"
    return path.read_text(encoding="utf-8")


def _docstring_nodes(tree: ast.Module) -> set[int]:
    """收集所有 docstring 节点的 ``id``：扫描 SQL 字面量时跳过它们（注释不是写点）。"""
    found: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            body = getattr(node, "body", [])
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                found.add(id(body[0].value))
    return found


def _sql_write_points(source: str) -> list[str]:
    """A81 扫描器：返回违规清单（空列表＝干净）。

    三类违规：① 名为 ``text`` 的调用；② 从 ``sqlalchemy`` 引入 ``text``；
    ③ 任何**非 docstring** 的字符串字面量里出现 SQL 形状（``UPDATE … SET`` /
    ``DELETE FROM`` / ``INSERT INTO`` / ``SELECT … FROM`` / DDL）。
    """
    tree = ast.parse(source)
    docstrings = _docstring_nodes(tree)
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            callee = ""
            if isinstance(func, ast.Name):
                callee = func.id
            elif isinstance(func, ast.Attribute):
                callee = func.attr
            if callee == "text":
                found.append(f"L{node.lineno}: text() 调用")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.startswith("sqlalchemy"):
                for alias in node.names:
                    if alias.name == "text":
                        found.append(f"L{node.lineno}: 从 {module} 引入 text")
        elif (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstrings
            and _SQL_SHAPE.search(node.value)
        ):
            found.append(f"L{node.lineno}: SQL 字面量")
    return found


def _dataclass_flags(cls: object) -> tuple[bool, bool]:
    """取 ``frozen`` / ``slots`` 两个参数（``__dataclass_params__`` 属实现细节）。"""
    params = getattr(cls, "__dataclass_params__", None)
    assert params is not None, f"{cls} 不是 dataclass"
    return bool(params.frozen), bool(params.slots)


def _public_methods(cls: type) -> set[str]:
    return {
        name for name, value in vars(cls).items() if not name.startswith("_") and callable(value)
    }


def _protocol_members(port: type) -> set[str]:
    """取 Protocol 声明的成员名（``__protocol_attrs__`` 属实现细节，故用 getattr 取）。"""
    return {str(name) for name in getattr(port, "__protocol_attrs__", ())}


def _module_level_private_functions(path: Path) -> set[str]:
    tree = ast.parse(_read(path))
    return {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name.startswith("_")
    }


def _function_def(path: Path, name: str) -> ast.FunctionDef:
    tree = ast.parse(_read(path))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{path.name} 里找不到顶层函数 {name}")


@pytest.fixture
def engine() -> Engine:
    """只做结构校验，不建表：内存库足够（用例级建库在 test_s2b_activity_* 里做）。"""
    return make_engine("sqlite://")


@pytest.fixture
def config(tmp_path: Path) -> AppConfig:
    return load_config(environ={"CAMPAIGNLAB_DATA_DIR": str(tmp_path)}, home=tmp_path)


def test_repositories_public_surface_is_pure_append() -> None:
    """既有 10 名一个不少、新增恰为 6 名（派单文 §5.7 第 1 条；A82 的符号面镜像）。"""
    actual = set(repositories.__all__)
    assert actual >= REPOSITORIES_PREEXISTING, (
        f"既有公开面缺名：{REPOSITORIES_PREEXISTING - actual}"
    )
    assert actual - REPOSITORIES_PREEXISTING == REPOSITORIES_ADDED, (
        f"多出的名：{actual - REPOSITORIES_PREEXISTING - REPOSITORIES_ADDED}；"
        f"缺的名：{REPOSITORIES_ADDED - actual}"
    )
    for name in actual:
        assert hasattr(repositories, name), f"__all__ 里有取不到的符号：{name}"


def test_new_repositories_expose_exactly_the_enumerated_methods() -> None:
    """三个新 Repository 的方法面逐字等于 design §11.3 第二条的枚举（8 / 4 / 7）。"""
    expected = {
        "ActivityRepository": ACTIVITY_REPOSITORY_METHODS,
        "ActivityBindingRepository": BINDING_REPOSITORY_METHODS,
        "RuleVersionRepository": RULE_REPOSITORY_METHODS,
    }
    for class_name, methods in expected.items():
        cls = getattr(repositories, class_name)
        assert inspect.isclass(cls) and not getattr(cls, "_is_protocol", False), class_name
        actual = _public_methods(cls)
        assert actual == methods, f"{class_name} 多：{actual - methods} 缺：{methods - actual}"


def test_new_records_are_frozen_slots_dataclasses_with_the_design_column_order() -> None:
    """三个 Record 的字段名与**顺序**照 design §2.4（列序错了映射就错位）。"""
    expected = {
        "ActivityRecord": ACTIVITY_RECORD_FIELDS,
        "BindingRecord": BINDING_RECORD_FIELDS,
        "RuleVersionRecord": RULE_VERSION_RECORD_FIELDS,
    }
    for class_name, fields in expected.items():
        cls: object = getattr(repositories, class_name)
        assert dataclasses.is_dataclass(cls), class_name
        frozen, slots = _dataclass_flags(cls)
        assert frozen, f"{class_name} 不是 frozen"
        assert slots, f"{class_name} 不是 slots"
        actual = tuple(field.name for field in dataclasses.fields(cls))
        assert actual == fields, f"{class_name} 列序不符：{actual}"


def test_private_row_mappers_stay_out_of_the_public_surface() -> None:
    """``_activity_of`` / ``_binding_of`` / ``_rule_version_of`` 存在但不进 ``__all__``。"""
    actual_all = set(repositories.__all__)
    for name in ("_activity_of", "_binding_of", "_rule_version_of"):
        assert callable(getattr(repositories, name)), f"缺私有行映射：{name}"
        assert name not in actual_all, f"私有映射漏进 __all__：{name}"


def test_deps_public_surface_is_pure_append() -> None:
    """既有 9 名一个不少、新增恰为 4 名（派单文 §5.7 第 2 条）。"""
    actual = set(deps.__all__)
    assert actual >= DEPS_PREEXISTING, f"既有公开面缺名：{DEPS_PREEXISTING - actual}"
    assert actual - DEPS_PREEXISTING == DEPS_ADDED, (
        f"多出的名：{actual - DEPS_PREEXISTING - DEPS_ADDED}；缺的名：{DEPS_ADDED - actual}"
    )
    for name in actual:
        assert hasattr(deps, name), f"__all__ 里有取不到的符号：{name}"


def test_deps_declares_exactly_one_private_state_helper() -> None:
    """派单文 §6②：``_state_service`` 被复制成第二个私有助手时本条必须红。"""
    assert _module_level_private_functions(DEPS_PY) == {"_state_service"}


@pytest.mark.parametrize(
    ("provider", "attribute", "port"),
    (
        ("get_activity_service", "activity_service", "ActivityService"),
        ("get_rule_service", "rule_service", "RuleService"),
    ),
)
def test_new_providers_reuse_the_shared_state_helper(
    provider: str, attribute: str, port: str
) -> None:
    """两个新提供器都**只**调 ``_state_service``，不自取 ``request.app.state``。"""
    node = _function_def(DEPS_PY, provider)
    calls = [child for child in ast.walk(node) if isinstance(child, ast.Call)]
    shared = [
        call
        for call in calls
        if isinstance(call.func, ast.Name) and call.func.id == "_state_service"
    ]
    assert len(shared) == 1, f"{provider} 没有恰好一次 _state_service 调用：{len(shared)}"
    arguments = shared[0].args
    assert [type(item).__name__ for item in arguments] == ["Name", "Constant", "Name"]
    assert isinstance(arguments[0], ast.Name) and arguments[0].id == "request"
    assert isinstance(arguments[1], ast.Constant) and arguments[1].value == attribute
    assert isinstance(arguments[2], ast.Name) and arguments[2].id == port
    # 取值口径不许在提供器里重写一遍
    for child in ast.walk(node):
        if isinstance(child, ast.Attribute) and child.attr == "state":
            raise AssertionError(f"{provider} 直接摸 app.state，等于复制了 _state_service")
    docstring = ast.get_docstring(node) or ""
    assert "application/activity_service.py" in docstring, f"{provider} 的 docstring 未写明实现处"


def test_protocols_and_implementations_have_identical_public_methods(
    config: AppConfig, engine: Engine
) -> None:
    """派单文 §5.7 第 3 条：Protocol 成员面 ↔ 实现类公开方法面，双向实取对撞。"""
    clock: Clock = FixedClock(T0)
    activity = activity_service.ActivityService(
        engine=engine, clock=clock, config=config, cursor_secret=b"0" * 32
    )
    rule = activity_service.RuleService(
        engine=engine, clock=clock, config=config, cursor_secret=b"0" * 32
    )
    assert isinstance(activity, deps.ActivityService)
    assert isinstance(rule, deps.RuleService)
    assert _protocol_members(deps.ActivityService) == _public_methods(
        activity_service.ActivityService
    )
    assert _protocol_members(deps.RuleService) == _public_methods(activity_service.RuleService)
    # 实现类是普通类：接口只有一份，在 api/deps.py（体例＝test_s3d_application）
    for cls in (activity_service.ActivityService, activity_service.RuleService):
        assert not getattr(cls, "_is_protocol", False), f"{cls.__name__} 是第二份 Protocol"


def test_service_public_surface_is_exactly_the_enumerated_names() -> None:
    """``activity_service.__all__`` ↔ design §11.3 第一条的枚举，双向对撞（禁增减、禁改名）。"""
    actual = set(activity_service.__all__)
    assert actual == SERVICE_PUBLIC_SURFACE, (
        f"多出的名：{actual - SERVICE_PUBLIC_SURFACE}；缺的名：{SERVICE_PUBLIC_SURFACE - actual}"
    )
    for name in actual:
        assert hasattr(activity_service, name), f"__all__ 里有取不到的符号：{name}"


def test_audit_action_and_target_constants_carry_the_design_values() -> None:
    """审计 action / target_kind 的字面值照 design §7.3（它们会落进 ``audit`` 表）。"""
    for name, value in AUDIT_ACTIONS.items():
        assert getattr(activity_service, name) == value, name
    for name, value in AUDIT_TARGET_KINDS.items():
        assert getattr(activity_service, name) == value, name
    assert activity_service.ACTIVITY_ID_PREFIX == "act"
    assert activity_service.RULE_ID_PREFIX == "rul"
    assert activity_service.ACTIVITIES_CURSOR_VERSION == 1
    for name in DETAIL_CONSTANTS:
        detail = getattr(activity_service, name)
        assert isinstance(detail, str) and detail.strip(), f"{name} 不是非空中文短句"


def test_cursor_key_and_bad_cursor_detail_are_reused_not_redeclared() -> None:
    """派单文 §6③：出现第二把密钥或第二句 detail 时本条必须红。"""
    # 经 ``sys.modules`` 取：三个名不在本模块 ``__all__`` 内（strict 开了
    # ``no_implicit_reexport``，直接点属性会被 mypy 判为隐式再导出）。
    loaded = sys.modules["campaignlab.application.activity_service"]
    for name in ("BAD_CURSOR_DETAIL", "load_cursor_secret", "audit_role_of"):
        assert getattr(loaded, name) is getattr(workspace_service, name), f"{name} 不同一份"
    tree = ast.parse(_read(ACTIVITY_SERVICE_PY))
    defined: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            defined.update(target.id for target in node.targets if isinstance(target, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            defined.add(node.target.id)
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            defined.add(node.name)
    # 复用面必须来自 import，不能在本模块另起一份
    for name in ("BAD_CURSOR_DETAIL", "load_cursor_secret", "audit_role_of"):
        assert name not in defined, f"{name} 在本模块被重新定义（第二把密钥／第二句 detail）"
    # 公开 detail 常量只有 design §11.3 那 6 个，不许再冒出第七句
    exported = [str(name) for name in getattr(loaded, "__all__", ())]
    public_details = {name for name in exported if name.endswith("_DETAIL")}
    assert public_details == DETAIL_CONSTANTS, public_details ^ DETAIL_CONSTANTS


def test_secret_lookup_goes_through_the_single_loader() -> None:
    """``_secret()`` 只允许调 ``load_cursor_secret``：第二把密钥无处可藏。"""
    for class_name in ("ActivityService", "RuleService"):
        tree = ast.parse(_read(ACTIVITY_SERVICE_PY))
        target = None
        for cls_node in tree.body:
            if isinstance(cls_node, ast.ClassDef) and cls_node.name == class_name:
                for item in cls_node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == "_secret":
                        target = item
        assert target is not None, f"{class_name} 没有 _secret"
        callees = {
            child.func.id
            for child in ast.walk(target)
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name)
        }
        assert callees <= {"load_cursor_secret"}, f"{class_name}._secret 另调了：{callees}"
        assert "load_cursor_secret" in callees, f"{class_name}._secret 没有复用共享装载器"


def test_activity_service_has_no_sql_write_point() -> None:
    """A81：三张表的 DML 只允许出现在 ``infra/db/repositories.py``。"""
    assert _sql_write_points(_read(ACTIVITY_SERVICE_PY)) == []
    # 反向自证：同一把扫描器在真正的写点上必须报得到（否则本条是空断言）
    assert _sql_write_points(_read(REPOSITORIES_PY)), "扫描器在 repositories.py 上没报到 SQL"


def test_sql_write_point_scanner_catches_a_probe(tmp_path: Path) -> None:
    """派单文 §5.8 的正向对照：在 ``tmp_path`` 造违规探针，断言扫描器抓得到。"""
    probe = tmp_path / "probe.py"
    probe.write_text(
        "from sqlalchemy import text\n"
        "\n"
        "\n"
        "def bad(conn: object) -> object:\n"
        '    """与 SQL 无关的 docstring。"""\n'
        '    return conn.execute(text("UPDATE activities SET revision = 1"))\n',
        encoding="utf-8",
    )
    hits = _sql_write_points(probe.read_text(encoding="utf-8"))
    assert hits, "扫描器抓不到 text() + UPDATE 探针"
    assert any("text() 调用" in hit for hit in hits), hits
    assert any("SQL 字面量" in hit for hit in hits), hits
    clean = tmp_path / "clean.py"
    clean.write_text(
        '"""干净文件：只谈口径，不写 SQL。"""\n'
        "\n"
        "\n"
        "def ok(value: int) -> int:\n"
        "    return value + 1\n",
        encoding="utf-8",
    )
    assert _sql_write_points(clean.read_text(encoding="utf-8")) == []


def test_problem_codes_and_domain_errors_have_no_new_entries() -> None:
    """design §11.2 已冻结错误面：本棒结束后两个集合都必须与 S2a 入库时点一致。"""
    assert set(common.PROBLEM_CODES) == PROBLEM_CODES_FROZEN, (
        f"多出：{set(common.PROBLEM_CODES) - PROBLEM_CODES_FROZEN}；"
        f"缺：{PROBLEM_CODES_FROZEN - set(common.PROBLEM_CODES)}"
    )
    actual = {
        name
        for name, value in vars(domain_errors).items()
        if inspect.isclass(value)
        and issubclass(value, domain_errors.DomainError)
        and value is not domain_errors.DomainError
    }
    assert actual == DOMAIN_ERRORS_FROZEN, (
        f"多出：{actual - DOMAIN_ERRORS_FROZEN}；缺：{DOMAIN_ERRORS_FROZEN - actual}"
    )
