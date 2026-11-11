# 前端执行约定与已知环境坑

来源：模板 `checklist_交付前自检.md` E 段，叠加本仓库在 WSL2 Ubuntu 24.04 上的实测经验。

| 坑 | 本仓库约定 |
|---|---|
| PowerShell 5 不支持 `&&`；外层 `powershell -Command` 传参会吞掉美元符 | 构建、测试、git 一律在 WSL 内以 bash 执行；跨边界传脚本用 base64 编码后解码执行 |
| PowerShell here-string 多行字符串中的转义引号会原样保留 | 多行内容先写文件再执行；写文档统一用带引号定界符的 heredoc，禁止变量展开 |
| 中文编码 | 一律 UTF-8 无 BOM；Python 加 `-X utf8` 与 `PYTHONIOENCODING=utf-8`；URL 中文用 `encodeURIComponent`；`.gitattributes` 已锁 LF |
| Playwright | 固定 `PLAYWRIGHT_BROWSERS_PATH`；`page.$x` 已移除，改用 locator；同 URL 只改 hash 不会重跑脚本，需 `page.reload()`（本项目用 vue-router history 模式） |
| 截图路径 | 不要用 URL 编码后的中文串当文件系统路径；证据截图统一存 `evidence/<阶段>/<页面>/`，文件名用 ASCII |
| Python 生成 JS | 字符串内不得出现真换行；含百分号的 JS 模板不要用百分号格式化 |
| WSL 跨边界性能与语义 | 代码与依赖必须在 ext4（`~/dev/CampaignLab`）；不要在 `/mnt/d` 下 npm install 或构建；`/mnt/d` 上 chmod 不落盘、可执行位无法提交（实测 git 一律记 100644） |
| 字体 | 视觉走查前先用 `fc-list` 确认已安装 Noto Sans CJK SC，否则截图不能作为视觉结论（部署机需 `sudo apt-get install -y fonts-noto-cjk`） |
| Windows interop PATH | WSL 的 PATH 会穿透 Windows 的 node/npm，`npm -v` 可能命中 Windows 版本；本项目 node 固定在 `~/.local/share/node/bin` 并前置于 PATH，脚本内主动探测 |
| sudo 边界 | Agent 无 sudo 权限；需要 root 的动作（apt 安装系统库、Playwright `--with-deps`、字体包）统一列成一条命令交由项目负责人执行 |
