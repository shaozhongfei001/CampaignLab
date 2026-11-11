# CampaignLab

营销活动策略复盘（智能复盘）项目。当前阶段以前端原型作为需求与验收基准，逐步转入规格驱动（SDD）开发。

## 目录结构

- `prototype/campaignlab-review-work/` — 原型源码：`shell.html` `style.css` `core.js` `ui.js` `generate_data.py` `build.py` `verify.mjs`（零第三方依赖）
- `prototype/campaignlab-review-deliverables/` — 交付产物：单文件原型 HTML、模拟数据 Bank A/B、复现规格与验收清单
- `docs/source-materials/` — 业务原始材料（`智能复盘.docx`、`策略复盘规划-1022.pptx`）
- `docs/` — 规格驱动开发产物：spec / plan / tasks / ADR

## 环境与运行

开发与测试环境统一为 **WSL2 Ubuntu 24.04**（与部署目标一致），代码放在 ext4 文件系统（`~/dev/CampaignLab`），不要在 `/mnt/d` 上构建。

```bash
# 校验交付包完整性
cd prototype && sha256sum -c SHA256SUMS

# 运行验收断言（Node 22）
cd prototype/campaignlab-review-work && node verify.mjs

# 重建原型（Python 3.12，仅标准库）
python3 build.py
```

## 约定

- 换行符 LF、UTF-8 无 BOM（见 `.gitattributes`）；`core.autocrlf=input`
- 构建产物与 handoff zip 不入库，由 `build.py` / `package.py` 重新生成

## 规格基线与设计裁定

- `spec/CampaignLab-SDD-v1.0/` — SDD 交接包 v1.0.0，按字节原样入库（`.gitattributes` 对 `spec/**` 禁用 EOL 转换）。校验：`cd spec/CampaignLab-SDD-v1.0 && python3 qa/verify_package.py`
- `spec/frontend-template-spdb-v1.1/` — 浦发风格前端设计模板 V1.1，同样按字节入库，仅作视觉真值参照，不参与构建
- `docs/decisions/ADR-003-frontend-design-baseline.md` — 前端设计基线裁定（采纳模板视觉语言，不采纳其运行时）
- `docs/design/token-mapping.md` — 令牌 → Element Plus → ECharts 三处一致映射
- `docs/design/page-component-map.md` — 26 页 ↔ 组件族映射与自研清单
- `docs/design/frontend-pitfalls.md` — WSL/Playwright/编码等执行约定
