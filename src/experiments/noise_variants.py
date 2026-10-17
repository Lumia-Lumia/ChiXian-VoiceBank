"""送气段改用倾斜/起伏噪声，输出到 demo/09_噪声源/。

前提：白噪不适合做爆破音。它等能量每赫兹、完全稳态、幅度服从高斯分布，
听起来是「嘶——」一条电子噪声带。真实的气流噪声：

  * 谱往高频掉（低频能量多）
  * 幅度随时间起伏（湍流不是稳态的）

四档全部沿用 demo/08 的 01_紧凑结构（起爆 6ms + 送气 20ms + 过渡 14ms，
三段互不重叠的部位带通，瞬态脉冲激励），只换噪声源：

    01_白噪            白噪，基线
    02_声源派生        声门源相位随机化（谱形同声门源，无周期性）
    03_声源派生+起伏   同上，再叠 35% 的慢速幅度起伏
    04_纯脉冲起爆      03 再拿掉起爆的部位带通噪声，只留脉冲
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

OUT = os.path.join("demo", "09_噪声源")
F0 = 311.1270
SYLS = ["ba", "pa", "da", "ta", "ga", "ka"]

BANDS = {"bilabial": (150.0, 900.0),
         "velar": (900.0, 2600.0),
         "alveolar": (2600.0, 9000.0)}

_ORIG = dict(
    tilt=render.NOISE_TILT, rough=render.NOISE_ROUGH,
    click=ph.GAIN_CLICK, burst=ph.GAIN_BURST, lp=ph.BURST_LP,
    plateau=ph.RELEASE_PLATEAU, tail=ph.RELEASE_TAIL,
    attack=ph.RELEASE_ATTACK_MS, glide=ph.GLIDE, band=dict(ph.PLACE_BURST),
    burst_ms={k: v.get("burst") for k, v in ph.CONSONANTS.items()},
    asp={k: v.get("aspiration") for k, v in ph.CONSONANTS.items()},
)

VARIANTS = {
    "01_白噪": dict(src=False, rough=0.0, burst=0.10),
    "02_声源派生": dict(src=True, rough=0.0, burst=0.10),
    "03_声源派生+起伏": dict(src=True, rough=0.35, burst=0.10),
    "04_纯脉冲起爆": dict(src=True, rough=0.35, burst=0.0),
}


def apply(p):
    # 结构：沿用 01_紧凑
    ph.GAIN_CLICK = 0.14
    ph.GAIN_BURST = 0.10
    ph.BURST_LP = 8000.0
    ph.RELEASE_PLATEAU = 0.50
    ph.RELEASE_TAIL = 0.08
    ph.RELEASE_ATTACK_MS = 1.5
    ph.GLIDE = 14
    ph.PLACE_BURST.clear()
    ph.PLACE_BURST.update(BANDS)
    for k in ("p", "t", "k"):
        ph.CONSONANTS[k]["burst"] = 6
        ph.CONSONANTS[k]["aspiration"] = 20
    for k in ("b", "d", "g"):
        ph.CONSONANTS[k]["burst"] = 6
        ph.CONSONANTS[k]["aspiration"] = 6
    # 噪声源
    render.NOISE_FROM_SOURCE = p["src"]
    render.NOISE_ROUGH = p["rough"]
    ph.GAIN_BURST = p["burst"]


def restore():
    render.NOISE_TILT = _ORIG["tilt"]
    render.NOISE_ROUGH = _ORIG["rough"]
    render.NOISE_FROM_SOURCE = False
    ph.GAIN_CLICK = _ORIG["click"]
    ph.GAIN_BURST = _ORIG["burst"]
    ph.BURST_LP = _ORIG["lp"]
    ph.RELEASE_PLATEAU = _ORIG["plateau"]
    ph.RELEASE_TAIL = _ORIG["tail"]
    ph.RELEASE_ATTACK_MS = _ORIG["attack"]
    ph.GLIDE = _ORIG["glide"]
    ph.PLACE_BURST.clear()
    ph.PLACE_BURST.update(_ORIG["band"])
    for k, v in _ORIG["burst_ms"].items():
        if v is not None:
            ph.CONSONANTS[k]["burst"] = v
    for k, v in _ORIG["asp"].items():
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
