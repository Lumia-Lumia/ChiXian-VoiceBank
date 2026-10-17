"""爆破音的谱平衡，输出到 demo/14_爆破_谱平衡/。

用户反馈仍然偏轻。对比参考后，问题不在总电平（RMS 我们比中文参考还高），
而在**频段分布**——两头薄、中间厚：

                 0-300  300-800  800-2000  2000-5000  5000-12000
    Kumi pa      -5.0    -5.4     -4.9      -12.0      -20.0
    我们 pa     -13.2    -3.5     -3.0      -24.9      -30.3

低频差 8dB、2-5k 差 13dB、5-12k 差 10dB，而 800-2000 反而高 2dB。
单换噪声源改善有限，因为串联谐振器在 5kHz 以上是 60dB/oct 陡降。

四档分别补两端：

    01_现状      不动
    02_补低频    低频冲击 1.5 → 3.5
    03_补高频    部位带通增益 0.25 → 0.55
    04_两头都补  低频冲击 3.5 + 部位带通 0.55
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

OUT = os.path.join("demo", "14_爆破_谱平衡")
F0 = 311.1270
SYLS = ["ba", "pa", "da", "ta", "ga", "ka"]

_ORIG = dict(thump=ph.THUMP_GAIN, burst=ph.GAIN_BURST)

VARIANTS = {
    "01_现状": dict(thump=1.5, burst=0.25),
    "02_补低频": dict(thump=3.5, burst=0.25),
    "03_补高频": dict(thump=1.5, burst=0.55),
    "04_两头都补": dict(thump=3.5, burst=0.55),
}


def main():
    fresh(OUT)          # 先清空，免得上一轮的变体残留
    for name, p in VARIANTS.items():
        ph.THUMP_GAIN = p["thump"]
        ph.GAIN_BURST = p["burst"]
        d = os.path.join(OUT, name)
        os.makedirs(d, exist_ok=True)
        for s in SYLS:
            audio, _ = render.render_cv(s[0], s[1], F0)
            audio = dsp.normalize(audio, dsp.rms(audio),
                                  C.VOICED_RMS_DBFS, C.PEAK_CEILING)
            write(os.path.join(d, f"{s}.wav"), audio)
        print(f"  {name}: 低频冲击 {p['thump']}  带通 {p['burst']}")
    ph.THUMP_GAIN = _ORIG["thump"]
    ph.GAIN_BURST = _ORIG["burst"]
    print(f"输出目录：{OUT}")


if __name__ == "__main__":
    main()
