"""领域层包入口（M0-02 · S3c 新建目录）。

依赖方向（PYTHON.md：分层保持依赖朝领域内收）::

    api/  ──▶  application/  ──▶  domain/ , infra/

``domain`` 是最内层：**不得** import ``api`` / ``application`` / ``infra``
（``errors.py`` 对 ``api.common.Issue`` 只有 ``TYPE_CHECKING`` 期的类型引用，
运行期不产生导入边）。

- ``errors`` ：Problem code 注册表 + ``DomainError`` 及 13 个子类（ADR-005 §2.1 单一来源）；
- ``ids``    ：资源 ID 正则与请求 ID 生成；
- ``values`` ：``Cents`` / ``RatioStr`` / ``TZ_SHANGHAI``。
"""
