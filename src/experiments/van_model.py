"""üan 的模型对比，输出到 demo/33_üan的模型/。

üe 定案后（整条韵母一次滑行），üan 要不要跟着改？这一组把两种模型放在一起：

    01_旧     介音 ü(55ms) + 韵腹 ɛ + 鼻尾 n    ← 原来的做法
    02_新065  韵腹 ü，整条滑向 ɛ，之后接鼻尾      曲线 u^0.65
    03_新085  同上，u^0.85
    04_新100  同上，匀速

新模型下 ɛ 只是滑行的终点，**没有静止段**，鼻尾接在滑行结束后。
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

OUT = os.path.join("demo", "33_üan的模型")
F0 = 311.1270

OLD = dict(on=[("v", 55)], on_hold=0, nucleus="E", coda="n")
NEW = dict(nucleus="v", off=[("E", 0)], coda="n", glide_all=True)

VARIANTS = {
    "01_旧": dict(OLD),
    "02_新065": dict(NEW, curve=0.65),
    "03_新085": dict(NEW, curve=0.85),
    "04_新100": dict(NEW, curve=1.0),
}

CV = {
    ("", "van"): "yuan", ("j", "van"): "juan",
    ("q", "van"): "quan", ("x", "van"): "xuan",
}


def main():
    fresh(OUT)
    orig = dict(ph.FINALS["van"])
    for name, spec in VARIANTS.items():
        ph.FINALS["van"] = dict(spec)
        d = os.path.join(OUT, name)
        os.makedirs(d, exist_ok=True)
        for (c, fin), fname in CV.items():
            if c:
                audio, _ = render.render_cv(c, fin, F0)
            else:
                audio, _ = render.render_vowel(fin, F0)
            audio = dsp.normalize(audio, dsp.rms(audio),
                                  C.VOICED_RMS_DBFS, C.PEAK_CEILING)
            write(os.path.join(d, f"{fname}.wav"), audio)
        print(f"  {name}: {spec}")
    ph.FINALS["van"] = orig
    print(f"输出目录：{OUT}")


if __name__ == "__main__":
    main()
