#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""中文书写规范门(zh-punct-lint):校验中文正文里是否残留英文半角标点。

「门禁」思路:逐行扫描 → 命中即 file:line 定位 → 退出码 0 干净 / 1 有残留 / 2 用法错,
可直接接进交付前自检 Loop 当机器收敛判据。

── 判定 ────────────────────────────────────────────────────────
中文正文中,标点应使用全角(,。;:!?、「」()等)。本门筛出「中文语境里的半角标点残留」:
半角标点集合 `, . ; : ! ? ( )` 中的字符,只要**紧邻一个 CJK 汉字**(前一个字符或后一个字符是汉字),
即判为残留(应改全角)。「紧邻汉字」这一约束把代码/英文/数字里的合法半角摘干净,只留下真正的中文语境误用。

豁免(不视为残留,先剔除再判定):
  - 围栏代码块 ``` ... ``` 内整段跳过(字段名/枚举/JSON 里的半角是合法的)。
  - 行内代码 `...` 内容剔除(字段名、枚举字面量、`3.0.2` 等)。
  - Markdown 链接的 URL 段 `](...)` 与裸 URL `http(s)://...` 剔除(URL 半角合法)。
  - 数字/英文之间的半角(如 `1,000`、`403/404`、`errors.md`、`10:30`)——因两侧非汉字,天然不命中。

用法:python3 zh_punct_lint.py <file.md> [<file.md> ...]
退出码:0 干净;1 有残留;2 用法错。
"""
import re
import sys

# 需要在中文语境里改成全角的半角标点
HALF = set(",.;:!?()")
# CJK 统一表意文字(含扩展 A)判定
CJK = re.compile(r"[一-鿿㐀-䶿]")

INLINE_CODE = re.compile(r"`[^`]*`")
MD_LINK_URL = re.compile(r"\]\([^)]*\)")   # 链接 URL 段,保留链接文字
BARE_URL = re.compile(r"https?://\S+")


def is_cjk(ch):
    return bool(ch) and bool(CJK.match(ch))


def strip_noncjk_context(line):
    """剔除行内代码、Markdown 链接 URL 段、裸 URL,用空格占位保持相邻关系。"""
    line = INLINE_CODE.sub(lambda m: " " * len(m.group(0)), line)
    line = MD_LINK_URL.sub(lambda m: "]" + " " * (len(m.group(0)) - 1), line)
    line = BARE_URL.sub(lambda m: " " * len(m.group(0)), line)
    return line


def scan_file(path):
    hits = []
    with open(path, encoding="utf-8", errors="ignore") as f:
        in_fence = False
        for lineno, raw in enumerate(f, 1):
            stripped = raw.lstrip()
            # 围栏代码块整段跳过
            if stripped.startswith("```") or stripped.startswith("~~~"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            line = strip_noncjk_context(raw.rstrip("\n"))
            for i, ch in enumerate(line):
                if ch not in HALF:
                    continue
                prev_ch = line[i - 1] if i > 0 else ""
                next_ch = line[i + 1] if i + 1 < len(line) else ""
                if is_cjk(prev_ch) or is_cjk(next_ch):
                    ctx_l = line[max(0, i - 12):i]
                    ctx_r = line[i + 1:i + 13]
                    hits.append((lineno, i + 1, ch, ctx_l, ctx_r))
    return hits


def main(argv):
    if len(argv) < 2:
        print("用法: python3 zh_punct_lint.py <file.md> [<file.md> ...]", file=sys.stderr)
        return 2
    total = 0
    for path in argv[1:]:
        try:
            hits = scan_file(path)
        except OSError as e:
            print(f"[跳过] {path}: {e}", file=sys.stderr)
            continue
        if hits:
            for lineno, col, ch, cl, cr in hits:
                print(f"{path}:{lineno}:{col}  半角『{ch}』紧邻汉字  ->  …{cl}{ch}{cr}…")
            total += len(hits)
        else:
            print(f"[OK] {path} 无英文半角标点残留")
    if total:
        print(f"\n[FAIL] 共 {total} 处英文半角标点残留")
        return 1
    print("\n[PASS] 全部交付物无英文半角标点残留")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
