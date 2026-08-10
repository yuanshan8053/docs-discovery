#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""zh_punct_fix:把中文语境里的英文半角标点改成全角。与 zh_punct_lint.py 同源的掩码逻辑
(跳过围栏代码块、行内代码 `...`、Markdown 链接 URL 段、裸 URL),保证只改中文正文、不动代码。

- 逗号/分号/冒号/叹号/问号/句点:掩码后紧邻汉字即转全角(这些无配对问题)。
- 圆括号:按配对处理——一对 (...) 中只要「( 前」「) 后」有汉字、或括号内含汉字,即整对转全角,
  避免出现「半角开、全角闭」的错配。孤立括号退化到「紧邻汉字」规则。

用法:python3 zh_punct_fix.py <file> [<file> ...]   # 原地改写,打印每文件改动数。
"""
import re
import sys

MAP = {",": "，", ".": "。", ";": "；", ":": "：", "!": "！", "?": "？", "(": "（", ")": "）"}
NONPAREN = set(",.;:!?")
CJK = re.compile(r"[一-鿿㐀-䶿]")
INLINE_CODE = re.compile(r"`[^`]*`")
MD_LINK_URL = re.compile(r"\]\([^)]*\)")
BARE_URL = re.compile(r"https?://\S+")


def is_cjk(ch):
    return bool(ch) and bool(CJK.match(ch))


def mask(line):
    """返回与 line 等长的掩码串:被掩码位置为 ' '(不可改),其余保留原字符。"""
    masked = list(line)
    for rgx in (INLINE_CODE, MD_LINK_URL, BARE_URL):
        for m in rgx.finditer(line):
            for i in range(m.start(), m.end()):
                masked[i] = " "
    return "".join(masked)


def fix_line(line):
    masked = mask(line)
    chars = list(line)
    n = len(chars)
    changed = 0

    # 1) 非括号标点:掩码位置可改 + 紧邻汉字
    for i, ch in enumerate(chars):
        if masked[i] == " ":
            continue
        if ch in NONPAREN:
            prev_ch = line[i - 1] if i > 0 else ""
            next_ch = line[i + 1] if i + 1 < n else ""
            if is_cjk(prev_ch) or is_cjk(next_ch):
                chars[i] = MAP[ch]
                changed += 1

    # 2) 圆括号:按配对处理
    line2 = "".join(chars)
    masked2 = mask(line2)
    stack = []
    out = list(line2)
    for i, ch in enumerate(line2):
        if masked2[i] == " ":
            continue
        if ch == "(":
            stack.append(i)
        elif ch == ")" and stack:
            open_i = stack.pop()
            inner = line2[open_i + 1:i]
            before = line2[open_i - 1] if open_i > 0 else ""
            after = line2[i + 1] if i + 1 < len(line2) else ""
            if is_cjk(before) or is_cjk(after) or CJK.search(inner):
                out[open_i] = "（"
                out[i] = "）"
                changed += 2
    # 剩余未配对的孤立括号:退化到紧邻汉字
    line3 = "".join(out)
    masked3 = mask(line3)
    out3 = list(line3)
    for i, ch in enumerate(line3):
        if masked3[i] == " ":
            continue
        if ch in "()":
            prev_ch = line3[i - 1] if i > 0 else ""
            next_ch = line3[i + 1] if i + 1 < len(line3) else ""
            if is_cjk(prev_ch) or is_cjk(next_ch):
                out3[i] = MAP[ch]
                changed += 1
    return "".join(out3), changed


def fix_file(path):
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    total = 0
    in_fence = False
    new_lines = []
    for raw in lines:
        stripped = raw.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            new_lines.append(raw)
            continue
        if in_fence:
            new_lines.append(raw)
            continue
        body = raw.rstrip("\n")
        nl = "\n" if raw.endswith("\n") else ""
        fixed, changed = fix_line(body)
        new_lines.append(fixed + nl)
        total += changed
    if total:
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
    print(f"{path}: 转换 {total} 处半角->全角")
    return total


def main(argv):
    if len(argv) < 2:
        print("用法: python3 zh_punct_fix.py <file> [<file> ...]", file=sys.stderr)
        return 2
    for path in argv[1:]:
        fix_file(path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
