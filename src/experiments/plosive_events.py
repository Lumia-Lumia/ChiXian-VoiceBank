"""爆破音的「发声事件」逐项叠加，输出到 demo/11_爆破_事件组合/。

依据（文献 + 参考声库实测）：

1. **起爆谱由阻塞点前方的腔体决定**（Wright：the cavity in front of the
   stop determines the spectrum of the noise）。峰位置：双唇 600~800Hz、
   齿龈 4000Hz 以上、软腭 1800~2000Hz。原来的软腭带通 (900,2600) 偏低。

2. **送气与共振峰过渡重叠**（牛津：transitions "often overlapping with"
   aspiration）。原来是送气走完再单独过渡一段。

3. **送气抬高后接元音的起始 F0**。实测重音テト：pa/ta/ka 的 F0 起点比稳态
   高 +8.8/+10.9/+13.7Hz，ba/da/ga 只有 +1.9/+4.4/+4.4Hz。

四档逐项叠加，用来听每一条各自的贡献：

    01_基础     全关（上一轮的状态）
    02_新带通   只换部位带通
    03_过渡重叠 再加送气与过渡合并
    04_加F0扰动 再加起始 F0 抬升

起爆电平固定用 demo/10 的 02_中（脉冲 0.25 / 带通 0.25）。
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

OUT = os.path.join("demo", "11_爆破_事件组合")
F0 = 311.1270
SYLS = ["ba", "pa", "da", "ta", "ga", "ka"]

OLD_BANDS = {"bilabial": (450.0, 1300.0),
             "alveolar": (1800.0, 3200.0),
             "velar": (950.0, 2100.0)}
NEW_BANDS = {"bilabial": (400.0, 950.0),
             "alveolar": (3400.0, 9000.0),
             "velar": (1500.0, 2700.0)}

_ORIG_BAND = dict(ph.PLACE_BURST)
_ORIG_BOOST = ph.ASP_F0_BOOST
_ORIG = dict(
    click=ph.GAIN_CLICK, burst=ph.GAIN_BURST, lp=ph.BURST_LP,
    plateau=ph.RELEASE_PLATEAU, tail=ph.RELEASE_TAIL,
    attack=ph.RELEASE_ATTACK_MS, glide=ph.GLIDE,
    burst_ms={k: v.get("burst") for k, v in ph.CONSONANTS.items()},
    asp={k: v.get("aspiration") for k, v in ph.CONSONANTS.items()},
    src=render.NOISE_FROM_SOURCE, rough=render.NOISE_ROUGH,
)

VARIANTS = {
    "01_基础": dict(band=OLD_BANDS, glide_seg=False, f0=False),
    "02_新带通": dict(band=NEW_BANDS, glide_seg=False, f0=False),
    "03_过渡重叠": dict(band=NEW_BANDS, glide_seg=True, f0=False),
    "04_加F0扰动": dict(band=NEW_BANDS, glide_seg=True, f0=True),
}


def apply(p):
    # 起爆电平：demo/10 的 02_中
    ph.GAIN_CLICK = 0.25
    ph.GAIN_BURST = 0.25
    ph.BURST_LP = 8000.0
    ph.RELEASE_PLATEAU = 0.50
    ph.RELEASE_TAIL = 0.08
    ph.RELEASE_ATTACK_MS = 1.5
    ph.GLIDE = 14
    for k in ("p", "t", "k"):
        ph.CONSONANTS[k]["burst"] = 6
        ph.CONSONANTS[k]["aspiration"] = 20
    for k in ("b", "d", "g"):
        ph.CONSONANTS[k]["burst"] = 6
        ph.CONSONANTS[k]["aspiration"] = 6
    render.NOISE_FROM_SOURCE = True
    render.NOISE_ROUGH = 0.35
    # 三个开关
    ph.PLACE_BURST.clear()
    ph.PLACE_BURST.update(p["band"])
    render.RELEASE_GLIDE = p["glide_seg"]
    ph.ASP_F0_BOOST = _ORIG_BOOST if p["f0"] else 0.0


def restore():
    ph.PLACE_BURST.clear()
    ph.PLACE_BURST.update(_ORIG_BAND)
    ph.ASP_F0_BOOST = _ORIG_BOOST
    render.RELEASE_GLIDE = False
    render.NOISE_FROM_SOURCE = _ORIG["src"]
    render.NOISE_ROUGH = _ORIG["rough"]
    ph.GAIN_CLICK = _ORIG["click"]
    ph.GAIN_BURST = _ORIG["burst"]
    ph.BURST_LP = _ORIG["lp"]
    ph.RELEASE_PLATEAU = _ORIG["plateau"]
    ph.RELEASE_TAIL = _ORIG["tail"]
    ph.RELEASE_ATTACK_MS = _ORIG["attack"]
    ph.GLIDE = _ORIG["glide"]
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
