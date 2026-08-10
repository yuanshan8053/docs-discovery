#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KOMOJU 文档内部跳转链接坏链检查器(check-komoju-links):离线扫全站快照，判定坏链。

思路借鉴 volc-bp-doc-fetch 的 check-links(extract → 分类 link_type → 对照 manifest
解析 → 给 verdict)，但 manifest、链接命名空间与「坏链」定义全部按 KOMOJU 文档实况重写。

── 语料实况(驱动判定规则)────────────────────────────────────
* 站点 host = doc.komoju.com；本地快照分目录 docs / reference / recipes / changelog。
* 内部跳转有 6 种写法(均指向 doc.komoju.com):
    1. 完整 URL   https://doc.komoju.com/docs/<slug>[#anchor]      (不带 .md)
    2. 根相对     /docs/<slug> 、/reference/<slug> 、/reference(区首页)
    3. 裸相对     getting-started-with-woocommerce  (无 scheme 无前导斜杠，落 docs/)
    4. 版本前缀   https://doc.komoju.com/v2025-01-28/docs/... 、/v1.0/recipes/...
    5. 组件属性   <TutorialTile link="https://doc.komoju.com/v1.0/recipes/<slug>" />
    6. 页内锚点   #secret-token 、...docs/authentication#api-version
* llms.txt 是站点权威机读索引(167 条，全带 .md)→ 与本地文件共同构成 slug manifest。
* files.readme.io = 图片 CDN；help / en / ja / about.komoju + 第三方域名 = 外链。

── 坏链分类(离线可判)────────────────────────────────────────
  MISSING_TARGET      内部 doc/reference/recipe slug 本地与 llms.txt 均无 → 点进去 404。
  BROKEN_ANCHOR       目标页存在，但 #anchor 匹配不到任何标题(ReadMe/GitHub slug 规则)。
  README_PAGE_ORPHAN  /page/<slug> 这类 ReadMe 专有构造，无对应文档。
  LEGACY_SLUG         单段根级遗留 slug(如 /payments-1)映射不到任何页。
  LEGACY_HOST         指向旧域名 komoju-docs.readme.io 而非 doc.komoju.com。
外链只分类、默认不判死；加 --live 才联网探活(观测集，离线不断言坏链)。

── 用法 ────────────────────────────────────────────────────────
    python3 scripts/check_links.py [--docs-dir DIR] [--json] [--live]

    --docs-dir   快照根目录，默认自动探测(仓库同级 / 子级 komoju_docs)
    --json       输出结构化 JSON(含 stats / link_type_counts / findings)
    --live       对外链联网探活(默认关闭)

退出码:0 无坏链;1 发现坏链;2 找不到快照目录 / 用法错。仅用 Python 标准库。
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

HOST = "doc.komoju.com"
LEGACY_HOSTS = {"komoju-docs.readme.io"}
VERSION_RE = re.compile(r"^/v[0-9][0-9a-zA-Z._-]*")   # /v1.0 、/v2025-01-28 、/v2025-01-28_add...


def find_docs_dir(explicit):
    if explicit:
        p = Path(explicit).expanduser().resolve()
        return p if (p / "llms.txt").exists() or p.is_dir() else None
    here = Path(__file__).resolve().parent.parent      # 仓库根
    for cand in (here / "komoju_docs", here.parent / "komoju_docs", Path.cwd() / "komoju_docs"):
        if cand.is_dir() and (cand / "llms.txt").exists():
            return cand
    return None


def build_manifest(root):
    """slug(<dir>/<slug>) -> 相对路径；外加 llms.txt 的 slug 集合。"""
    files = {}
    for md in root.rglob("*.md"):
        parts = md.relative_to(root).with_suffix("").parts
        files["/".join(parts)] = str(md.relative_to(root))
    llms = set()
    lp = root / "llms.txt"
    if lp.exists():
        for m in re.finditer(r"https://doc\.komoju\.com/([^)\s]+)", lp.read_text(encoding="utf-8")):
            slug = re.sub(r"#.*$", "", re.sub(r"\.md$", "", m.group(1)))
            llms.add(slug)
    return files, llms


