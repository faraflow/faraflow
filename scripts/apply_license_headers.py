#!/usr/bin/env python3
# Copyright 2026 Alokin LLC
# SPDX-License-Identifier: FCL-1.0-ALv2
"""Adds license headers to the files Alokin LLC added or changed since the PySpur fork point.

Files added since the base get an FCL header. Upstream files that were changed get an
Apache-2.0 attribution plus a "Modified by" line. Pure renames, unchanged files, files that
cannot carry comments and files identical to upstream are left alone. Dry run by default.

    scripts/apply_license_headers.py            # dry run, writes localdocs/license-report.md
    scripts/apply_license_headers.py --apply    # writes the headers
"""

import argparse
import subprocess
import sys
from pathlib import Path

BASE = "75c124cf"
YEAR = "2026"
OWNER = "Alokin LLC"
UPSTREAM_URL = "https://github.com/PySpur-Dev/pyspur"

NEW_LINES = [
    f"Copyright {YEAR} {OWNER}",
    "SPDX-License-Identifier: FCL-1.0-ALv2",
]
MODIFIED_LINES = [
    f"Originally from PySpur ({UPSTREAM_URL}), licensed under Apache-2.0.",
    f"Modified by {OWNER}, {YEAR}; modifications licensed under FCL-1.0-ALv2.",
    "SPDX-License-Identifier: Apache-2.0 AND FCL-1.0-ALv2",
]

# Files generated from a third-party template: they get the FCL header plus a provenance note.
SHADCN_PREFIXES = ("frontend/src/lib/components/ui/", "frontend/src/lib/utils.ts")
SHADCN_LINES = [
    f"Copyright {YEAR} {OWNER}",
    "Generated from shadcn-svelte (https://www.shadcn-svelte.com), MIT License. The MIT notice is in NOTICE.",
    "SPDX-License-Identifier: FCL-1.0-ALv2",
]

HASH_EXTS = {".py", ".sh", ".yml", ".yaml", ".toml", ".conf"}
HASH_NAMES = {"Dockerfile", ".gitignore", ".env.example", ".dockerignore", "robots.txt"}
SLASH_EXTS = {".ts", ".js", ".mjs", ".cjs"}
BLOCK_EXTS = {".css"}
HTML_EXTS = {".svelte", ".md", ".html"}
# Formats that cannot carry a comment header safely; covered by NOTICE instead.
NO_COMMENT_EXTS = {".json", ".lock", ".mdc", ".png", ".jpg", ".ico", ".svg", ".cfg", ".ini"}
# LICENSE and NOTICE are the license texts themselves and carry no header.
NO_HEADER_NAMES = {"LICENSE", "LICENSE.md", "LICENSE-APACHE", "NOTICE"}


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def comment_style(path: Path) -> str | None:
    name, ext = path.name, path.suffix
    if name in NO_HEADER_NAMES or ext in NO_COMMENT_EXTS:
        return None
    if ext in HASH_EXTS or name in HASH_NAMES or name.startswith("Dockerfile"):
        return "hash"
    if ext in SLASH_EXTS:
        return "slash"
    if ext in BLOCK_EXTS:
        return "block"
    if ext in HTML_EXTS:
        return "html"
    return None


def render(lines: list[str], style: str) -> str:
    if style == "hash":
        return "".join(f"# {line}\n" for line in lines)
    if style == "slash":
        return "".join(f"// {line}\n" for line in lines)
    if style == "block":
        return "/*\n" + "".join(f" * {line}\n" for line in lines) + " */\n"
    return "<!--\n" + "".join(f"  {line}\n" for line in lines) + "-->\n"


