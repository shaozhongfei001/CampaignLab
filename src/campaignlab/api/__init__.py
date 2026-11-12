"""HTTP 层（api）包入口。

本包只放「协议翻译」：把已验证的输入交给 ``application``，把结果组装成符合活契约的响应。
路由函数只做「解析 → 调 application → 组装响应」，**不得写 SQL**（PYTHON.md）。

- ``common``    ：Problem 错误体、ETag、Idempotency-Key 与游标包装、DTO（M0-03b 冻结面）；
- ``app``       ：``create_app()``（后续轮次交付；必须置 ``openapi_url/docs_url/redoc_url=None``，
  契约真值只在 ``contracts/openapi.json``，不得暴露第二个 OpenAPI 面）；
- ``deps``/``health``/``session``/``workspaces``：后续轮次交付。
"""