def slugify(heading):
    h = heading.strip()
    h = re.sub(r"`([^`]*)`", r"\1", h)
    h = re.sub(r"\*\*([^*]*)\*\*", r"\1", h)
    h = re.sub(r"\*([^*]*)\*", r"\1", h)
    h = h.replace("\\_", "_").replace("\\", "").lower()
    h = re.sub(r"[^\w\s-]", "", h)
    return re.sub(r"\s+", "-", h.strip())


def heading_slugs(root, path):
    slugs, counts = set(), {}
    for line in (root / path).read_text(encoding="utf-8").splitlines():
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if not m:
            continue
        base = slugify(m.group(2))
        if not base:
            continue
        n = counts.get(base, 0)
        slugs.add(base if n == 0 else f"{base}-{n}")
        counts[base] = n + 1
    return slugs


def slugify_anchor(a):
    a = re.sub(r"[^\w\s-]", "", a.strip().lower())
    return re.sub(r"\s+", "-", a)


MD_LINK = re.compile(r"(?<!\!)\[[^\]]*\]\(\s*([^)\s]+)")
ATTR_LINK = re.compile(r'\b(?:link|href|url|src)\s*=\s*"([^"]+)"')


def extract(root, path):
    out = []
    for i, line in enumerate((root / path).read_text(encoding="utf-8").splitlines(), 1):
        for rx, kind in ((MD_LINK, "md"), (ATTR_LINK, "attr")):
            for m in rx.finditer(line):
                out.append((i, kind, m.group(1).strip(), line.strip()))
    return out


def classify(href, src_path):
    raw = href
    anchor = None
    if "#" in href:
        href, anchor = href.split("#", 1)
    href = href.strip()

    if raw.startswith("#"):
        return dict(link_type="internal_anchor",
                    slug="/".join(Path(src_path).with_suffix("").parts),
                    anchor=raw[1:], external=False)

    if re.match(r"^https?://", href):
        host = re.match(r"^https?://([^/]+)", href).group(1)
        if host in LEGACY_HOSTS:
            m = re.search(r"/recipes/([^/?#]+)", href)
            return dict(link_type="legacy_host_recipe",
                        slug=("recipes/" + m.group(1)) if m else None,
                        anchor=anchor, external=False, host=host)
        if host == HOST:
            rest = href.split("://", 1)[1]
            path = "/" + rest.split("/", 1)[1] if "/" in rest else "/"
            return _classify_sitepath(path, anchor)
        return dict(link_type="external_url", slug=None, anchor=anchor, external=True, host=host)

    if href.startswith("mailto:") or href.startswith("tel:"):
        return dict(link_type="external_url", slug=None, anchor=anchor, external=True,
                    host=href.split(":")[0])

    if href.startswith("/"):
        return _classify_sitepath(href, anchor)

    # 裸相对：相对源文件目录
    resolved = os.path.normpath(str(Path(src_path).parent / href))
    return dict(link_type="internal_relative", slug=resolved, anchor=anchor, external=False)


def _classify_sitepath(path, anchor):
    versioned = False
    vm = VERSION_RE.match(path)
    if vm:
        versioned = True
        path = path[vm.end():] or "/"
    path = path.rstrip("/")
    if path in ("", "/reference", "/docs"):
        return dict(link_type="site_home", slug=None, anchor=anchor, external=False, versioned=versioned)
    if path.startswith("/page/"):
        return dict(link_type="readme_page", slug=path[1:], anchor=anchor, external=False, versioned=versioned)
    if any(path.startswith(p) for p in ("/docs/", "/reference/", "/recipes/", "/changelog/")):
        return dict(link_type="internal_absolute", slug=re.sub(r"\.md$", "", path[1:]),
                    anchor=anchor, external=False, versioned=versioned)
    return dict(link_type="legacy_root_slug", slug=path[1:], anchor=anchor, external=False, versioned=versioned)


