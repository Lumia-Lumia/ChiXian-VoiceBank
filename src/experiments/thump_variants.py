"""释放低频冲击四档，输出到 demo/13_低频冲击/。

用户反馈：整体偏轻、b 听不见。对比参考后找到了原因 ——

             0-300   300-800  800-2000  2000-5000   质心
    Kumi pa   -5.0    -5.4     -4.9     -12.0     916Hz
    我们 pa  -14.7    -5.5     -1.7     -20.7     925Hz

参考声库的辅音段**在 300Hz 以下是最强的一档**，我们低了约 10dB。
"轻"不是电平不够（RMS 我们还高 2~4dB），而是缺了低频的"重量"。

原因是脉冲要过共振峰滤波器，而 F1（约 1037Hz）把 300Hz 以下全挡住了。
物理上，闭合突然释放除了高频瞬态，还有一次**低频的压力冲击**——补一条
不经过声道的低频衰减即可。

四档只差这条低频冲击的增益：

    01_无      0.0   当前
    02_轻      1.5
    03_中      3.0   0-300Hz 从 -14.7 提到 -7.2，质心 808Hz
    04_重      5.0
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

OUT = os.path.join("demo", "13_低频冲击")
F0 = 311.1270
SYLS = ["ba", "pa", "da", "ta", "ga", "ka"]

_ORIG = ph.THUMP_GAIN

VARIANTS = {
    "01_无": 0.0,
    "02_轻": 1.5,
    "03_中": 3.0,
    "04_重": 5.0,
}


def main():
    global _ORIG
    fresh(OUT)          # 先清空，免得上一轮的变体残留
    for name, gain in VARIANTS.items():
        ph.THUMP_GAIN = gain
        d = os.path.join(OUT, name)
        os.makedirs(d, exist_ok=True)
        for s in SYLS:
            audio, _ = render.render_cv(s[0], s[1], F0)
            audio = dsp.normalize(audio, dsp.rms(audio),
                                  C.VOICED_RMS_DBFS, C.PEAK_CEILING)
            write(os.path.join(d, f"{s}.wav"), audio)
        print(f"  {name}: 低频冲击 ×{gain}")
    ph.THUMP_GAIN = _ORIG
    print(f"输出目录：{OUT}")


if __name__ == "__main__":
    main()
