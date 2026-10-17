"""韵尾渐变曲线与鼻尾音色，输出到 demo/26_韵尾渐变/。

demo/25 的用户反馈：
  1. ai / ao 时长很长，抬起开始太靠后，前半段完全是 a —— 应「早些开始、
     慢慢抬升、尾部快速抬升」
  2. an / ang 发音完全不对，一部分可能也是开始太晚

所以引擎新增两个旋钮：

    FIN_GLIDE_SPAN  滑音占韵腹的比例（1.0 = 整段都在走）
    CODA_F/CODA_BW  鼻尾的目标共振峰（None = MURMUR + DEFAULT_BW）

四个变体是这两维的交叉。鼻尾的「亮」版本把 F1 从 250 抬到 400、带宽放宽到
280 —— 实测我们的鼻音在 800~2200Hz 比参考低 20dB 以上，听感是一团低频嗡鸣。

    01_全段       span 1.0   暗鼻尾（MURMUR 原值）
    02_后六成     span 0.6   暗鼻尾
    03_全段_亮鼻  span 1.0   亮鼻尾
    04_后六成_亮鼻 span 0.6   亮鼻尾

只渲 ai / ao / an / ang 四个韵母，另外附一个 a 作对照。
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

OUT = os.path.join("demo", "26_韵尾渐变")
F0 = 311.1270
FINALS = ["a", "ai", "ao", "an", "ang"]

# 亮鼻尾：F1 抬到 400、带宽放宽，但**保留 n / ng 的 F2 差别**
# （1700 vs 1000）—— 那是两者唯一可靠的听感线索。
BRIGHT_F = {
    "n":  [400.0, 1600.0, 2500.0, 3400.0, 4000.0],
    "ng": [400.0, 1000.0, 2200.0, 3300.0, 4000.0],
}
BRIGHT_BW = {
    "n":  [280.0, 250.0, 200.0, 220.0, 300.0],
    "ng": [280.0, 260.0, 200.0, 220.0, 300.0],
}

VARIANTS = {
    "01_全段":        dict(span=1.0, bright=False),
    "02_后六成":      dict(span=0.6, bright=False),
    "03_全段_亮鼻":   dict(span=1.0, bright=True),
    "04_后六成_亮鼻": dict(span=0.6, bright=True),
}

_ORIG = dict(span=ph.FIN_GLIDE_SPAN, F=dict(render.CODA_F), BW=dict(render.CODA_BW))


def apply(p):
    ph.FIN_GLIDE_SPAN = p["span"]
    render.CODA_F = dict(BRIGHT_F) if p["bright"] else {}
    render.CODA_BW = dict(BRIGHT_BW) if p["bright"] else {}


def restore():
    ph.FIN_GLIDE_SPAN = _ORIG["span"]
    render.CODA_F = dict(_ORIG["F"])
    render.CODA_BW = dict(_ORIG["BW"])


def main():
    fresh(OUT)
    for name, p in VARIANTS.items():
        apply(p)
        d = os.path.join(OUT, name)
        os.makedirs(d, exist_ok=True)
        for fin in FINALS:
            audio, _ = render.render_vowel(fin, F0)
            audio = dsp.normalize(audio, dsp.rms(audio),
                                  C.VOICED_RMS_DBFS, C.PEAK_CEILING)
            write(os.path.join(d, f"{fin}.wav"), audio)
        print(f"  {name}: span={p['span']} 亮鼻={p['bright']}")
    restore()
    print(f"输出目录：{OUT}")


if __name__ == "__main__":
    main()
