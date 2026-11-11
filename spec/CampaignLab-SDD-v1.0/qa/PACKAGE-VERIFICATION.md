# 交接包核验记录

核验日期 2026-11-12。核验范围为设计交接包和合成数据。应用开发、自测和独立 QA 的证据由实施阶段归档。

| 项目 | 已复核结果 | 重跑 |
|---|---|---|
| 包结构与引用 | 26 页、80 个接口操作、35 项验收、55 个材料点位、47 个手册操作点。页面和文档链接及文件摘要校对通过 | `python3 qa/verify_package.py` |
| 初始存储 | SQLite 参考 DDL 28 表成功执行。PRAGMA integrity_check 和 foreign_key_check 通过。跨工作区外键负例拒绝 | `python3 qa/verify_package.py` |
| 分析样例 | 甲乙各 510 切片，乙 4590 长表项。元分转换、六行 CSV/JSON、五层、两个分母、贡献、估算和补数核对通过 | `python3 qa/verify_package.py` |
| 仿真样例 | 15 个案例逐个核对两版结果，5 种预发状态验证通过 | `python3 qa/verify_package.py` |
| 类型验证 | 123 个组件 Schema、5 个独立 Schema、22 个 API 请求、60 条问法计划和规则数据通过 JSON Schema 校验 | `python3 qa/verify_schemas.py`，依赖 jsonschema |
| 原型证据 | 原型 v0.1 的 79 项程序核验复跑通过，历史结果见相邻参考文件 | [原型记录](../reference/prototype-results-v0.1.json) |

交接包核验使用 CPython 3.12.14 和 SQLite 3.53.1。本机应用目标 CPython 3.14 的安装、锁文件、浏览器和端到端验收见 [M0–M5](../framework/DELIVERY.md)。
