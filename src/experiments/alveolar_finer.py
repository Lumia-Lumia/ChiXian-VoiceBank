"""齿龈带通在「微调一」附近的细分，输出到 demo/23_齿龈再调/。

上一轮结论：
  * d/g 的低频冲击**分开定**：d 用 ×0.3，g 用 ×0.5（demo/21）
  * 齿龈带通落在「微调一」(3300,8000) 附近（demo/22）

这一组把冲击固定在 d=0.3 / g=0.5，只把齿龈带通在 (3300,8000) 两侧细分。
带通单独通过 6ms 白噪时的谱质心：

    3400-8500   6229 Hz   上移      比微调一高 245Hz（现状是 6442）
    3300-8000   5984 Hz   微调一    ← 上一轮选中的点
    3200-7700   5829 Hz   下移一    低 155Hz
    3100-7400   5667 Hz   下移二    低 317Hz

四个点跨度 562Hz，都在「同一类音色」里。微调二 (3000,7000)=5419 已被上一轮
听过但没选，这一组的下移二 (5667) 还比它高 250Hz。

带通是部位属性，ta 跟着变；软腭不动，ga/ka 作为参照。
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

OUT = os.path.join("demo", "23_齿龈再调")
F0 = 311.1270
SYLS = ["ba", "pa", "da", "ta", "ga", "ka"]

_ORIG = ph.PLACE_BURST["alveolar"]

VARIANTS = {
    "01_上移":   (3400.0, 8500.0),
    "02_微调一": (3300.0, 8000.0),
    "03_下移一": (3200.0, 7700.0),
    "04_下移二": (3100.0, 7400.0),
}

# demo/21 定的冲击：d 与 g 不同
THUMP = {"d": 0.3, "g": 0.5}


def apply(band):
    ph.PLACE_BURST["alveolar"] = band
    for k, t in THUMP.items():
        ph.CONSONANTS[k]["burst_scale"] = 0.56
        ph.CONSONANTS[k]["thump_scale"] = t
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
        print(f"  {name}: 齿龈 {band}  （d 冲击 0.3 / g 冲击 0.5）")
    restore()
    print(f"输出目录：{OUT}")


if __name__ == "__main__":
    main()
