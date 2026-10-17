"""爆破音四档方案对比，输出到 demo/05_爆破_送气形状/。

背景：把参考声库的包络量出来后发现，我们的塞音是

    静音 → 起爆 → **-15dB 的平坦送气平台 90~100ms** → 40ms 爬升进元音

而重音テト的 CV 样本是

    静音 → 起爆 → **5~10ms 就进元音**（只有 /ka/ 有 10ms 低谷再 30ms 爬升）

中文的 p/t/k 本来就送气长一些，但「平坦一段再突然爬上去」这个形状不对。
四档分别动一处：

    01_现状     基线
    02_短送气   送气 55→32ms（不送气 12→10），过渡 32→26
    03_衰减     送气段从平台电平一路衰减（PLATEAU 0.75→0.50、TAIL 0.55→0.25）
    04_短+过渡  02 的基础上去掉独立的过渡段，让送气本身就在滑向元音
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

OUT = os.path.join("demo", "05_爆破_送气形状")
F0 = 311.1270
SYLS = ["ba", "pa", "da", "ta", "ga", "ka"]

# 原始值，跑完要还原 —— 这几个模块级变量是全局状态
_ORIG = dict(
    PLATEAU=ph.RELEASE_PLATEAU,
    TAIL=ph.RELEASE_TAIL,
    GLIDE=ph.GLIDE,
    ASP={k: v["aspiration"] for k, v in ph.CONSONANTS.items() if "aspiration" in v},
)

VARIANTS = {
    "01_现状": dict(),
    "02_短送气": dict(aspirated=32, unaspirated=10, glide=26),
    "03_衰减": dict(plateau=0.50, tail=0.25),
    "04_短+过渡": dict(aspirated=32, unaspirated=10, glide=16, release_glide=True),
}


def restore():
    ph.RELEASE_PLATEAU = _ORIG["PLATEAU"]
    ph.RELEASE_TAIL = _ORIG["TAIL"]
    ph.GLIDE = _ORIG["GLIDE"]
    for k, v in _ORIG["ASP"].items():
        ph.CONSONANTS[k]["aspiration"] = v
    render.RELEASE_GLIDE = False


def apply(p):
    restore()
    if "aspirated" in p:
        for k in ("p", "t", "k"):
            ph.CONSONANTS[k]["aspiration"] = p["aspirated"]
    if "unaspirated" in p:
        for k in ("b", "d", "g"):
            ph.CONSONANTS[k]["aspiration"] = p["unaspirated"]
    if "glide" in p:
        ph.GLIDE = p["glide"]
    if "plateau" in p:
        ph.RELEASE_PLATEAU = p["plateau"]
    if "tail" in p:
        ph.RELEASE_TAIL = p["tail"]
    render.RELEASE_GLIDE = bool(p.get("release_glide"))


def main():
    fresh(OUT)          # 先清空，免得上一轮的变体残留
    for name, params in VARIANTS.items():
        apply(params)
        d = os.path.join(OUT, name)
        os.makedirs(d, exist_ok=True)
        for s in SYLS:
            c, v = s[0], s[1]
            audio, _ = render.render_cv(c, v, F0)
            audio = dsp.normalize(audio, dsp.rms(audio),
                                  C.VOICED_RMS_DBFS, C.PEAK_CEILING)
            write(os.path.join(d, f"{s}.wav"), audio)
        print(f"  {name}: {len(SYLS)} 个音节")
    restore()
    print(f"输出目录：{OUT}")


if __name__ == "__main__":
    main()
