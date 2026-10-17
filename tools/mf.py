"""MediaFire 下载：先从文件页取出直链，再下载。

    python tools/mf.py <输出目录> <mediafire 链接> [...]

MediaFire 的文件页现在是 JS 渲染的，但直链仍写在 HTML 里
（`https://download####.mediafire.com/...`），所以两步走即可。
请求之间要留间隔，连续快速请求会被拒绝。
"""
import os
import re
import sys
import time
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"


def get(url, referer=None, timeout=120):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    if referer:
        req.add_header("Referer", referer)
    return urllib.request.urlopen(req, timeout=timeout).read()


def direct(file_url):
    page = get(file_url, referer="https://www.mediafire.com/", timeout=40).decode("utf-8", "ignore")
    m = re.search(r"https?://download\d+\.mediafire\.com/[^\"&]+", page)
    return m.group(0) if m else None


def name_of(file_url, page_hint=None):
    # 形如 /file/<key>/<文件名>/file —— 末尾那一段固定是 "file"，
    # 真正的文件名在它前面一段。早期版本取了 basename，结果所有下载都叫
    # "file"，后一个直接覆盖前一个。
    parts = [p for p in urllib.parse.urlparse(file_url).path.split("/") if p]
    if len(parts) >= 2 and parts[-1] == "file":
        parts = parts[:-1]
    base = parts[-1] if parts else "download.bin"
    return urllib.parse.unquote(base) or "download.bin"


def main(outdir, urls):
    os.makedirs(outdir, exist_ok=True)
    for u in urls:
        try:
            d = direct(u)
        except Exception as e:
            print(f"FAIL {u}\n  {e}")
            continue
        if not d:
            print(f"FAIL 取不到直链 {u}")
            continue
        name = name_of(u)
        path = os.path.join(outdir, name)
        try:
            data = get(d, referer="https://www.mediafire.com/", timeout=300)
        except Exception as e:
            print(f"FAIL 下载 {name}: {e}")
            continue
        with open(path, "wb") as f:
            f.write(data)
        print(f"OK {len(data):>9} B  {name}")
        time.sleep(4)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
