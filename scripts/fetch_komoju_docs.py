#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KOMOJU 全套英文文档抓取器(fetch-komoju-docs):随时把官网最新文档拉到本地。

── 方法(本 session 验证过的可复现路径)────────────────────────────
KOMOJU 文档站在根路径提供一份机读清单 `llms.txt`:
    https://doc.komoju.com/llms.txt
里面逐行列出全站文档,格式形如:
    [标题](https://doc.komoju.com/<section>/<slug>.md): 一句话描述
每个 `.md` 链接直接返回原始 Markdown(HTTP 200,text/markdown),无需渲染 JS、无需登录。
section 有四类:docs / reference / recipes / changelog。

本脚本:抓 llms.txt → 正则解析出所有 `doc.komoju.com/<section>/<slug>.md` 链接
→ 逐个下载原始 Markdown → 按 section 落进对应子目录,重建镜像。

── 用法 ────────────────────────────────────────────────────────
    python3 fetch_komoju_docs.py [-o 输出目录] [-w 并发数] [--dry-run]

    -o / --out-dir   输出根目录,默认 ./komoju_docs
    -w / --workers   并发线程数,默认 8
    --dry-run        只解析清单、列出将要抓取的链接,不落盘
    --base-url       文档站根,默认 https://doc.komoju.com

退出码:0 全部成功;1 有链接抓取失败(失败清单打印到 stderr);2 清单抓取失败/用法错。
仅用 Python 标准库,零三方依赖。
"""
import argparse
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

DEFAULT_BASE = "https://doc.komoju.com"
UA = "Mozilla/5.0 (compatible; komoju-docs-fetcher/1.0)"
# 匹配 llms.txt 里的 .md 链接:https://doc.komoju.com/<section>/<...>.md
LINK_RE = re.compile(r"https?://doc\.komoju\.com/(\S+?\.md)")


def http_get(url, timeout=30):
    """GET 一个 URL,返回解码后的文本(UTF-8)。"""
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_manifest(text):
    """从 llms.txt 正文里抽出全部 .md 相对路径(去重、保序)。

    返回形如 ['docs/xxx.md', 'reference/yyy.md', ...] 的列表。
    """
    seen = set()
    paths = []
    for m in LINK_RE.finditer(text):
        rel = m.group(1)  # 形如 docs/xxx.md
        if rel not in seen:
            seen.add(rel)
            paths.append(rel)
    return paths


def fetch_one(base_url, rel_path, out_dir):
    """下载单个 .md,落到 out_dir/<rel_path>。返回 (rel_path, ok, msg)。"""
    url = f"{base_url}/{rel_path}"
    try:
        text = http_get(url)
    except (HTTPError, URLError, TimeoutError) as e:
        return (rel_path, False, str(e))
    dest = os.path.join(out_dir, rel_path)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        f.write(text)
    return (rel_path, True, f"{len(text)} bytes")


def main(argv):
    ap = argparse.ArgumentParser(
        description="抓取 KOMOJU 全套英文文档(基于 llms.txt 清单)。"
    )
    ap.add_argument("-o", "--out-dir", default="komoju_docs", help="输出根目录,默认 ./komoju_docs")
    ap.add_argument("-w", "--workers", type=int, default=8, help="并发线程数,默认 8")
    ap.add_argument("--dry-run", action="store_true", help="只解析清单、列出链接,不落盘")
    ap.add_argument("--base-url", default=DEFAULT_BASE, help=f"文档站根,默认 {DEFAULT_BASE}")
    args = ap.parse_args(argv[1:])

    base_url = args.base_url.rstrip("/")
    manifest_url = f"{base_url}/llms.txt"

    # 1) 抓清单
    try:
        manifest = http_get(manifest_url)
    except (HTTPError, URLError, TimeoutError) as e:
        print(f"[FAIL] 清单抓取失败 {manifest_url}: {e}", file=sys.stderr)
        return 2

    paths = parse_manifest(manifest)
    if not paths:
        print(f"[FAIL] 清单里没解析到任何 .md 链接:{manifest_url}", file=sys.stderr)
        return 2

    # 分 section 统计
    by_section = {}
    for p in paths:
        sec = p.split("/", 1)[0] if "/" in p else "(root)"
        by_section.setdefault(sec, 0)
        by_section[sec] += 1
    summary = "  ".join(f"{s}:{n}" for s, n in sorted(by_section.items()))
    print(f"[清单] {manifest_url} 共 {len(paths)} 篇  ({summary})")

    if args.dry_run:
        for p in paths:
            print(f"  {base_url}/{p}")
        print(f"\n[DRY-RUN] 未落盘,共 {len(paths)} 个链接")
        return 0

    # 2) 并发下载
    os.makedirs(args.out_dir, exist_ok=True)
    # 顺便把清单本身也存一份,方便离线核对
    with open(os.path.join(args.out_dir, "llms.txt"), "w", encoding="utf-8") as f:
        f.write(manifest)

    ok, failed = 0, []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(fetch_one, base_url, p, args.out_dir): p for p in paths}
        for fut in as_completed(futs):
            rel, good, msg = fut.result()
            if good:
                ok += 1
            else:
                failed.append((rel, msg))
                print(f"  [x] {rel}: {msg}", file=sys.stderr)

    print(f"\n[完成] 成功 {ok}/{len(paths)},输出目录:{args.out_dir}")
    if failed:
        print(f"[FAIL] {len(failed)} 篇抓取失败(见上方 stderr)", file=sys.stderr)
        return 1
    print("[PASS] 全部抓取成功")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
