"""渲染几组不同设计的 /s/，用于试听挑选。

    python src/experiments/s_variants.py

输出到 demo/s_variants/<方案名>/，每个方案 an sa si su 四个音节。
调音色只需改下面的 VARIANTS 表。
"""

import os
import sys

# 实验脚本在子目录里，而合成模块在上一级（src/）。从项目根目录运行时
# 脚本所在目录会被加进 sys.path，但 src/ 不会，所以这里补一条。
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import dsp
import phonemes as ph
import render

F0 = 261.6256
ITEMS = [("sa", "s", "a"), ("si", "s", "i"), ("su", "s", "u"), ("ha", "h", "a")]

BASE = dict(SIB_HP=ph.SIB_HP, SIB_PEAKS=ph.SIB_PEAKS, SIB_ROUGH=ph.SIB_ROUGH,
            FF_SPILL=ph.FF_SPILL, FRIC_ON_RAMP=ph.FRIC_ON_RAMP,
            GAIN=ph.GAIN_FRICATIVE_S, DUR=ph.CONSONANTS["s"]["frication"])

VARIANTS = {
    "V1_当前": {},
    "V2_谱更低": dict(SIB_HP=2800.0,
                      SIB_PEAKS=((4000, 1500), (5800, 1700), (7800, 2200))),
    "V3_更长更平": dict(DUR=95, FRIC_ON_RAMP=20.0,
                        SIB_PEAKS=((4300, 2200), (6600, 2600), (8600, 2600))),
    "V4_更响": dict(GAIN=0.45),
}


def apply(over):
    ph.SIB_HP = over.get("SIB_HP", BASE["SIB_HP"])
    ph.SIB_PEAKS = over.get("SIB_PEAKS", BASE["SIB_PEAKS"])
    ph.SIB_ROUGH = over.get("SIB_ROUGH", BASE["SIB_ROUGH"])
    ph.FF_SPILL = over.get("FF_SPILL", BASE["FF_SPILL"])
    ph.FRIC_ON_RAMP = over.get("FRIC_ON_RAMP", BASE["FRIC_ON_RAMP"])
    ph.GAIN_FRICATIVE_S = over.get("GAIN", BASE["GAIN"])
    ph.GAIN_FRICATIVE_VC = over.get("GAIN", BASE["GAIN"])
    ph.CONSONANTS["s"]["frication"] = BASE["DUR"]
    for name in ("s",):
        ph.CONSONANTS[name]["frication"] = over.get("DUR", BASE["DUR"])


def main():
    for label, over in VARIANTS.items():
        apply(over)
        outdir = os.path.join("demo", "s_variants", label)
        os.makedirs(outdir, exist_ok=True)
        for name, c, v in ITEMS:
            audio, _ = render.render_cv(c, v, F0)
            dsp.write_wav(os.path.join(outdir, f"{name}.wav"), audio)
        pe = ph.CONSONANTS["s"]["frication"]
        print(f"  demo/s_variants/{label}/  "
              f"高通{ph.SIB_HP:.0f}Hz  峰{tuple(int(x[0]) for x in ph.SIB_PEAKS)}  "
              f"擦音{pe}ms  增益{ph.GAIN_FRICATIVE_S}")
    apply({})   # 复原


if __name__ == "__main__":
    main()
