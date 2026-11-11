# 本机 Codex 启动任务

从本目录接手 CampaignLab 实施，目标为首版六个功能域与两条已确认的业务流程。请以 [AGENTS.md](AGENTS.md)、[规格索引](SPEC_INDEX.md)、[选型决定](decisions/ADR-001-approved-scope.md)、[交付计划](framework/DELIVERY.md) 为入口。任务按 [实施清单](framework/IMPLEMENTATION-TASKS.md) 拆分。先执行 `python3 qa/verify_package.py`，记录输出并检查工作区现状。

创建或使用隔离的 Git 工作区。按 M0 至 M5 实施。每个阶段从指定业务与技术契约取输入，先用验收用例验证契约边界，再实现最小可运行切片。对既有数据、权限、重启和失败重试一并实测。每次只提交当前任务相关变更。完成一个阶段后继续下一个已授权阶段，直到两条业务流程、离线备份与恢复、文档和独立 QA 交接闭合。

先建立本机可复现的运行环境和依赖锁，再按 [API](architecture/API.md)、[持久层](architecture/DOMAIN.md)、[逐页设计](ui/INDEX.md) 实现。首轮用 [甲乙模拟银行](fixtures/README.md) 与 [规则验收样例](fixtures/README.md) 对齐。展示的数据出处、规则版本、结果和报告随同一业务范围流转。缺少真实银行定义时，用合成语义验证规定的待补分支，并在待补事项中保留实际依赖。

阶段回执列出任务号、提交、命令和结果、证据路径、是否可移交、待办与责任。最后交付实际可运行代码、锁文件、启动及恢复说明、E2E 证据与独立 QA 记录。当前包的设计、原型结果、实际开发结果使用各自状态。
