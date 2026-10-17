"""d/g 起爆的谱与低频冲击 2×2，输出到 demo/20_dg起爆谱/。

用户反馈：d/g 压到 −5dB 依然显得响，怀疑是高频太多。

测量把两个问题分开了（1/3 倍频带，相对该起爆自身总能量）：

                    250    500    1k     2k     3k     4k     6k     8k
    Teto ta       -3.7   -5.8   -7.0  -27.0  -27.6  -29.1  -29.5  -28.8
    我们 ta       -9.5  -13.7  -35.7  -26.9  -18.8  -15.0  -13.7  -14.8

真实齿龈爆破的能量压在 1kHz 以下再滚降；我们的在 1~2kHz 挖了 20dB 的坑，
把能量全堆到 6~8kHz —— 齿龈带通 (3400,9000) 单独量出来峰值在 6657Hz，
就是一段高频嘶声。软腭 (1500,2700) 峰值落在 2kHz，与 Teto ka 一致，不用动。

另一半：低频冲击（250Hz）贡献了起爆能量的 4.3dB，比脉冲本身还响。
d/g 没有 20ms 送气去盖它，所以是一声孤立可闻的「咚」。

   01_现状        齿龈 (3400,9000)   d/g 冲击 ×1.0
   02_齿龈2-5k    齿龈 (2000,5000)   d/g 冲击 ×1.0
   03_冲击减半    齿龈 (3400,9000)   d/g 冲击 ×0.5
   04_两者        齿龈 (2000,5000)   d/g 冲击 ×0.5

注意：**带通是部位属性，02/04 里 ta 也跟着变**（d/t 必须共用一个齿龈谱），
软腭不动，所以 ga/ka 只受冲击那一维影响。d/g 仍保持上一轮定的 −5dB 电平。
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

OUT = os.path.join("demo", "20_dg起爆谱")
F0 = 311.1270
SYLS = ["ba", "pa", "da", "ta", "ga", "ka"]

_ORIG_ALV = ph.PLACE_BURST["alveolar"]

VARIANTS = {
    "01_现状":     dict(alveolar=(3400.0, 9000.0), thump=1.0),
    "02_齿龈2-5k": dict(alveolar=(2000.0, 5000.0), thump=1.0),
    "03_冲击减半": dict(alveolar=(3400.0, 9000.0), thump=0.5),
    "04_两者":     dict(alveolar=(2000.0, 5000.0), thump=0.5),
}


def apply(p):
    ph.PLACE_BURST["alveolar"] = p["alveolar"]
    for k in ("d", "g"):
        ph.CONSONANTS[k]["burst_scale"] = 0.56   # demo/19 定的 −5dB
        ph.CONSONANTS[k]["thump_scale"] = p["thump"]
    for k in ("p", "t", "k", "b"):
        ph.CONSONANTS[k]["burst_scale"] = 1.0


def restore():
    ph.PLACE_BURST["alveolar"] = _ORIG_ALV
    for k in ph.CONSONANTS:
        ph.CONSONANTS[k].pop("burst_scale", None)
        ph.CONSONANTS[k].pop("thump_scale", None)


def main():
    fresh(OUT)          # 先清空，免得上一轮的变体残留
    for name, p in VARIANTS.items():
        apply(p)
        d = os.path.join(OUT, name)
        os.makedirs(d, exist_ok=True)
        for syl in SYLS:
            audio, _ = render.render_cv(syl[0], syl[1], F0)
            audio = dsp.normalize(audio, dsp.rms(audio),
                                  C.VOICED_RMS_DBFS, C.PEAK_CEILING)
            write(os.path.join(d, f"{syl}.wav"), audio)
        print(f"  {name}: 齿龈 {p['alveolar']}  d/g 冲击 ×{p['thump']}")
    restore()
    print(f"输出目录：{OUT}")


if __name__ == "__main__":
    main()
