# BLOCKER 预检与登记

| 编号 | 阻塞任务 | 事项 | 需要谁 | 建议命令或动作 |
|---|---|---|---|---|
| BLK-01 | 降级：待 M0-03 验证 | Playwright 浏览器缓存已存在（chromium-1254 与 headless shell），可能无需 sudo | 待验证 | M0-03 用真实 spec 启动一次；失败再走 npx playwright install --with-deps chromium |
| BLK-02 | M0-03、M5-01（措辞已更新） | 缺 Noto Sans CJK。现有 7 条中文字体（WenQuanYi Zen Hei、Unifont）足以出图，但字形度量与行内设计基线不一致，视觉走查结论必须附带此声明 | 项目负责人 | `sudo apt-get install -y fonts-noto-cjk` |
| BLK-03 | 各阶段 PR | gh 未认证，编排器无法建 PR 与触发 workflow | 项目负责人 | `gh auth login`，或用 compare 链接手工建 PR |
| BLK-04 | M3-01、M3-03 的行内语义 | ADR-003 三项未决（主色与导航、语义色分层、图表补偿） | 项目负责人 | 现按推荐值推进并留痕，收到裁定后回归核对 |
| BLK-05 | 需求追溯 | `CampaignLab-Bank-Strategy-Review-Source-Extract.md` 原件缺失 | 项目负责人 | 提供原件，或批准由 docx/pptx 重建 extract |
| BLK-06 | 已关闭 | duckdb 或 pydantic-core 若无 cp314 wheel | — | M0-01 实测 CPython 3.14.10 全部安装成功，无需回退 |
| BLK-07 | 编排机制（新增） | 宿主机重启会销毁全部子智能体实例；恢复时不得假设实例还在，需按 state.json 重新 spawn，并用 send_input 语义在新实例上续做 | 编排器自检 | 恢复协议第 2 步已加「实例丢失」判定；开工前先读 state.json 的 resume 块 |
| NOTE-01 | M0-03、M5-01（非阻塞） | 宿主占用 TCP 3000/3001/3002（WSL 镜像网络可见）；vite 默认 5173 空闲 | 编排器 | 前端 dev server 固定用 5173 或在 playwright.config 显式指定端口，勿绑 3000 段 |
| NOTE-02 | 全体（新增，操作纪律） | 经 PowerShell→bash 通道写多行文件有两类自伤：heredoc 字面写入使反斜杠翻倍；`sed` 模式串含 `/` 会提前终止定界符 | 编排器与全部子智能体 | 一律用「PowerShell 字面 here-string → base64 → WSL 解码」整文件写入；改配置优先整写或 `python3 -c` 定点替换，禁止含 `/` 的 sed 模式串。详见 LONG-HORIZON-ORCHESTRATION.md 第 13.2 节 |
| NOTE-03 | 编排器自身（新增） | 提交 2fcfb8e 的标题含未转义的 `\uXXXX` 字面量：`git commit -m` 里嵌转义序列时 bash 不解释。因禁止 force-push，不改写历史，仅留痕 | 编排器 | 后续一律 `git commit -F 文件`，文件用 here-string→base64 通道写入（见手册 13.2） |