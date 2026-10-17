"""解压文件名以 Shift-JIS 存储的 zip（UTAU 日语音源常见）。

Python 的 zipfile 在 zip 条目没有 UTF-8 标志时按 CP437 解码文件名，
于是日文名变成乱码。这里把 CP437 的结果还原成字节再按 CP932 解一次。

    python extract_sjis.py <zip> <目标目录>
"""

import os
import sys
import zipfile


def decode_name(info):
    if info.flag_bits & 0x800:      # 已标记为 UTF-8
        return info.filename
    try:
        return info.filename.encode("cp437").decode("cp932")
    except UnicodeDecodeError:
        return info.filename


def main(zip_path, outdir):
    z = zipfile.ZipFile(zip_path)
    n = 0
    for info in z.infolist():
        name = decode_name(info).replace(os.sep, "/").lstrip("/")
        # 防目录穿越
        name = "/".join(p for p in name.split("/") if p not in ("", ".", ".."))
        if not name:
            continue
        tgt = os.path.join(outdir, *name.split("/"))
        if info.is_dir():
            os.makedirs(tgt, exist_ok=True)
            continue
        os.makedirs(os.path.dirname(tgt), exist_ok=True)
        with z.open(info) as src, open(tgt, "wb") as dst:
            dst.write(src.read())
        n += 1
    print(f"解压 {n} 个文件到 {outdir}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
