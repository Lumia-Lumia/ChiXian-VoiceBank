"""üe 的滑行曲线，输出到 demo/30_yue的ü长度/。

模型已经换过两次：
  * «介音 ü + 韵腹 ɛ» —— ü 太短，yue 像 ye
  * «韵腹 ü + 短韵尾 ɛ» —— 仍然在两端停留
  * **整条韵母就是一次从 ü 到 ɛ 的滑行**（用户指定的最终形态）：起音 10ms，
    之后 780ms（韵腹 680 + 收尾 100）全部用于过渡，两端都不停留

`glide_all=True` 就是这个模式。唯一还能调的是**曲线形状** —— 进度 p = u^curve：

    01_0.55  快起慢收
    02_0.65
    03_0.75
    04_0.85  接近匀速

yuan（üan）没有动，四档完全相同，可作锚点。
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config as C
import dsp
import phonemes as ph
import render
from _demo import fresh, write

OUT = os.path.join("demo", "30_yue的ü长度")
F0 = 311.1270

VARIANTS = {
    "01_0.55": 0.55,
    "02_0.65": 0.65,
    "03_0.75": 0.75,
    "04_0.85": 0.85,
}

CASES = {
    ("", "ve"): "yue", ("j", "ve"): "jue",
    ("q", "ve"): "que", ("x", "ve"): "xue",
    ("", "van"): "yuan",
}


def main():
    fresh(OUT)
    orig = ph.FINALS["ve"].get("curve")
    for name, curve in VARIANTS.items():
        ph.FINALS["ve"]["curve"] = curve
        d = os.path.join(OUT, name)
        os.makedirs(d, exist_ok=True)
        for (c, fin), fname in CASES.items():
            if c:
                audio, _ = render.render_cv(c, fin, F0)
            else:
                audio, _ = render.render_vowel(fin, F0)
            audio = dsp.normalize(audio, dsp.rms(audio),
                                  C.VOICED_RMS_DBFS, C.PEAK_CEILING)
            write(os.path.join(d, f"{fname}.wav"), audio)
        print(f"  {name}: 曲线进度 = u^{curve}")
    ph.FINALS["ve"]["curve"] = orig
    print(f"输出目录：{OUT}")


if __name__ == "__main__":
    main()
