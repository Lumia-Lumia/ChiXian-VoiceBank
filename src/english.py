"""英语音素表（Delta 式英语 CVVC，X-SAMPA 别名）。

规范和中文那份一样：本文件只放**参数**，装配逻辑在 `render.py`。
render 的三个入口都有 `tbl=` 参数，传 `english` 即可复用同一套 DSP。

别名体系
--------
用 Delta 式英语 CVVC 的 X-SAMPA 写法（UTAU 英语的事实标准，见
https://tl.tubs.wtf/2020/11/09/delta-eng）:

    元音   i I E { A O V U u @ 3
    双元音 aI eI aU OI oU
    辅音   p b t d k g f v T D s z S Z h tS dZ m n N l r w j

四种别名形态（本批只做前两种 + 后两种的同形别名）：

    CV          `p a`       词中
    - CV        `- p a`     词首
    V C         `a p`       词中收尾
    V C-        `a p-`      词尾

Delta 的第 6、7 号表把 `- CV`/`CV` 与 `V C`/`V C-` 视作同一份采样（只是别名
不同），本批照此办理 —— 省一半渲染量，且这两组差别本来就在 oto 参数里而不是
波形里。辅音丛（`C C` / `C C-`）留到第二批。

元音说明
--------
共振峰是**成人男声基准值**（Peterson & Barney 1952 一类），照旧由
`config.FORMANT_SCALE_BY_INDEX` 统一做女性化缩放。所以这里填男声值即可，
不要预先乘 1.22 —— 那会缩放两次。

双元音用 `F`（起点）+ `F2`（终点）+ `DIPH_AT`（转折点比例）表示，
渲染时在元音内部做一次共振峰滑动。
"""

from phonemes import (DEFAULT_BW, FADE_OUT, FF_SPILL, GAIN_BURST,
                     GAIN_FRICATIVE_H, GAIN_FRICATIVE_S, GAIN_LATERAL,
                     GAIN_LATERAL_GLIDE, GAIN_LATERAL_VC, GAIN_MURMUR,
                     GAIN_NASAL_GLIDE, GAIN_RELEASE, GLIDE, RELEASE_SPILL,
                     VC_GLIDE, VC_VOWEL, VOWEL_HOLD, VOWEL_ON_RAMP,
                     VOWEL_TAIL)

# F4/F5 所有元音共用：英语里这两条基本不参与音位对立，
# 值取与中文表一致，保持两个语种的高频手感相同。
_TAIL_F = [3400.0, 4000.0]
_BW = [80.0, 110.0, 150.0, 200.0, 300.0]


def _v(f1, f2, f3, bw1=None, bw2=None):
    BW = list(_BW)
    if bw1 is not None:
        BW[0] = bw1
    if bw2 is not None:
        BW[1] = bw2
    return dict(F=[f1, f2, f3] + _TAIL_F, BW=BW)


# --------------------------------------------------------------------------
# 单元音
# --------------------------------------------------------------------------
VOWELS = {
    "i": _v(270, 2290, 3010, bw1=70),     # feel
    "I": _v(390, 1990, 2550),             # bit
    "E": _v(530, 1840, 2480),             # bed
    "{": _v(660, 1720, 2410),             # bad
    "A": _v(730, 1090, 2440),             # art
    "O": _v(570,  840, 2410),             # bot
    "V": _v(640, 1190, 2390),             # cut
    "U": _v(440, 1020, 2240),             # could
    "u": _v(300,  870, 2240, bw1=70),     # food
    "3": _v(490, 1350, 1690),             # bird（F3 低是美式儿化的关键）
    "@": _v(500, 1500, 2500),             # 非重读 schwa
}

# --------------------------------------------------------------------------
# 双元音：起点 F + 终点 F2
# --------------------------------------------------------------------------
# 终点的取值是**滑音目标**，不是完整的第二个元音 —— 真实的 aI 后半段只是
# 一个趋于 ɪ 的方向，并不会真的站到 ɪ 上。
_I_OFF = [400.0, 1900.0, 2550.0] + _TAIL_F
_U_OFF = [450.0,  980.0, 2200.0] + _TAIL_F

