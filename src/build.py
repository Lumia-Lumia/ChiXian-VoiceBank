"""批量渲染 + 打包成传统 UTAU 声库目录。

    python src/build.py                          # 默认 D#4，输出到 out/chixian/
    python src/build.py --pitch C4 C5            # 多个音阶
    python src/build.py --only vowels cv         # 只做一部分，方便快速试听

产出结构（经典 UTAU 多音阶布局，OpenUtau 也能直接读）：

    out/chixian/
        character.txt
        oto.ini          （把各音阶的 oto 汇总，方便整体查看）
        C4/
            a.wav  ba.wav  ...  "a b.wav" ...
            oto.ini
"""

import argparse
import sys
import time
from pathlib import Path

import dsp
import oto
import phonemes as ph
import render

# 音阶 → 基频。用十二平均律，A4 = 440Hz
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

# 普通话里真实存在的音节（声母 + 韵母）。用来标记哪些是有效拼音 ——
# 这个 MVP 会把 11×5 的组合全渲染出来验证机制，但正式中文声库只需要下面这些。
VALID_MANDARIN = {
    "b": {"a", "o", "i", "u", "e"},
    "p": {"a", "o", "i", "u", "e"},
    "m": {"a", "o", "i", "u", "e"},
    "d": {"a", "e", "i", "u"},
    "t": {"a", "e", "i", "u"},
    "n": {"a", "e", "i", "u"},
    "l": {"a", "e", "i", "u"},
    "g": {"a", "e", "u"},
    "k": {"a", "e", "u"},
    "h": {"a", "e", "u"},
    "s": {"a", "e", "i", "u"},
}


def build_pitch(pitch, root, only):
    f0 = PITCHES[pitch]
    outdir = root / pitch
    outdir.mkdir(parents=True, exist_ok=True)
    # 先清掉上一轮的采样。音素表改动后（例如 VC 的 b/d/g 按规范改成 p/t/k），
    # 旧文件名不会被覆盖，会作为孤儿留在目录里，让 wav 数和 oto 行数对不上。
    stale = sorted(outdir.glob("*.wav"))
    for f in stale:
        f.unlink()
    if stale:
        print(f"  {pitch}: 清掉 {len(stale)} 个上一轮的采样")
    lines = []

    def emit(filename, alias, kind, meta):
        lines.append(oto.format_line(filename, alias, oto.params_for(kind, meta)))

    if "vowels" in only:
        for v in ph.VOWELS:
            audio, meta = render.render_vowel(v, f0)
            dsp.write_wav(outdir / f"{v}.wav", audio)
            emit(f"{v}.wav", v, "vowel", meta)

    if "cv" in only:
        for c in ph.CONSONANTS:
            for v in ph.VOWELS:
                alias = f"{c}{v}"
                audio, meta = render.render_cv(c, v, f0)
                dsp.write_wav(outdir / f"{alias}.wav", audio)
                emit(f"{alias}.wav", alias, "cv", meta)

    if "vc" in only:
        # 后继辅音用送气形式（b/d/g → p/t/k），见 phonemes.VC_INITIAL 的说明。
        # 11 个声母在这里只剩 8 类。
        for v in ph.VOWELS:
            for c in ph.vc_initials():
                # 文件名不含空格，别名才用空格：VC 别名按规范是「a p」这种形式，
                # 但 UTAU 调 resampler/wavtool 是走命令行的，带空格的路径有风险。
                # 真实声库也都这么做（重音テト _あ.wav 别名 あ、Hitsuboku _a_a.wav）。
                fname = f"_{v}_{c}.wav"
                alias = f"{v} {c}"
                audio, meta = render.render_vc(v, c, f0)
                dsp.write_wav(outdir / fname, audio)
                emit(fname, alias, "vc", meta)

    oto.write_oto(outdir / "oto.ini", lines)
    return lines


def main(argv=None):
    ap = argparse.ArgumentParser(description="渲染并打包 UTAU 声库")
    ap.add_argument("--pitch", nargs="+", default=["D#4"], choices=sorted(PITCHES),
                    help="要生成的音阶（默认 C4）")
    ap.add_argument("--out", default="out", help="输出根目录")
    ap.add_argument("--name", default="chixian", help="声库名字")
    ap.add_argument("--only", nargs="+", default=["vowels", "cv", "vc"],
                    choices=["vowels", "cv", "vc"], help="只生成指定部分")
    args = ap.parse_args(argv)

    root = Path(args.out) / args.name
    root.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    for pitch in args.pitch:
        lines = build_pitch(pitch, root, set(args.only))
        n_wav = len(list((root / pitch).glob("*.wav")))
        print(f"  {pitch}: {n_wav} 个采样，{len(lines)} 行 oto")

    # 不在根目录放汇总 oto.ini：真实声库（重音テト、Hitsuboku Kumi）都只在各
    # 音阶子文件夹里放一份，根目录再放一份带 `C4\` 前缀的汇总会让 UTAU 读到
    # 两套定义。顺手清掉早期版本留下的那一份。
    old_root_oto = root / "oto.ini"
    if old_root_oto.exists():
        old_root_oto.unlink()
        print("  清掉了根目录里遗留的汇总 oto.ini")

    (root / "character.txt").write_text(
        f"name={args.name}\nimage=\nauthor=\n", encoding="cp932")

    dt = time.time() - t0
    total = len(list(root.rglob("*.wav")))
    print(f"\n共 {total} 个采样，用时 {dt:.1f}s")
    print(f"输出：{root.resolve()}")

    if "cv" in args.only:
        bad = [f"{c}{v}" for c in ph.CONSONANTS for v in ph.VOWELS
               if v not in VALID_MANDARIN[c]]
        print(f"\n提示：这 {len(bad)} 个 CV 组合不是有效普通话音节"
              f"（{', '.join(bad)}）")
        print("本批全部渲染是为了验证机制，正式中文声库只需保留有效音节。")

    print("\n注意：oto.ini 是按合成脚本已知的段落边界算出的初版，")
    print("仍需用 SetParam 按听感微调（纲领 TODO 第 7 步）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
