"""并联共振峰的不同幅度曲线，渲染对照供试听挑选。

    python src/experiments/timbre_variants.py
"""

import os
import sys

# 实验脚本在子目录里，而合成模块在上一级（src/）。从项目根目录运行时
# 脚本所在目录会被加进 sys.path，但 src/ 不会，所以这里补一条。
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import dsp
import phonemes as ph
import render

F0 = 261.6256
ITEMS = [("a", "a"), ("i", "i"), ("u", "u"), ("e", "e"), ("o", "o")]

BASE_A = {v: list(ph.VOWELS[v]["A"]) for v in ph.VOWELS}
BASE_BW = render.BANDWIDTH_SCALE

VARIANTS = {
    "V1_基准": dict(A=[1.00, 0.80, 0.55, 0.36, 0.30], bw=1.10),
    "V2_明亮": dict(A=[1.00, 0.90, 0.72, 0.55, 0.48], bw=1.10),
    "V3_通透": dict(A=[1.00, 0.95, 0.85, 0.70, 0.62], bw=1.35),
    "V4_靠前": dict(A=[1.00, 1.00, 0.80, 0.50, 0.42], bw=1.10),
}


def main():
    for label, cfg in VARIANTS.items():
        for v in ph.VOWELS:
            ph.VOWELS[v]["A"] = list(cfg["A"])
        render.BANDWIDTH_SCALE = cfg["bw"]
        outdir = os.path.join("demo", "timbre", label)
        os.makedirs(outdir, exist_ok=True)
        for name, v in ITEMS:
            audio, _ = render.render_vowel(v, F0)
            dsp.write_wav(os.path.join(outdir, f"{name}.wav"), audio)
        ba, _ = render.render_cv("b", "a", F0)
        dsp.write_wav(os.path.join(outdir, "ba.wav"), ba)
        print(f"  demo/timbre/{label}/  A={cfg['A']}  BW×{cfg['bw']}")
    for v in ph.VOWELS:
        ph.VOWELS[v]["A"] = BASE_A[v]
    render.BANDWIDTH_SCALE = BASE_BW


if __name__ == "__main__":
    main()