for _alias, _start, _off, _at in [
    ("aI", "A", _I_OFF, 0.45),   # I
    ("eI", "E", _I_OFF, 0.45),   # bake
    ("aU", "A", _U_OFF, 0.45),   # round
    ("OI", "O", _I_OFF, 0.40),   # boy
    ("oU", "O", _U_OFF, 0.40),   # old
]:
    VOWELS[_alias] = dict(F=list(VOWELS[_start]["F"]), F2=list(_off),
                          BW=list(VOWELS[_start]["BW"]),
                          DIPH_AT=_at)


# --------------------------------------------------------------------------
# 部位的共振峰轨迹起点
# --------------------------------------------------------------------------
PLACE_LOCUS = {
    "bilabial":     [300.0,  800.0, 2200.0, 3300.0, 4000.0],
    "labiodental":  [330.0, 1200.0, 2400.0, 3300.0, 4000.0],
    "dental":       [320.0, 1500.0, 2500.0, 3400.0, 4000.0],
    "alveolar":     [320.0, 1700.0, 2600.0, 3400.0, 4000.0],
    "postalveolar": [330.0, 1800.0, 2400.0, 3300.0, 4000.0],
    "lateral":      [350.0, 1100.0, 2700.0, 3400.0, 4000.0],
    "velar":        None,          # 逐元音给，见下
    "glottal":      None,          # /h/ 沿用后接元音
}

# 软腭与齿龈的 locus **必须逐元音给**，理由在 phonemes.py 里写得很细：
# 给固定值会让 /gu/ 听成 /du/、/ko/ 听成 /kio/（齿龈同理，/to/ 会像 /tio/）。
# 这里只列 F2，其余沿用统一模板。
_VELAR_F2 = {
    "i": 2200, "I": 2100, "E": 1900, "{": 1750, "A": 1400, "O": 1050,
    "V": 1300, "U": 1100, "u": 1050, "3": 1500, "@": 1500,
    "aI": 1400, "eI": 1900, "aU": 1400, "OI": 1050, "oU": 1050,
}
_ALV_F2 = {
    "i": 1900, "I": 1800, "E": 1750, "{": 1700, "A": 1500, "O": 1250,
    "V": 1400, "U": 1150, "u": 1150, "3": 1600, "@": 1600,
    "aI": 1500, "eI": 1750, "aU": 1500, "OI": 1250, "oU": 1250,
}

VELAR_LOCUS = {v: [300.0, f2, 2300.0, 3300.0, 4000.0] for v, f2 in _VELAR_F2.items()}
ALVEOLAR_LOCUS = {v: [300.0, f2, 2500.0, 3300.0, 4000.0] for v, f2 in _ALV_F2.items()}

PLACE_LOCUS_BY_VOWEL = {
    "velar": VELAR_LOCUS,
    "alveolar": ALVEOLAR_LOCUS,
}

# 爆破噪声的带通范围（Hz），沿用中文表的取值思路：
# 齿龈最亮、软腭最紧凑、双唇最低。
PLACE_BURST = {
    "bilabial":     (450.0, 1300.0),
    "labiodental":  (600.0, 1800.0),
    "dental":       (1600.0, 3000.0),
    "alveolar":     (1800.0, 3200.0),
    "postalveolar": (1400.0, 2600.0),
    "velar":        (950.0, 2100.0),
}

# 鼻音共鸣腔
MURMUR = {
    "m": [250.0, 1100.0, 2300.0, 3300.0, 4000.0],
    "n": [250.0, 1700.0, 2600.0, 3400.0, 4000.0],
    "N": [250.0, 1990.0, 2400.0, 3300.0, 4000.0],
}

# 边音
LATERAL = [350.0, 1100.0, 2700.0, 3400.0, 4000.0]

