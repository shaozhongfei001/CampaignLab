# BLOCKER 预检与登记

| 编号 | 阻塞任务 | 事项 | 需要谁 | 建议命令或动作 |
|---|---|---|---|---|
| BLK-01 | M0-03（性质已降级为任务级待验证） | `doctor.sh` 已判 `[ OK ]`：浏览器缓存存在（chromium-1234/1254 与 headless shell）+ `web/node_modules/@playwright/test` 已安装，摘要 `PASS=16 WARN=0 FAIL=0`。但 doctor 只证明「存在」，不证明「能用真实 spec 启动」 | 无需人工 | M0-03 用真实 spec 启动一次 Playwright 并留证据；成功即置已关闭；失败再走 `npx playwright install --with-deps chromium`（免密 sudo 已就绪） |
| BLK-02 | 已关闭（结论不受 D-007 影响；字体确已装，此前 WARN 属工具假阴性，见 D-007）（2026-11-12T22:55:34+08:00） | `fonts-noto-cjk 1:20230817+repack1-3` 安装完成；`fc-list :lang=zh \| grep -ci noto` = 30，`bash scripts/doctor.sh` rc=0；M0-03、M5-01 的视觉走查不再需要「字体度量不一致」声明 | — | 证据：`evidence/monthly/M0-P01/run-04/commands.md` 第 7 节 |
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
| NOTE-07 | 全体（新增，门禁确定性纪律） | `set -o pipefail` 下 `cmd | grep -q` 会因 grep 命中即退出、上游继续写管道而触发 SIGPIPE(141)，被 pipefail 传播成**假红或假绿**；D-007 即此因（doctor.sh:246 假 WARN 率 28/30）。另：`doctor.sh` 对脏树与 `DOCTOR_SKIP_VERIFY=1` 都会 WARN，故 **WARN 计数不可单独作判据** | 编排器与全部子智能体 | ① 禁止在管道里用 `grep -q`/`head`/`sed q` 等会提前退出的命令做判定，改用 `grep -c`、`grep -n` 或先落临时文件；② 判定 G14 必须读 WARN **文本**，区分「脏树 / 跳过 verify」两类预期 WARN 与真实环境问题；③ 已由 `tests/unit/test_doctor_determinism.py` 静态扫描 `scripts/**/*.sh` 守住（含分母断言，扫到 0 个 .sh 即 fail）；④ 新增或修改任何门禁脚本，必须附「连跑 N 次摘要一致」的确定性证据，N≥3 |
