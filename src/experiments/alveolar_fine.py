"""齿龈带通的细微下调，输出到 demo/22_齿龈微调/。

上一轮（demo/20）用户判定 (2000,5000) **超级过度**，只想微调一点点。
这一组固定 d/g 冲击 ×0.5（已认可），只动齿龈带通的上下限。

带通单独通过 6ms 白噪时的谱质心（dsp.bandpass，4 阶巴特沃斯）：

    3400-9000   6442 Hz   现状
    3300-8000   5947 Hz   微调一
    3000-7000   5419 Hz   微调二
    2500-6000   4596 Hz   微调三

作为参照，被否掉的 (2000,5000) 是 3702 Hz —— 这一组最狠的一档也比它高
900Hz，仍属「同一类音色、只是压掉一点毛刺」。

注意：带通是部位属性，所以 ta 也跟着变（d/t 必须共用同一个齿龈谱）。
软腭不动，ga/ka 在这一组里完全不变，可作为参照。
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

OUT = os.path.join("demo", "22_齿龈微调")
F0 = 311.1270
SYLS = ["ba", "pa", "da", "ta", "ga", "ka"]

_ORIG = ph.PLACE_BURST["alveolar"]

VARIANTS = {
    "01_现状":     (3400.0, 9000.0),
    "02_微调一":   (3300.0, 8000.0),
    "03_微调二":   (3000.0, 7000.0),
    "04_微调三":   (2500.0, 6000.0),
}


def apply(band):
    ph.PLACE_BURST["alveolar"] = band
    for k in ("d", "g"):
        ph.CONSONANTS[k]["burst_scale"] = 0.56
        ph.CONSONANTS[k]["thump_scale"] = 0.5
    for k in ("p", "t", "k", "b"):
        ph.CONSONANTS[k]["burst_scale"] = 1.0


def restore():
    ph.PLACE_BURST["alveolar"] = _ORIG
    for k in ph.CONSONANTS:
        ph.CONSONANTS[k].pop("burst_scale", None)
        ph.CONSONANTS[k].pop("thump_scale", None)


def main():
    fresh(OUT)          # 先清空，免得上一轮的变体残留
    for name, band in VARIANTS.items():
        apply(band)
        d = os.path.join(OUT, name)
        os.makedirs(d, exist_ok=True)
        for syl in SYLS:
            audio, _ = render.render_cv(syl[0], syl[1], F0)
            audio = dsp.normalize(audio, dsp.rms(audio),
                                  C.VOICED_RMS_DBFS, C.PEAK_CEILING)
            write(os.path.join(d, f"{syl}.wav"), audio)
        print(f"  {name}: 齿龈 {band}")
    restore()
    print(f"输出目录：{OUT}")


if __name__ == "__main__":
    main()
