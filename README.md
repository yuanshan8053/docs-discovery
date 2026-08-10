# docs-discovery

KOMOJU 全套英文文档的两项成果：AI 友好度质检 + API 文档内容增强建议。

## 目录

### `ai-friendly-check/` — AI 友好度质检

- `问题清单.md` — AI 友好度质检问题清单（通俗版），含 `.md` 原文位置（行号 + 出错片段摘录）与渲染页链接，共 31 条**点状缺陷**（高 22 · 中高 7 · 中 2）。质检维度：字段名拼写、说明与实现一致性、枚举缺失、跨文档口径冲突、代码示例可运行性、术语/命名一致性等。

### `api-content-enhancement/` — API 文档内容增强建议

- `API文档内容增强建议.md` — 站在 API 使用者立场，梳理可进一步补充的内容缺口，共 9 条增强建议（高 4 · 中高 4 · 中 1），具体建议并入表格最右列。覆盖字段说明、枚举含义、示例值、错误码/限流等，与《问题清单》无重复。

### 交付纪律与工具

- `交付纪律.md` — 硬纪律：所有 `.md` 交付物在提交/推送前**必须**通过中文书写规范门。
- `scripts/zh_punct_lint.py` — 中文书写规范门禁（半角标点残留检查，退出码 0/1/2）。
- `scripts/zh_punct_fix.py` — 配套就地修复器，把中文正文里的半角标点转全角。
- `scripts/fetch_komoju_docs.py` — KOMOJU 全套英文文档抓取器，基于官网 `llms.txt` 机读清单随时拉取最新文档，按 `docs/reference/recipes/changelog/` 分目录落盘。用法：`python3 scripts/fetch_komoju_docs.py -o komoju_docs`（`--dry-run` 只列链接不落盘）。本仓库两份分析结论均基于该脚本抓取的快照产出，需复核或更新时可一键重抓。