# --------------------------------------------------------------------------
# 咝音的谱形：/s/ 与 /S/ 必须分开
# --------------------------------------------------------------------------
# /s/ 沿用中文表（文献 PMC4457315：最低谱峰 3.5~5kHz）。
# /S/（sh）整体下移一个倍频程附近：最低谱峰在 2~3kHz，这是它区别于 /s/
# 的唯一可靠线索 —— 两者用同一套谱形的话，混在一起就分不开。
SIB_S = dict(hp=3400.0, peaks=((4800.0, 1600.0), (6800.0, 1800.0), (8800.0, 2200.0)))
SIB_SH = dict(hp=2000.0, peaks=((2600.0, 1400.0), (3800.0, 1600.0), (5400.0, 1800.0)))

# --------------------------------------------------------------------------
# 辅音表
# --------------------------------------------------------------------------
# kind : plosive / nasal / lateral / fricative / affricate / approximant
# voicing : 浊辅音的浊音成分相对电平（清辅音不填）。
#           英语的浊擦音（v D z Z）是**浊音+摩擦**同时存在，不是纯噪声。
CONSONANTS = {
    "p": dict(kind="plosive", place="bilabial", aspirated=True,
              closure=60, burst=20, aspiration=55),
    "b": dict(kind="plosive", place="bilabial", aspirated=False,
              closure=50, burst=16, aspiration=12),
    "t": dict(kind="plosive", place="alveolar", aspirated=True,
              closure=55, burst=20, aspiration=60),
    "d": dict(kind="plosive", place="alveolar", aspirated=False,
              closure=45, burst=16, aspiration=12),
    "k": dict(kind="plosive", place="velar", aspirated=True,
              closure=60, burst=20, aspiration=65),
    "g": dict(kind="plosive", place="velar", aspirated=False,
              closure=50, burst=16, aspiration=14),

    "m": dict(kind="nasal", place="bilabial", murmur=75),
    "n": dict(kind="nasal", place="alveolar", murmur=75),
    "N": dict(kind="nasal", place="velar", murmur=80),

    "l": dict(kind="lateral", place="lateral", lateral=60),

    # 近音：稳态共振峰 + 滑向元音。r 的低 F3（约 1600Hz）是它最硬的听感线索。
    "r": dict(kind="approximant", F=[330.0, 1100.0, 1600.0, 3300.0, 4000.0],
              dur=65, gain=0.75, glide_gain=0.95),
    "w": dict(kind="approximant", F=[300.0, 610.0, 2150.0, 3300.0, 4000.0],
              dur=55, gain=0.75, glide_gain=0.95),
    "j": dict(kind="approximant", F=[280.0, 2200.0, 2950.0, 3400.0, 4000.0],
              dur=55, gain=0.75, glide_gain=0.95),

    # 擦音：noise="tract" 走声道滤波（f v T D h），"sib" 走咝音谱形（s z S Z）
    "f": dict(kind="fricative", place="labiodental", noise="tract", frication=90),
    "v": dict(kind="fricative", place="labiodental", noise="tract", frication=70,
              voicing=0.35),
    "T": dict(kind="fricative", place="dental", noise="tract", frication=90),
    "D": dict(kind="fricative", place="dental", noise="tract", frication=70,
              voicing=0.35),
    "s": dict(kind="fricative", place="alveolar", noise="sib", sib=SIB_S, frication=75),
    "z": dict(kind="fricative", place="alveolar", noise="sib", sib=SIB_S, frication=60,
              voicing=0.30),
    "S": dict(kind="fricative", place="postalveolar", noise="sib", sib=SIB_SH, frication=85),
    "Z": dict(kind="fricative", place="postalveolar", noise="sib", sib=SIB_SH, frication=65,
              voicing=0.30),
    "h": dict(kind="fricative", place="glottal", noise="tract", frication=80),

    # 塞擦音：闭塞 + 起爆 + 咝音摩擦
    "tS": dict(kind="affricate", place="postalveolar", sib=SIB_SH,
               closure=55, burst=16, frication=75),
    "dZ": dict(kind="affricate", place="postalveolar", sib=SIB_SH,
               closure=45, burst=14, frication=65, voicing=0.25),
}


def vc_initials():
    """VC 段需要的后继辅音。

    英语与中文不同：塞音的清浊（p/b、t/d、k/g）必须保留 —— 英语的浊塞音
    是真实的音位对立，不像中文 CVVC 那样可以在 VC 段合并。
    """
    return sorted(CONSONANTS)
