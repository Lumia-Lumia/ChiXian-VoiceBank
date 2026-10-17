"""普通话韵母与第二批声母的试听，输出到 demo/25_韵母与声母/。

中文完整化的第一批实现：37 个韵母 + 10 个新声母（f z c zh ch sh r j q x）。
这一组不做对照，只用来逐个检查发音对不对。

    01_韵母/    零声母，用拼音写法命名：a o e ai ei ao ou an en ang eng ong
                er yi ya ye yao you yan yin yang ying yong wu wa wo wai wei
                wan wen wang weng yu yue yuan yun zi zhi
    02_新声母/  每个新声母配两个韵母：fa za ca zha cha sha ra
                ji qi xi ze zhe ju qu xu zi ci si zhi chi shi ri
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config as C
import dsp
import mandarin as m
import phonemes as ph
import render
from _demo import fresh, write

OUT = os.path.join("demo", "25_韵母与声母")
F0 = 311.1270

# 韵母 → 用哪个零声母拼音命名（同音只留一个代表）
FINALS = {
    "a": "a", "o": "o", "e": "e", "ai": "ai", "ei": "ei", "ao": "ao", "ou": "ou",
    "an": "an", "en": "en", "ang": "ang", "eng": "eng", "ong": "ong", "er": "er",
    "i": "yi", "ia": "ya", "ie": "ye", "iao": "yao", "iou": "you", "ian": "yan",
    "in": "yin", "iang": "yang", "ing": "ying", "iong": "yong",
    "u": "wu", "ua": "wa", "uo": "wo", "uai": "wai", "uei": "wei",
    "uan": "wan", "uen": "wen", "uang": "wang", "ueng": "weng",
    "v": "yu", "ve": "yue", "van": "yuan", "vn": "yun",
    "i0": "zi", "ir": "zhi",
}

# 新声母 → [(韵母, 文件名), ...]。文件名单独给，不能拿韵母名拼 ——
# 舌尖元音和 j/q/x 后面的 i 拼出来都不是拼音（z+i 是 zi，但 j+i 是 ji）。
NEW_INITIALS = {
    "f":  [("a", "fa"), ("en", "fen")],
    "z":  [("a", "za"), ("e", "ze"), ("i0", "zi")],
    "c":  [("a", "ca"), ("e", "ce"), ("i0", "ci")],
    "zh": [("a", "zha"), ("e", "zhe"), ("ir", "zhi")],
    "ch": [("a", "cha"), ("e", "che"), ("ir", "chi")],
    "sh": [("a", "sha"), ("e", "she"), ("ir", "shi")],
    "r":  [("e", "re"), ("ir", "ri")],
    "j":  [("i", "ji"), ("a", "jia")],
    "q":  [("i", "qi"), ("a", "qia")],
    "x":  [("i", "xi"), ("a", "xia")],
}


def normalize(audio):
    return dsp.normalize(audio, dsp.rms(audio), C.VOICED_RMS_DBFS, C.PEAK_CEILING)


def main():
    fresh(OUT)

    d = os.path.join(OUT, "01_韵母")
    os.makedirs(d, exist_ok=True)
    for fin, name in FINALS.items():
        audio, _ = render.render_vowel(fin, F0)
        write(os.path.join(d, f"{name}.wav"), normalize(audio))
        print(f"  韵母 {fin} → {name}.wav")

    d = os.path.join(OUT, "02_新声母")
    os.makedirs(d, exist_ok=True)
    for ini, pairs in NEW_INITIALS.items():
        for fin, name in pairs:
            audio, _ = render.render_cv(ini, fin, F0)
            write(os.path.join(d, f"{name}.wav"), normalize(audio))
            print(f"  声母 {ini}+{fin} → {name}.wav")

    print(f"输出目录：{OUT}")


if __name__ == "__main__":
    main()
