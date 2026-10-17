"""d/g 的起爆电平四档，输出到 demo/19_dg起爆/。

用户反馈：d/g 的爆破有点过响（p/t/k 正常）。

结构原因：d/g 不送气，辅音段只有 26ms（闭合 + 起爆6 + 送气6 + 过渡14），
6ms 的起爆占了可听内容的近一半；而 p/t/k 后面还有 20ms 送气，起爆占比小得多。
所以同样的起爆增益，在 d/g 上就显得突出。

用逐辅音的 `burst_scale` 压 d/g，`p/t/k` 与 `b` 保持 1.0（b 的 12ms 起爆
是上一步为可听性专门加长的，压下去会退回听不清）：

    01_现状   1.00
    02_压1.5dB 0.84
    03_压3dB   0.71
    04_压5dB   0.56
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

OUT = os.path.join("demo", "19_dg起爆")
F0 = 311.1270
SYLS = ["ba", "pa", "da", "ta", "ga", "ka"]

VARIANTS = {
    "01_现状": 1.00,
    "02_压1.5dB": 0.84,
    "03_压3dB": 0.71,
    "04_压5dB": 0.56,
}


def apply(scale):
    # 只压 d/g。b 的起爆是 12ms（上一步为可听性专门加长的），压下去会退回听不清
    for k in ("d", "g"):
        ph.CONSONANTS[k]["burst_scale"] = scale
    for k in ("p", "t", "k", "b"):
        ph.CONSONANTS[k]["burst_scale"] = 1.0


def restore():
    for k in ph.CONSONANTS:
        ph.CONSONANTS[k].pop("burst_scale", None)


def main():
    fresh(OUT)          # 先清空，免得上一轮的变体残留
    for name, s in VARIANTS.items():
        apply(s)
        d = os.path.join(OUT, name)
        os.makedirs(d, exist_ok=True)
        for syl in SYLS:
            audio, _ = render.render_cv(syl[0], syl[1], F0)
            audio = dsp.normalize(audio, dsp.rms(audio),
                                  C.VOICED_RMS_DBFS, C.PEAK_CEILING)
            write(os.path.join(d, f"{syl}.wav"), audio)
        print(f"  {name}: d/g 起爆 ×{s}（{20*np.log10(s):+.1f}dB）")
    restore()
    print(f"输出目录：{OUT}")


if __name__ == "__main__":
    main()