def _count(xs):
    d = {}
    for x in xs:
        d[x] = d.get(x, 0) + 1
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs-dir")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--live", action="store_true")
    args = ap.parse_args()

    root = find_docs_dir(args.docs_dir)
    if not root:
        print("ERROR: 找不到 komoju_docs 快照目录，请用 --docs-dir 指定。", file=sys.stderr)
        sys.exit(2)

    files, llms = build_manifest(root)
    slug_cache = {}

    def get_slugs(slug):
        if slug in files:
            if slug not in slug_cache:
                slug_cache[slug] = heading_slugs(root, files[slug])
            return slug_cache[slug]
        return None

    findings, type_counts = [], {}
    stats = {"files": 0, "links": 0}

    for md in sorted(root.rglob("*.md")):
        rel = str(md.relative_to(root))
        stats["files"] += 1
        for line, kind, href, ctx in extract(root, rel):
            if not href or href.startswith("{") or href.startswith("data:"):
                continue
            stats["links"] += 1
            c = classify(href, rel)
            lt = c["link_type"]
            type_counts[lt] = type_counts.get(lt, 0) + 1

            broken_type, reason = None, None
            if lt in {"internal_absolute", "internal_relative", "legacy_host_recipe"}:
                slug = c.get("slug")
                exists = slug in files or slug in llms
                if not exists:
                    broken_type = "MISSING_TARGET"
                    reason = f"slug '{slug}' 本地无文件且不在 llms.txt 清单中"
                elif lt == "legacy_host_recipe":
                    broken_type = "LEGACY_HOST"
                    reason = f"指向旧域名 {c.get('host')}，应为 {HOST}"
                elif c.get("anchor") and slug in files:
                    sl = get_slugs(slug)
                    if sl is not None and slugify_anchor(c["anchor"]) not in sl:
                        broken_type = "BROKEN_ANCHOR"
                        reason = f"锚点 '#{c['anchor']}' 匹配不到 {slug} 的任何标题"
            elif lt == "internal_anchor":
                sl = get_slugs(c["slug"])
                if sl is not None and slugify_anchor(c["anchor"]) not in sl:
                    broken_type = "BROKEN_ANCHOR"
                    reason = f"页内锚点 '#{c['anchor']}' 匹配不到本篇任何标题"
            elif lt == "readme_page":
                broken_type = "README_PAGE_ORPHAN"
                reason = f"ReadMe /page/ 构造 '{c['slug']}' 无对应文档 / 本地文件"
            elif lt == "legacy_root_slug":
                slug = c.get("slug")
                if not (("docs/" + slug) in files or ("reference/" + slug) in files or slug in llms):
                    broken_type = "LEGACY_SLUG"
                    reason = f"根级遗留 slug '/{slug}' 映射不到任何 doc/reference 页"

            if broken_type:
                findings.append(dict(source_file=rel, line=line, extractor=kind, href=href,
                                     link_type=lt, versioned=c.get("versioned", False),
                                     broken_type=broken_type, reason=reason, context=ctx[:160]))

    result = dict(root=str(root), stats=stats, link_type_counts=type_counts,
                  broken_count=len(findings),
                  broken_by_type=_count([f["broken_type"] for f in findings]),
                  findings=findings)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"扫描 {stats['files']} 篇、{stats['links']} 条链接。")
        print("链接类型:", json.dumps(type_counts, ensure_ascii=False))
        print("坏链:", result["broken_by_type"], f"(共 {len(findings)} 处)")
        for f in findings:
            print(f"\n[{f['broken_type']}] {f['source_file']}:{f['line']}")
            print(f"    href: {f['href']}")
            print(f"    原因: {f['reason']}")

    sys.exit(1 if findings else 0)


if __name__ == "__main__":
    main()
