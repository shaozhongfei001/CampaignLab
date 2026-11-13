"""``getHealth`` 路由（M0-02 · S3c；design §1 第 3 条 / §6 ``api/health.py:get_health``）。

契约（切片 ``operations.getHealth``）：``GET /health``（前缀 ``/api/v1``）、``security: []``、
200 返回 ``Health{status,app_version,contract_version,worker,schema_revision}``
（五字段全必填、``additionalProperties: false``），并声明
400/401/403/404/409/412/413/422/428/429/500 的 Problem 形。

路由函数只做「解析 → 调 application → 组装响应」（PYTHON.md）：五字段的**取值逻辑全部**
在 ``HealthService``（S3d）内——``contract_version`` 运行时读活契约、``schema_revision`` 取
``alembic_version`` 当前行、``worker`` 按 design §4 判定、``status="READY"`` 当且仅当
``worker=="READY"`` 且 revision 等于 head。本文件**不复制**任何一条判定。

A7：契约响应码全集**无 304**，故本路由不引入任何条件请求／304 分支。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from campaignlab.api.deps import HealthService, get_health_service
from campaignlab.config import API_PREFIX

__all__ = ["get_health", "router"]

router = APIRouter(prefix=API_PREFIX, tags=["health"])


@router.get("/health", operation_id="getHealth")
async def get_health(
    # design §1 冻结签名逐字保留（``svc: HealthService = Depends(...)``）；ruff B008 与
    # FastAPI 的依赖注入惯用法直接冲突，改 ``Annotated`` 形会改动已冻结签名，故就地豁免。
    svc: HealthService = Depends(get_health_service),  # noqa: B008
) -> Response:
    """``getHealth``：200 + ``Health``（``X-Request-Id`` 由中间件统一加，此处不重复设置）。"""
    snapshot = svc.snapshot()
    return Response(
        content=snapshot.model_dump_json(),
        status_code=200,
        media_type="application/json",
    )
