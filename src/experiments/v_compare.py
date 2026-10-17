"""ye / yu / yue 的横向对比，输出到 demo/32_ye_yu_yue/。

demo/30 定下 üe 的新模型：整条韵母就是一次 ü→ɛ 滑行，曲线 u^0.85。
这一组把三个容易混的韵母放在一起：

    ye    ie  —— i + ɛ
    yu    v   —— 纯 ü
    yue   ve  —— 整条滑行
    yuan  van —— 仍是「介音 ü + 韵腹 ɛ + 鼻尾」，用来对照
    jue / que / xue / yun —— 带声母或鼻尾的 ü 韵母

不带对照，全部用当前定稿参数。
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

OUT = os.path.join("demo", "32_ye_yu_yue")
F0 = 311.1270

VOWELS = {
    "ie": "ye", "v": "yu", "ve": "yue", "van": "yuan", "vn": "yun",
    "i": "yi", "e": "e",
}
CV = {
    ("j", "ve"): "jue", ("q", "ve"): "que", ("x", "ve"): "xue",
}


def main():
    fresh(OUT)
    for fin, fname in VOWELS.items():
        audio, _ = render.render_vowel(fin, F0)
        audio = dsp.normalize(audio, dsp.rms(audio),
                              C.VOICED_RMS_DBFS, C.PEAK_CEILING)
        write(os.path.join(OUT, f"{fname}.wav"), audio)
        print(f"  {fin} → {fname}.wav")
    for (c, fin), fname in CV.items():
        audio, _ = render.render_cv(c, fin, F0)
        audio = dsp.normalize(audio, dsp.rms(audio),
                              C.VOICED_RMS_DBFS, C.PEAK_CEILING)
        write(os.path.join(OUT, f"{fname}.wav"), audio)
        print(f"  {c}+{fin} → {fname}.wav")
    print(f"输出目录：{OUT}")


if __name__ == "__main__":
    main()
