# BLOCKER 预检与登记

| 编号 | 阻塞任务 | 事项 | 需要谁 | 建议命令或动作 |
|---|---|---|---|---|
| BLK-01 | M5-01、M5-02 | Playwright 浏览器系统依赖需 root | 项目负责人 | `cd web && npx playwright install --with-deps chromium` |
| BLK-02 | M0-03、M5-01 | 中文字体需 root，否则视觉走查结论不可用 | 项目负责人 | `sudo apt-get install -y fonts-noto-cjk` |
| BLK-03 | 各阶段 PR | gh 未认证，编排器无法建 PR 与触发 workflow | 项目负责人 | `gh auth login`，或用 compare 链接手工建 PR |
| BLK-04 | M3-01、M3-03 的行内语义 | ADR-003 三项未决（主色与导航、语义色分层、图表补偿） | 项目负责人 | 现按推荐值推进并留痕，收到裁定后回归核对 |
| BLK-05 | 需求追溯 | `CampaignLab-Bank-Strategy-Review-Source-Extract.md` 原件缺失 | 项目负责人 | 提供原件，或批准由 docx/pptx 重建 extract |
| BLK-06 | M0-01 | duckdb 或 pydantic-core 若无 cp314 wheel | 编排器自决 | 记 CR/ADR，按 ADR-002 的安装版本回退路径处理 |
