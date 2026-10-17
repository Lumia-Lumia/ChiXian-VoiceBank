"""渲染并打包英语（Delta 式 CVVC）声库。

    python src/build_english.py                  # 默认 D#4，输出 out/chixian-en/
    python src/build_english.py --pitch D#4 C5
    python src/build_english.py --only vowels cv

产出结构与中文那份相同（经典 UTAU 多音阶布局）：

    out/chixian-en/
        character.txt
        D#4/
            ih.wav  ay.wav  p_ae.wav  ae_p.wav  ...
            oto.ini

文件名是 `SAFE` 里的大小写安全记号（Windows 文件名不区分大小写，X-SAMPA
别名区分），**别名本身仍是 X-SAMPA**。

别名形态（Delta 式，见 english.py 的说明）：

    i.wav     -> `i`
    p_a.wav   -> `p a` 和 `- p a`     词中 / 词首
    a_p.wav   -> `a p` 和 `a p-`      词中收尾 / 词尾

`- CV` 与 `V C-` **不是独立采样**，只是同一份 wav 的第二个别名 —— Delta 的
第 6、7 号表就是这么做的（两者差别在 oto 参数而不在波形里）。
"""

import argparse
import sys
import time
from pathlib import Path

import dsp
import english as en
import oto
import render

# 与 build.py 保持一致
PITCHES = {
    "C3": 130.8128,
    "D3": 146.8324,
    "C4": 261.6256,
    "D#4": 311.1270,
    "D4": 293.6648,
    "E4": 329.6276,
    "F4": 349.2282,
    "G4": 391.9954,
    "A4": 440.0000,
    "C5": 523.2511,
}


# 文件名用的安全记号。
#
# **X-SAMPA 别名区分大小写，Windows 文件名不区分** —— 直接用别名当文件名，
# `S.wav` 与 `s.wav`、`T.wav` 与 `t.wav`、`I.wav` 与 `i.wav`、`U.wav` 与 `u.wav`
# 会互相覆盖（实测 784 个采样只剩 545 个，且 oto 里存在指向错误音频的条目）。
# 所以文件名统一转成小写且互不相同的记号；**别名本身仍用 X-SAMPA**。
SAFE = {
    # 元音
    "i": "i", "I": "ih", "E": "eh", "{": "ae", "A": "aa", "O": "ao",
    "V": "uh", "U": "oo", "u": "uw", "3": "er", "@": "ax",
    # 双元音
    "aI": "ay", "eI": "ey", "aU": "aw", "OI": "oy", "oU": "ow",
    # 辅音
    "p": "p", "b": "b", "t": "t", "d": "d", "k": "k", "g": "g",
    "f": "f", "v": "v", "T": "th", "D": "dh", "s": "s", "z": "z",
    "S": "sh", "Z": "zh", "h": "h", "tS": "ch", "dZ": "jh",
    "m": "m", "n": "n", "N": "ng", "l": "l", "r": "r", "w": "w", "j": "y",
}


def build_pitch(pitch, root, only):
    f0 = PITCHES[pitch]
    outdir = root / pitch
    outdir.mkdir(parents=True, exist_ok=True)
    stale = sorted(outdir.glob("*.wav"))
    for f in stale:
        f.unlink()
    if stale:
        print(f"  {pitch}: 清掉 {len(stale)} 个上一轮的采样")
    lines = []

    def emit(filename, alias, kind, meta):
        lines.append(oto.format_line(filename, alias, oto.params_for(kind, meta)))

    if "vowels" in only:
        for v in en.VOWELS:
            audio, meta = render.render_vowel(v, f0, lang=en)
            fname = f"{SAFE[v]}.wav"
            dsp.write_wav(outdir / fname, audio)
            emit(fname, v, "vowel", meta)

    if "cv" in only:
        for c in en.CONSONANTS:
            for v in en.VOWELS:
                # 文件名不带空格（UTAU 会走命令行调用 resampler），别名才用空格
                fname = f"{SAFE[c]}_{SAFE[v]}.wav"
                audio, meta = render.render_cv(c, v, f0, lang=en)
                dsp.write_wav(outdir / fname, audio)
                emit(fname, f"{c} {v}", "cv", meta)
                emit(fname, f"- {c} {v}", "cv", meta)   # 词首

    if "vc" in only:
        for v in en.VOWELS:
            for c in en.CONSONANTS:
                fname = f"{SAFE[v]}_{SAFE[c]}.wav"
                audio, meta = render.render_vc(v, c, f0, lang=en)
                dsp.write_wav(outdir / fname, audio)
                emit(fname, f"{v} {c}", "vc", meta)
                emit(fname, f"{v} {c}-", "vc", meta)    # 词尾

    oto.write_oto(outdir / "oto.ini", lines)
    return lines


def main(argv=None):
    ap = argparse.ArgumentParser(description="渲染并打包英语 UTAU 声库")
    ap.add_argument("--pitch", nargs="+", default=["D#4"], choices=sorted(PITCHES))
    ap.add_argument("--out", default="out")
    ap.add_argument("--name", default="chixian-en")
    ap.add_argument("--only", nargs="+", default=["vowels", "cv", "vc"],
                    choices=["vowels", "cv", "vc"])
    args = ap.parse_args(argv)

    root = Path(args.out) / args.name
    root.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    for pitch in args.pitch:
        lines = build_pitch(pitch, root, set(args.only))
        n_wav = len(list((root / pitch).glob("*.wav")))
        print(f"  {pitch}: {n_wav} 个采样，{len(lines)} 行 oto")

    old_root_oto = root / "oto.ini"
    if old_root_oto.exists():
        old_root_oto.unlink()

    (root / "character.txt").write_text(
        f"name={args.name}\nimage=\nauthor=\n", encoding="cp932")

    dt = time.time() - t0
    total = len(list(root.rglob("*.wav")))
    print(f"\n共 {total} 个采样，用时 {dt:.1f}s")
    print(f"输出：{root.resolve()}")
    print("\n注意：oto.ini 是按段落边界算出的初版，仍需在 SetParam 里按听感微调。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
