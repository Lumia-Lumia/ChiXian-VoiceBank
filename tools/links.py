"""从保存下来的网页里挑出可能的下载链接。

    python tools/links.py <html 文件> [...]
"""
import re
import sys

KEYS = re.compile(
    r"mega\.nz|drive\.google|mediafire|dropbox|yadi\.sk|disk\.yandex|"
    r"booml|\.zip|\.rar|\.7z|\.ust",
    re.I,
)


def main(paths):
    for p in paths:
        try:
            h = open(p, encoding="utf-8", errors="ignore").read()
        except OSError as e:
            print(f"!! {p}: {e}")
            continue
        seen = set()
        print(f"== {p}")
        for u in re.findall(r"https?://[^\s\"<>]+", h):
            u = u.rstrip("\\'\")")
            if u in seen:
                continue
            seen.add(u)
            if KEYS.search(u):
                print("  " + u[:150])
        print()


if __name__ == "__main__":
    main(sys.argv[1:])