def worktree_blob(path: str) -> str | None:
    result = subprocess.run(["git", "hash-object", path], capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


def blob(ref: str, path: str) -> str | None:
    result = subprocess.run(["git", "rev-parse", f"{ref}:{path}"], capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


def collect(base: str) -> list[tuple[str, str, str]]:
    """Returns (category, path, old_path) for every file added or changed since base."""
    entries = []
    for line in git("diff", "-M", "--name-status", base).splitlines():
        parts = line.split("\t")
        status = parts[0]
        if status.startswith("D"):
            continue
        if status.startswith("R"):
            old, new = parts[1], parts[2]
            entries.append(("moved" if status == "R100" else "modified", new, old))
        elif status == "A":
            entries.append(("new", parts[1], ""))
        elif status == "M":
            entries.append(("modified", parts[1], parts[1]))
    tracked = {path for _, path, _ in entries}
    for path in git("ls-files", "--others", "--exclude-standard").splitlines():
        if path not in tracked:
            entries.append(("new", path, ""))
    # An empty file added next to an empty file deleted shows up as a rename of identical
    # content (R100); it is a new file for licensing purposes.
    fixed = []
    for category, path, old in entries:
        if category == "moved" and old:
            size = int(git("cat-file", "-s", f"HEAD:{path}").strip() or 0) if blob("HEAD", path) else -1
            if size == 0:
                category, old = "new", ""
        fixed.append((category, path, old))
    return sorted(fixed, key=lambda e: e[1])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--base", default=BASE, help="fork-point commit (default: %(default)s)")
    parser.add_argument("--upstream", default="upstream/main", help="upstream ref to compare against")
    parser.add_argument("--apply", action="store_true", help="write headers (default is a dry run)")
    parser.add_argument("--report", default="localdocs/license-report.md")
    args = parser.parse_args()

    root = Path(git("rev-parse", "--show-toplevel").strip())
    results: dict[str, list[str]] = {
        "header-new": [], "header-new-shadcn": [], "header-modified": [], "already-has-header": [],
        "skip-moved-only": [], "skip-same-as-upstream": [], "skip-no-comment-format": [],
        "skip-missing-or-binary": [],
    }

    for category, path, _old in collect(args.base):
        file = root / path
        if blob(args.upstream, path) is not None and blob(args.upstream, path) == worktree_blob(path) and category != "new":
            results["skip-same-as-upstream"].append(path)
            continue
        if category == "moved":
            results["skip-moved-only"].append(path)
            continue
        style = comment_style(file)
        if style is None:
            results["skip-no-comment-format"].append(path)
            continue
        try:
            text = file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            results["skip-missing-or-binary"].append(path)
            continue
        if "SPDX-License-Identifier" in "".join(text.splitlines(keepends=True)[:20]):
            results["already-has-header"].append(path)
            continue
        if path.startswith(SHADCN_PREFIXES):
            lines, key = SHADCN_LINES, "header-new-shadcn"
        elif category == "new":
            lines, key = NEW_LINES, "header-new"
        else:
            lines, key = MODIFIED_LINES, "header-modified"
        header = render(lines, style)
        results[key].append(path)
        if args.apply:
            prefix = ""
            if text.startswith("#!"):
                prefix, _, text = text.partition("\n")
                prefix += "\n"
            elif style == "html" and path.endswith(".md") and text.startswith("---\n"):
                end = text.find("\n---\n", 4)
                if end != -1:
                    prefix, text = text[: end + 5], text[end + 5 :]
            elif style == "html" and path.endswith(".html") and text.lstrip().lower().startswith("<!doctype"):
                first, _, text = text.partition("\n")
                prefix = first + "\n"
            file.write_text(prefix + header + text, encoding="utf-8")

    report = root / args.report
    report.parent.mkdir(parents=True, exist_ok=True)
    mode = "applied" if args.apply else "dry run"
    lines = [f"# License header report ({mode})", "", f"Base: `{args.base}`. Upstream ref: `{args.upstream}`.", ""]
    for key, paths in results.items():
        lines += [f"## {key} ({len(paths)})", ""] + [f"- `{p}`" for p in paths] + [""]
    report.write_text("\n".join(lines), encoding="utf-8")

    for key, paths in results.items():
        print(f"{key:28} {len(paths)}")
    print(f"report: {report.relative_to(root)} ({mode})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
