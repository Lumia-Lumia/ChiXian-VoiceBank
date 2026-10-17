"""送气噪声源 A/B，输出到 demo/18_噪声源AB/。

之前有个静默失败：`NOISE_FROM_SOURCE` 的默认值是 False，所以 demo/13、16、17
用的都是**白噪**，而 demo/11 的 04（用户认定表现最好的那档）用的是**声源派生
噪声**。两者的比较基线不一致，需要在实际定稿参数下重新 A/B 一次。

    01_白噪      宽带白噪经声道滤波（当前默认）
    02_声源派生  声门源相位随机化 + 35% 缓慢幅度起伏
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

OUT = os.path.join("demo", "18_噪声源AB")
F0 = 311.1270
SYLS = ["ba", "pa", "da", "ta", "ga", "ka"]

_ORIG = dict(src=render.NOISE_FROM_SOURCE, rough=render.NOISE_ROUGH)

VARIANTS = {
    "01_白噪": dict(src=False, rough=0.0),
    "02_声源派生": dict(src=True, rough=0.35),
}


def main():
    fresh(OUT)          # 先清空，免得上一轮的变体残留
    for name, p in VARIANTS.items():
        render.NOISE_FROM_SOURCE = p["src"]
        render.NOISE_ROUGH = p["rough"]
        d = os.path.join(OUT, name)
        os.makedirs(d, exist_ok=True)
        for s in SYLS:
            audio, _ = render.render_cv(s[0], s[1], F0)
            audio = dsp.normalize(audio, dsp.rms(audio),
                                  C.VOICED_RMS_DBFS, C.PEAK_CEILING)
            write(os.path.join(d, f"{s}.wav"), audio)
        print(f"  {name}: 声源派生={p['src']} 起伏={p['rough']}")
    render.NOISE_FROM_SOURCE = _ORIG["src"]
    render.NOISE_ROUGH = _ORIG["rough"]
    print(f"输出目录：{OUT}")


if __name__ == "__main__":
    main()
