# FU-32 —— G5c 端口守卫腐化修正（A163；lane U / Hertz）

## 结论
方案 **(A)**：改写 `web/vite.config.ts` 中唯一命中守卫模式的注释，使其不再含
`3000`/`3001`/`3002` 字面量，保留信息量与 NOTE-01 指向。守卫实测回到 `rc=1`，
并用临时探针做过**必命中的正向对照**（`rc=0`），探针已删除、`git status --porcelain web/` 无残留。

## 改动前后原文（逐字；本卡显式授权的**一行注释改写**）
- 前（HEAD，`web/vite.config.ts:32`）：
  `// 宿主 3000/3001/3002 实测 BUSY（NOTE-01）。该端口是**项目级默认约定**而非契约项，`
- 后：
  `// 宿主侧 host 端口段见 NOTE-01 实测记录（三个被占端口一律避开）。该端口是**项目级默认约定**而非契约项，`

`git diff --numstat HEAD -- web/vite.config.ts` = `1  1  web/vite.config.ts`（deleted=1，符合预期）。
文件其余 68 行一字未改；字节数 3441 → 3479。

## 语义与判据
- 该注释与同文件第 4/7 行的既有口径一致（第 7 行原文即「本文件刻意不出现那三个被占端口的数字字面量，
  以免 grep -rn 端口自证命令误命中」），第 32 行是**后来注入的例外**，属守卫腐化而非产品缺陷。
- 改写后不再出现任何 `30xx` 具体端口字面量；`8000`/`8080`/`5173` 等非守卫模式端口原样保留。
- rc 语义按 `grep` 约定：`0`=有匹配（腐化）、`1`=无匹配（守卫期望）、`2`=命令自身错误（判红）。
  本轮实测无 rc=2 出现。
- 一律 `-E`（ERE，R10-5）。

## 正向对照（防「恒 rc=1」假绿）
临时探针 `web/vite.config.probe.tmp`（内容含 `3001`）→ 同形守卫命令 `rc=0` 且命中该文件；
随后 `unlink()` 删除 → 守卫复测 `rc=1`；`git status --porcelain web/` 仅 `M web/vite.config.ts`，
探针不留痕。四元组见 `commands.md`。

## write_set 自查
件二只写：`web/vite.config.ts` + 本目录两份证据（`00-index.md`、`commands.md`）。
`web/playwright.config.ts`、`web/package.json`、`web/tsconfig*.json`、`web/src/**`、`web/tests/**`
均未触碰；探针文件已删除且不入证据清单外的路径。
