"""起爆的激励方式对比，输出到 demo/07_爆破_激励方式/。

问题：起爆听上去像合成器效果音，不像人声。

原因：之前的起爆是「一段带通滤过的白噪」。滤波噪声的相位是随机的，
过共振峰滤波器只会得到一条被塑形的噪声带，激不出有结构的余振。

真实爆破是**闭合突然释放的瞬态**去激励声道，让共振腔自己按共振峰振铃：
一声很短的「啪」，余振由共振峰带宽决定（BW≈80Hz → 约 7ms 衰减）。

四档在「脉冲 / 噪声」的配比上不同：

    01_原噪声    只有噪声，基线
    02_脉冲轻    脉冲 0.12（起爆峰约 -15dB）+ 原噪声
    03_脉冲中    脉冲 0.18（起爆峰约 -11dB）+ 原噪声
    04_脉冲+高频  03 再换上不重叠的三段带通（高频部位线索）

先比较 01/02/03 定脉冲电平，再看 04 的高频带通有没有帮助。
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

OUT = os.path.join("demo", "07_爆破_激励方式")
F0 = 311.1270
SYLS = ["ba", "pa", "da", "ta", "ga", "ka"]

ORIG_BAND = dict(ph.PLACE_BURST)
ORIG = dict(click=ph.GAIN_CLICK, burst=ph.GAIN_BURST, lp=ph.BURST_LP)

# 三个部位互不重叠，参考里它们的起爆峰分别落在
# 双唇 ~150Hz、软腭 ~1400Hz、齿龈 4~8kHz
SEPARATED = {"bilabial": (150.0, 900.0),
             "velar": (900.0, 2600.0),
             "alveolar": (2600.0, 9000.0)}

VARIANTS = {
    "01_原噪声": dict(click=0.0, burst=0.06, band=None, lp=2700.0),
    "02_脉冲轻": dict(click=0.12, burst=0.06, band=None, lp=2700.0),
    "03_脉冲中": dict(click=0.18, burst=0.06, band=None, lp=2700.0),
    "04_脉冲+高频": dict(click=0.18, burst=0.10, band=SEPARATED, lp=8000.0),
}


def apply(p):
    ph.GAIN_CLICK = p["click"]
    ph.GAIN_BURST = p["burst"]
    ph.BURST_LP = p["lp"]
    ph.PLACE_BURST.clear()
    ph.PLACE_BURST.update(ORIG_BAND)
    if p["band"]:
        ph.PLACE_BURST.update(p["band"])


def restore():
    ph.GAIN_CLICK = ORIG["click"]
    ph.GAIN_BURST = ORIG["burst"]
    ph.BURST_LP = ORIG["lp"]
    ph.PLACE_BURST.clear()
    ph.PLACE_BURST.update(ORIG_BAND)


def main():
    fresh(OUT)          # 先清空，免得上一轮的变体残留
    for name, params in VARIANTS.items():
        apply(params)
        d = os.path.join(OUT, name)
        os.makedirs(d, exist_ok=True)
        for s in SYLS:
            audio, _ = render.render_cv(s[0], s[1], F0)
            audio = dsp.normalize(audio, dsp.rms(audio),
                                  C.VOICED_RMS_DBFS, C.PEAK_CEILING)
            write(os.path.join(d, f"{s}.wav"), audio)
        print(f"  {name}: {len(SYLS)} 个音节")
    restore()
    print(f"输出目录：{OUT}")


if __name__ == "__main__":
    main()
