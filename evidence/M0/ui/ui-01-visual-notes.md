# UI-01 视觉取证说明（M0-03 / S9）

字体声明（doctor 第 8 节要求，先声明再下视觉结论）：容器内 `fc-list :lang=zh` 实测 37 个中文字面，
其中 **Noto Sans CJK SC** 2 个（Regular/Bold）。body 计算字体串为
`Inter, "Noto Sans CJK SC", "Microsoft YaHei", system-ui, sans-serif`（Inter 未安装，中文落到 Noto Sans CJK SC）。
因此下述尺寸结论可信，但**拉丁字形与本机 Inter 设计稿存在差异**，不作像素级比对结论。

| 视口 | 截图 | 左导航宽 | 顶栏高 | 焦点轮廓 |
|---|---|---|---|---|
| 1440x900（desktop-1440x900） | `evidence/M0/M0-03/ui-01-desktop-1440x900.png` | 216px | 56px | 2px |
| 1024x768（laptop-1024x768） | `evidence/M0/M0-03/ui-01-laptop-1024x768.png` | 64px（<=1100 折叠档） | 56px | 2px |

两处 `<=1100px` / `<=800px` 折叠由 `--cl-bp-rail-collapse` / `--cl-bp-rail-drawer` 注记驱动，
与 token-mapping §3 档位一致（断点守卫实测 `违规条数 = 0`）。

数据面为合成夹具（`web/tests/e2e/fixtures/stubApi.ts`，两条工作区：合成 / 授权脱敏），
非服务端返回，故本图只作**布局与层级**证据，不作数据正确性证据。
