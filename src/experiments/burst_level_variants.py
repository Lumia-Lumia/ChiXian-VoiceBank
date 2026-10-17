"""起爆电平四档，输出到 demo/10_起爆电平/。

用户反馈：几乎听不见爆破音。测量确认了原因 ——

    目标（参考）  pa 峰 -8.1dB 质心 400~600      ta 峰 -7.9 质心 1400~2700
    本声库        pa 峰 -12.1  质心 377         ta 峰 -4.3 质心 747

起爆既不够响、频谱又偏低（377Hz 是低频的「咚」，本来就不容易被听见）。
这里把**脉冲电平**和**部位带通电平**一起往上推，其余沿用 09 的结构
（声源派生噪声、瞬态脉冲、三段互不重叠的部位带通）。

    01_很轻   脉冲 0.14  带通 0.10   现状
    02_中     脉冲 0.25  带通 0.25
    03_响     脉冲 0.40  带通 0.40
    04_很响   脉冲 0.60  带通 0.60
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

OUT = os.path.join("demo", "10_起爆电平")
F0 = 311.1270
SYLS = ["ba", "pa", "da", "ta", "ga", "ka"]

BANDS = {"bilabial": (150.0, 900.0),
         "velar": (900.0, 2600.0),
         "alveolar": (2600.0, 9000.0)}

_ORIG = dict(
    click=ph.GAIN_CLICK, burst=ph.GAIN_BURST, lp=ph.BURST_LP,
    plateau=ph.RELEASE_PLATEAU, tail=ph.RELEASE_TAIL,
    attack=ph.RELEASE_ATTACK_MS, glide=ph.GLIDE, band=dict(ph.PLACE_BURST),
    burst_ms={k: v.get("burst") for k, v in ph.CONSONANTS.items()},
    asp={k: v.get("aspiration") for k, v in ph.CONSONANTS.items()},
    src=render.NOISE_FROM_SOURCE, rough=render.NOISE_ROUGH,
)

VARIANTS = {
    "01_很轻": dict(click=0.14, band=0.10),
    "02_中": dict(click=0.25, band=0.25),
    "03_响": dict(click=0.40, band=0.40),
    "04_很响": dict(click=0.60, band=0.60),
}


def apply(p):
    ph.GAIN_CLICK = p["click"]
    ph.GAIN_BURST = p["band"]
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
    render.NOISE_FROM_SOURCE = True
    render.NOISE_ROUGH = 0.35


def restore():
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
    render.NOISE_FROM_SOURCE = _ORIG["src"]
    render.NOISE_ROUGH = _ORIG["rough"]


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
