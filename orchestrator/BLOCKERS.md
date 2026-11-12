# BLOCKER 预检与登记

| 编号 | 阻塞任务 | 事项 | 需要谁 | 建议命令或动作 |
|---|---|---|---|---|
| BLK-01 | 降级：待 M0-03 验证 | Playwright 浏览器缓存已存在（chromium-1254 与 headless shell），可能无需 sudo | 待验证 | M0-03 用真实 spec 启动一次；失败再走 npx playwright install --with-deps chromium |
| BLK-02 | M0-03、M5-01（措辞已更新） | **降级：安装进行中**。免密 sudo 已落地（`/etc/sudoers.d/90-campaignlab-ops`，限定包管理/服务类命令），`apt-get install -y fonts-noto-cjk` 已在跑（需下载 61.2 MB，实测约 45 KB/s）。现有 7 条中文字体足以出图，但字形度量与行内设计基线不一致，视觉走查结论仍须附此声明 | 无需人工（已授权） | 装完复验 `dpkg -l fonts-noto-cjk` 出现 `ii`、`fc-list :lang=zh \| grep -ci noto > 0`，复跑 `bash scripts/doctor.sh`（WARN 应由 2 降为 1），再置本行为「已关闭」并附实测 |
| BLK-03 | 各阶段 PR | gh 未认证，编排器无法建 PR 与触发 workflow | 项目负责人 | `gh auth login`，或用 compare 链接手工建 PR |
| BLK-04 | M3-01、M3-03 的行内语义 | ADR-003 三项未决（主色与导航、语义色分层、图表补偿） | 项目负责人 | 现按推荐值推进并留痕，收到裁定后回归核对 |
| BLK-05 | 需求追溯 | `CampaignLab-Bank-Strategy-Review-Source-Extract.md` 原件缺失 | 项目负责人 | 提供原件，或批准由 docx/pptx 重建 extract |
| BLK-06 | 已关闭 | duckdb 或 pydantic-core 若无 cp314 wheel | — | M0-01 实测 CPython 3.14.10 全部安装成功，无需回退 |
| BLK-07 | 编排机制（新增） | 宿主机重启会销毁全部子智能体实例；恢复时不得假设实例还在，需按 state.json 重新 spawn，并用 send_input 语义在新实例上续做 | 编排器自检 | 恢复协议第 2 步已加「实例丢失」判定；开工前先读 state.json 的 resume 块 |
| NOTE-01 | M0-03、M5-01（非阻塞） | 宿主占用 TCP 3000/3001/3002（WSL 镜像网络可见）；vite 默认 5173 空闲 | 编排器 | 前端 dev server 固定用 5173 或在 playwright.config 显式指定端口，勿绑 3000 段 |
| NOTE-02 | 全体（新增，操作纪律） | 经 PowerShell→bash 通道写多行文件有两类自伤：heredoc 字面写入使反斜杠翻倍；`sed` 模式串含 `/` 会提前终止定界符 | 编排器与全部子智能体 | 一律用「PowerShell 字面 here-string → base64 → WSL 解码」整文件写入；改配置优先整写或 `python3 -c` 定点替换，禁止含 `/` 的 sed 模式串。详见 LONG-HORIZON-ORCHESTRATION.md 第 13.2 节 |
| NOTE-03 | 编排器自身（新增） | 提交 2fcfb8e 的标题含未转义的 `\uXXXX` 字面量：`git commit -m` 里嵌转义序列时 bash 不解释。因禁止 force-push，不改写历史，仅留痕 | 编排器 | 后续一律 `git commit -F 文件`，文件用 here-string→base64 通道写入（见手册 13.2） |
| NOTE-04 | 编排器自身（新增，最高危） | 手册与 state.json 此前没有「开工闸门」：`resume.next_actions` 直接写「并行派发 wave1」，任何新实例按第 10/13.1 节恢复协议续跑，都会在项目负责人未下指令时擅自派单开发 | 编排器 + 项目负责人 | 已加手册 15.1 与 `state.json.resume.owner_gate=AWAIT_OWNER_GO`；owner_gate 非 GO 时只允许只读自检与治理修复，禁止 spawn 任何开发子智能体 |
| NOTE-05 | 全体（新增，证据纪律） | `.gitignore` 的 `*.log` 曾使 state.json 的 4 条 `gates[].evidence` 指针在仓库内悬空（D-003）：证据写盘 ≠ 证据入库，宿主重置即永久丢失 | 编排器与全部子智能体 | 证据落盘后立即用 `git ls-files --others --exclude-standard <path>` 确认可入库；不可入库的证据视为未留证，必须补 `commands.md` |
| NOTE-06 | 全体（新增，无人值守 sudo 纪律） | 长程无人值守下任何等待密码的 sudo 都会让流水线停摆；但把 root 全权放开又违反最小权限 | 编排器（子智能体一律不得 sudo） | 已落地**限定范围**免密 `/etc/sudoers.d/90-campaignlab-ops`（0440 root:root，`Cmnd_Alias` 仅 apt-get/apt/apt-mark/dpkg/fc-cache/fc-list/systemctl/service/docker/docker-compose/snap 的绝对路径）。新会话实测：`sudo -n apt-get\|dpkg\|fc-cache` rc=0；`sudo -n true\|bash -c true\|tee\|cat` rc=1（无 shell 逃逸、无任意 root 写）。密码只经 PTY stdin 静默传入（`read -rs`），**零落盘**：不进 argv/脚本/日志/证据/提交/state.json。alias 之外的 root 需求：登记 BLOCKER 为「需项目负责人」并继续其他 lane，禁止扩权或绕过。每次接管后须用正/负例各一条复验并把 rc 记入当轮 `commands.md`。详见手册 15.7 |
