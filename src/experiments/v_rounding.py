"""ü 的音色（嘴唇圆展），输出到 demo/29_ü的音色/。

demo/28 的用户反馈：**yue 和 ye 差别很小，ü 的音难以辨别**。

原因在共振峰表：现在的
    i = [300, 2350, 3000, ...]
    ü = [300, 2100, 2700, ...]
只差 F2 250Hz、F3 300Hz。而圆唇会把 F2 和 F3 **同时**压低（唇管延长、
腔体整体变长），标准普通话测量里 i≈2250/2900、ü≈1900/2400，差 350/500。

四档只动 VOWELS["v"] 的 F2/F3：

    01_现状  2100 / 2700
    02_略低  1950 / 2550
    03_标准  1850 / 2400
    04_更低  1750 / 2250

渲 ye（ie）与 yue（ve）作对比，另加 yu（v 本身）、yun（vn）、jue、xue。
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

OUT = os.path.join("demo", "29_ü的音色")
F0 = 311.1270

# 韵母 → 文件名
CASES = {
    "ie": "ye", "ve": "yue", "v": "yu", "vn": "yun",
    "ian": "yan",
}
CV_CASES = {
    ("j", "ve"): "jue", ("q", "ve"): "que", ("x", "ve"): "xue",
    ("j", "vn"): "jun", ("x", "vn"): "xun",
}

VARIANTS = {
    "01_现状": (2100.0, 2700.0),
    "02_略低": (1950.0, 2550.0),
    "03_标准": (1850.0, 2400.0),
    "04_更低": (1750.0, 2250.0),
}

_ORIG = list(ph.VOWELS["v"]["F"])


def apply(f2, f3):
    F = list(_ORIG)
    F[1] = f2
    F[2] = f3
    ph.VOWELS["v"]["F"] = F


def restore():
    ph.VOWELS["v"]["F"] = list(_ORIG)


def main():
    fresh(OUT)
    for name, (f2, f3) in VARIANTS.items():
        apply(f2, f3)
        d = os.path.join(OUT, name)
        os.makedirs(d, exist_ok=True)
        for fin, fname in CASES.items():
            audio, _ = render.render_vowel(fin, F0)
            audio = dsp.normalize(audio, dsp.rms(audio),
                                  C.VOICED_RMS_DBFS, C.PEAK_CEILING)
            write(os.path.join(d, f"{fname}.wav"), audio)
        for (c, fin), fname in CV_CASES.items():
            audio, _ = render.render_cv(c, fin, F0)
            audio = dsp.normalize(audio, dsp.rms(audio),
                                  C.VOICED_RMS_DBFS, C.PEAK_CEILING)
            write(os.path.join(d, f"{fname}.wav"), audio)
        print(f"  {name}: ü 的 F2/F3 = {f2:.0f}/{f3:.0f}")
    restore()
    print(f"输出目录：{OUT}")


if __name__ == "__main__":
    main()
