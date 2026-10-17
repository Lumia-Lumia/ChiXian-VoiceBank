"""按参考测量结果重建爆破音，输出到 demo/08_爆破_重建/。

对比四家声库（同一套测量方法，dB 相对元音电平）：

                辅音段   起爆峰   尾段     形状
    Teto日 pa     6ms    -6.8   -12.2   起爆后立刻进元音
    Teto日 ka    24ms    -5.1   -10.1   起爆 → 降到 -17 → 爬升
    Teto英 ka    46ms    -3.7   -12.7
    Kumi中 pa    40ms    -8.1   -18.5   起爆 → 降到 -28 → 爬升
    Kumi中 ba    12ms   -10.5   -14.9
    本声库 pa    96ms    -4.7   -14.7   平直平台 ← 问题所在
    本声库 ka   104ms    -3.4   -14.0   平直平台

两处结构错误：
  1. 辅音段长 96~104ms，是中文参考的 2.4 倍
  2. 平台是平的，参考是「先降后升」

三档只差辅音段长度，其余（起爆激励、部位带通、包络形状）全部一致：

    01_紧凑   起爆6 + 送气20 + 过渡14 = 40ms
    02_中     起爆6 + 送气30 + 过渡20 = 56ms
    03_长     起爆6 + 送气40 + 过渡24 = 70ms
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

OUT = os.path.join("demo", "08_爆破_重建")
F0 = 311.1270
SYLS = ["ba", "pa", "da", "ta", "ga", "ka"]

ORIG = dict(
    click=ph.GAIN_CLICK, burst=ph.GAIN_BURST, lp=ph.BURST_LP,
    plateau=ph.RELEASE_PLATEAU, tail=ph.RELEASE_TAIL,
    attack=ph.RELEASE_ATTACK_MS, glide=ph.GLIDE,
    band=dict(ph.PLACE_BURST),
    burst_ms={k: v.get("burst") for k, v in ph.CONSONANTS.items()},
    asp={k: v.get("aspiration") for k, v in ph.CONSONANTS.items()},
)

# 三个部位互不重叠：双唇低、软腭中、齿龈高
BANDS = {"bilabial": (150.0, 900.0),
         "velar": (900.0, 2600.0),
         "alveolar": (2600.0, 9000.0)}

VARIANTS = {
    "01_紧凑": dict(aspirated=20, unaspirated=6, glide=14),
    "02_中": dict(aspirated=30, unaspirated=10, glide=20),
    "03_长": dict(aspirated=40, unaspirated=14, glide=24),
}


def apply(p):
    ph.GAIN_CLICK = 0.14          # 起爆峰约 -13dB
    ph.GAIN_BURST = 0.10          # 部位带通（高频线索）
    ph.BURST_LP = 8000.0
    ph.RELEASE_PLATEAU = 0.50     # 瞬态衰减到的平台
    ph.RELEASE_TAIL = 0.08        # 送气段末衰减到 -22dB，再由元音起音接上
    ph.RELEASE_ATTACK_MS = 1.5
    ph.GLIDE = p["glide"]
    ph.PLACE_BURST.clear()
    ph.PLACE_BURST.update(BANDS)
    for k in ("p", "t", "k"):
        ph.CONSONANTS[k]["burst"] = 6
        ph.CONSONANTS[k]["aspiration"] = p["aspirated"]
    for k in ("b", "d", "g"):
        ph.CONSONANTS[k]["burst"] = 6
        ph.CONSONANTS[k]["aspiration"] = p["unaspirated"]


def restore():
    ph.GAIN_CLICK = ORIG["click"]
    ph.GAIN_BURST = ORIG["burst"]
    ph.BURST_LP = ORIG["lp"]
    ph.RELEASE_PLATEAU = ORIG["plateau"]
    ph.RELEASE_TAIL = ORIG["tail"]
    ph.RELEASE_ATTACK_MS = ORIG["attack"]
    ph.GLIDE = ORIG["glide"]
    ph.PLACE_BURST.clear()
    ph.PLACE_BURST.update(ORIG["band"])
    for k, v in ORIG["burst_ms"].items():
        if v is not None:
            ph.CONSONANTS[k]["burst"] = v
    for k, v in ORIG["asp"].items():
        if v is not None:
            ph.CONSONANTS[k]["aspiration"] = v


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
