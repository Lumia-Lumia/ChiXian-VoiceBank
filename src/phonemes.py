"""音素表与参数配置表（纲领 四 / 五）。

单位约定
--------
* 频率 Hz，带宽 Hz，时长 ms。
* 共振峰一律给 F1..F5 五个，带宽给 BW1..BW5。
* 这里填的是**基准值**（未做女性化缩放）。实际渲染时由 config.FORMANT_SCALE
  和 BANDWIDTH_SCALE 统一缩放，所以调整女声程度只需要改那两个数。
* 共振峰是**绝对频率**，不随 f0 变化 —— 这是避免变调「花栗鼠效应」的关键。

术语
----
locus   : 辅音的共振峰「轨迹起点」。辅音本身没有稳态共振峰，
          发元音时声道从 locus 滑向元音目标，这个滑动就是过渡段。
murmur  : 鼻音的鼻咽共鸣腔共振峰（含鼻腔反谐振造成的整体发闷）。
F5      : 4kHz 附近的高次共振峰，是「明亮度」的主要来源之一。
"""

# ==========================================================================
# 元音（普通话，常用文献值）
# ==========================================================================
# A 是并联共振峰的**幅度**。并联结构里它是显式参数（串联里由前级衰减
# 顺带决定、无法指定）。基准曲线取 A_i ∝ i^-0.35 附近，再按元音微调。
VOWELS = {
    "a": dict(F=[850, 1250, 2600, 3400, 4000], BW=[80, 110, 150, 200, 300],
              A=[1.00, 0.80, 0.55, 0.36, 0.30]),
    "o": dict(F=[520,  850, 2450, 3350, 4000], BW=[70,  95, 150, 200, 300],
              A=[1.00, 0.85, 0.60, 0.40, 0.33]),
    "e": dict(F=[530, 1250, 2500, 3400, 4000], BW=[75, 100, 150, 200, 300],
              A=[1.00, 0.82, 0.58, 0.38, 0.31]),
    # /i/ 的 F1 特意取得偏宽（120，比 F2 的 100 还宽）。
    # 原因：D#4 的基频 311Hz 正好落在 F1（约 366Hz）的带内，窄 F1 会让 h1 独吞
    # 全部共振增益 —— 实测 h2 比 h1 低 27dB，而参考只有 12dB，整个 F2 区被压暗。
    # 把 F1 抬到 300（×1.22=366）、带宽放宽到 120（×1.35=162），h2 抬高约 10dB，
    # 700~4000Hz 各频带随之提升 5~7dB。再宽就会听不出是 /i/ 了。
    "i": dict(F=[300, 2350, 3000, 3600, 4200], BW=[120, 100, 160, 200, 300],
              A=[1.00, 0.75, 0.60, 0.45, 0.38]),
    "u": dict(F=[330,  760, 2300, 3350, 4000], BW=[65,  90, 150, 200, 300],
              A=[1.00, 0.88, 0.62, 0.42, 0.35]),
    # ---- 以下五个是韵母扩展用的音色目标 ----
    # ü [y]：圆唇前高，F2 比 /i/ 低一档。
    "v": dict(F=[300, 2100, 2700, 3600, 4200], BW=[70, 100, 160, 200, 300],
              A=[1.00, 0.75, 0.60, 0.45, 0.38]),
    # ɛ：ie / üe / ian 的韵腹，比 /e/ 更低更前。
    "E": dict(F=[550, 1900, 2600, 3400, 4000], BW=[80, 110, 150, 200, 300],
              A=[1.00, 0.80, 0.55, 0.36, 0.30]),
    # ɿ（zi / ci / si 的韵母）：舌尖前，F2 被舌尖挡住。
    "i0": dict(F=[380, 1400, 2900, 3500, 4200], BW=[80, 110, 160, 200, 300],
               A=[1.00, 0.80, 0.58, 0.38, 0.31]),
    # ʅ（zhi / chi / shi / ri 的韵母）：舌尖后，F3 压到 1900 是卷舌的听感线索。
    "ir": dict(F=[380, 1300, 1900, 3500, 4200], BW=[80, 110, 160, 200, 300],
               A=[1.00, 0.80, 0.58, 0.38, 0.31]),
    # ɚ（er）：卷舌央元音，F3 压到 1650。
    "er": dict(F=[500, 1350, 1650, 3400, 4000], BW=[90, 120, 160, 200, 300],
               A=[1.00, 0.80, 0.58, 0.38, 0.31]),
}

# ==========================================================================
# 韵母（普通话 37 个）
# ==========================================================================
# 每个韵母按传统三分：**韵头**（介音）/ **韵腹**（主要元音）/ **韵尾**。
# 韵腹撑住整个长音，韵头只在起音处滑一下，韵尾在收尾前滑出去 —— 这个顺序
# 决定 UTAU 拉长音符时听到的是元音本体，而不是被拉长的滑音。
#
#     on      [(音色, 时长ms), ...]  韵头
#     nucleus  音色                  韵腹
#     off     [(音色, 时长ms), ...]  韵尾（滑音）
#     coda    "n" / "ng" / None      鼻尾
#
# 音色指向 VOWELS；鼻尾指向 MURMUR。
FINALS = {
    "a":   dict(nucleus="a"),
    "o":   dict(nucleus="o"),
    "e":   dict(nucleus="e"),
    "ai":  dict(nucleus="a", off=[("i", 130)]),
    "ei":  dict(nucleus="e", off=[("i", 130)]),
    "ao":  dict(nucleus="a", off=[("u", 130)]),
    "ou":  dict(nucleus="o", off=[("u", 130)]),
    "an":  dict(nucleus="a", coda="n"),
    "en":  dict(nucleus="e", coda="n"),
    "ang": dict(nucleus="a", coda="ng"),
    "eng": dict(nucleus="e", coda="ng"),
    "ong": dict(nucleus="u", coda="ng"),
    "er":  dict(nucleus="er"),
    "i":   dict(nucleus="i"),
    "io":  dict(on=[("i", 55)], nucleus="o"),       # 哟 yo（罕见）
    "ia":  dict(on=[("i", 60)], nucleus="a"),
    "ie":  dict(on=[("i", 60)], nucleus="E"),
    "iao": dict(on=[("i", 60)], nucleus="a", off=[("u", 130)]),
    "iou": dict(on=[("i", 60)], nucleus="o", off=[("u", 130)]),
    "ian": dict(on=[("i", 55)], nucleus="E", coda="n"),
    "in":  dict(nucleus="i", coda="n"),
    "iang": dict(on=[("i", 60)], nucleus="a", coda="ng"),
    "ing": dict(nucleus="i", coda="ng"),
    "iong": dict(on=[("i", 55)], nucleus="u", coda="ng"),
    "u":   dict(nucleus="u"),
    "ua":  dict(on=[("u", 60)], nucleus="a"),
    "uo":  dict(on=[("u", 60)], nucleus="o"),
    "uai": dict(on=[("u", 60)], nucleus="a", off=[("i", 120)]),
    "uei": dict(on=[("u", 60)], nucleus="e", off=[("i", 120)]),
    "uan": dict(on=[("u", 60)], nucleus="a", coda="n"),
    "uen": dict(on=[("u", 60)], nucleus="e", coda="n"),
    "uang": dict(on=[("u", 60)], nucleus="a", coda="ng"),
    "ueng": dict(on=[("u", 60)], nucleus="e", coda="ng"),
    "v":   dict(nucleus="v"),
    # üe **不是「介音 ü + 韵腹 ɛ」，也不是「韵腹 ü + 短韵尾 ɛ」** ——
    # 它整条就是一次从 ü 到 ɛ 的滑行：两端都不停留，全部时间用于过渡。
    # glide_all 让韵腹段和收尾段合起来整段插值，curve=1.0 是匀速。
    "ve":  dict(nucleus="v", off=[("E", 0)], glide_all=True, curve=0.65),
    # üan 跟着 üe 走：韵腹是 ü，整条滑向 ɛ，ɛ 只是滑行的终点，之后接鼻尾。
    # （旧模型是「介音 ü + 韵腹 ɛ + 鼻尾」，ü 只有 55ms。）
    "van": dict(nucleus="v", off=[("E", 0)], coda="n",
                glide_all=True, curve=0.65),
    "vn":  dict(nucleus="v", coda="n"),
    "i0":  dict(nucleus="i0"),
    "ir":  dict(nucleus="ir"),
}

# 韵头 / 韵尾 / 鼻尾的时长都在上面逐条给了；鼻尾统一用这个长度。
CODA_MS = 80

# 韵尾滑音的分配曲线。长音里不能「撑满 680ms 再花 130ms 滑过去」——那样
# 前半段完全是韵腹，听感是一个静止的 a 突然变成 ai。真实的长音是**整段都在
# 慢慢往韵尾走，越靠尾部越快**，所以进度取 u^p（p>1 = 前慢后快），并拆成
# 若干段用折线逼近曲线（引擎段间是线性插值）。
FIN_GLIDE_CURVE = 2.0
FIN_GLIDE_STEPS = 8
# 滑音占韵腹的多大比例。1.0 = 整段都在走；0.6 = 前 40% 保持韵腹、后 60% 才走。
# 0.87 是 demo/27 四档试听后选的（100 / 87 / 73 / 60）。
FIN_GLIDE_SPAN = 0.87

# 韵头滑到韵腹的过渡时长（ms）。None = 用 FINALS 里逐条给的值。
# 注意这只是**过渡段**，前面还有 VOWEL_ON_RAMP（30ms）的静止起音。
FIN_ON_MS = None

# 辅音段用缺省幅度曲线
DEFAULT_A = [1.00, 0.80, 0.55, 0.36, 0.30]

# 缺省带宽，用于辅音段
DEFAULT_BW = [80, 110, 150, 200, 300]

# ==========================================================================
# 辅音部位参数
# ==========================================================================
# 各部位的共振峰轨迹起点（Hz）。glottal 为 None 表示「无声腔阻碍」，
# 直接沿用后接元音的共振峰（/h/ 就是这样）。
# F5 基本不参与过渡，各部位统一给 4000 即可。
PLACE_LOCUS = {
    "bilabial": [300,  800, 2200, 3300, 4000],   # 双唇 b p m
    "alveolar": [320, 1700, 2600, 3400, 4000],   # 齿龈 d t n s z c
    "lateral":  [350, 1100, 2700, 3400, 4000],   # 边音 l（F2 明显偏低）
    "glottal":  None,                            # 声门 h
    "labiodental": [300, 1200, 2400, 3300, 4000],  # 唇齿 f
    "retroflex":   [350, 1300, 1900, 3300, 4000],  # 卷舌 zh ch sh r（F3 压低）
    "palatal":     [300, 2000, 2800, 3400, 4000],  # 舌面 j q x
}

# 软腭音的 locus 必须随后接元音变化 —— 软腭是协同发音最强的部位。
# 这是把 /g/ /k/ 与 /d/ /t/ 区分开的**主要**线索：
#
#     /gu/   F2 从 1050 滑到 760   —— 几乎不动
#     /du/   F2 从 1700 滑到 760   —— 大幅下落
#
# 反过来，如果给软腭一个固定的高 F2（比如 1900），那么 /ko/ 的 F2
# 会从 1900 一路扫到 850，中途经过 ~1400 的 /e/ 频段，听起来就多出一个
# 介音，变成「kio」。F3 压低到 2300~2500 与 F2 靠拢，形成软腭音的
# 「捏合」特征。
VELAR_LOCUS = {
    "a": [300, 1600, 2300, 3300, 4000],
    "o": [300, 1100, 2300, 3300, 4000],
    "e": [300, 1900, 2400, 3300, 4000],
    "i": [300, 2200, 2500, 3300, 4000],
    "u": [300, 1050, 2300, 3300, 4000],
}

# 齿龈音的 locus 同样要随元音变。原来给固定值 F2=1700，经 FORMANT_SCALE
# 缩放后是 2074Hz —— 已经落在 /e/~/i/ 的区间，所以 F2 从 2074 扫向 /u/ 的
# 927 时，起点就带着「前」的音色，听起来多一个介音（to 像 tio、tu 像 tiu）。
# 这和当初 /ko/ 听成 /kio/ 是同一个病，只是当时只修了软腭。
ALVEOLAR_LOCUS = {
    "a": [320, 1700, 2600, 3400, 4000],
    "e": [320, 1750, 2600, 3400, 4000],
    "i": [320, 1900, 2700, 3400, 4000],
    "o": [320, 1250, 2500, 3300, 4000],
    "u": [320, 1150, 2400, 3300, 4000],
}

# 哪些部位的 locus 要逐元音查表（其余部位用 PLACE_LOCUS 的固定值）
PLACE_LOCUS_BY_VOWEL = {
    "velar":    VELAR_LOCUS,
    "alveolar": ALVEOLAR_LOCUS,
}

# 爆破噪声的带通范围（Hz）。三个部位要分得开，软腭 / 齿龈的落差尤其重要：
# 齿龈爆破偏高频，软腭爆破是低频紧凑的一团。
#
# 齿龈的上限不能给到 9k：那样带通单独通过 6ms 白噪时谱质心是 6442Hz，峰值
# 落在 6.6kHz —— 听感是一段高频嘶声而不是爆破（demo/20~23 实证）。收到
# 8500 后质心 6229Hz，与 Teto 的齿龈爆破（质心约 2kHz、能量压在 1kHz 以下
# 再滚降）仍偏亮，但用户实听后选的是这一档，再往下降就「超级过度」了。
PLACE_BURST = {
    "bilabial": (450.0, 1050.0),
    "alveolar": (3400.0, 8500.0),
    "velar":    (1500.0, 2700.0),
    # 塞擦音（z c zh ch j q）复用这三档。卷舌与舌面比齿龈低一档：
    # 阻塞点越往后，前腔越长、共振越低。
    "retroflex": (1800.0, 4000.0),
    "palatal":   (2500.0, 5500.0),
}

# 咝音谱形（hp=高通截止 Hz，peaks=(中心, 带宽)）。
# s / z / c 用 SIB_S，sh / zh / ch 用 SIB_SH。
# x / j / q 是舌面前音 [ɕ]，能量介于 [s] 与 [ʃ] 之间。
SIB_S = dict(hp=3400.0, peaks=((4800.0, 1600.0), (6800.0, 1800.0), (8800.0, 2200.0)))
SIB_SH = dict(hp=2000.0, peaks=((2600.0, 1400.0), (3800.0, 1600.0), (5400.0, 1800.0)))
SIB_X = dict(hp=2500.0, peaks=((3400.0, 1500.0), (4800.0, 1700.0), (6600.0, 2000.0)))

# /s/ 的谱形。
# 单纯用窄带通滤白噪会得到「哨音 / 静电噪声」的听感 —— 带限白噪的谱太平、
# 太窄。真实 /s/ 是前腔几个宽共振叠出来的，谱上有明显的峰谷起伏，所以要
# 用「陡峭高通 + 几个宽共振」去塑形，而不是一段窄带通。
SIB_HP = 3400.0                        # 高通截止 Hz，挡住 /ʃ/ 频段
SIB_HP_ORDER = 4
# 目标谱的依据：文献 (PMC4457315) 总结 /s/ 在成人里「最低的谱峰在 3.5~5kHz，
# 大部分声能集中在 4kHz 以上」。原先把高通放在 3.9kHz、峰放在 5.4/7.5/9.6k，
# 能量重心跑到 6~8kHz，听感偏「高频嘶声 / 哨音」而不是 /s/。
SIB_PEAKS = ((4800, 1600), (6800, 1800), (8800, 2200))   # (中心, 带宽)
SIB_ROUGH = 0.22                       # 幅度起伏深度（湍流噪声不是恒定的）
SIB_ROUGH_CORR = 16.0                  # 起伏相关长度 ms

# 爆破经声道那一路的低通截止（Hz）。必须低通，不能直接喂宽带白噪：locus 上
# 有一条 F4(4148Hz) 和一条给女声明亮度的 F5(4880Hz)，宽带噪声过这两条高 Q
# 谐振器会被抬得很亮，把爆破变成嘶声。
BURST_LP = 8000.0
BURST_LP_ORDER = 4

# 鼻音共鸣腔共振峰（Hz）
# ng 是软腭鼻尾（ang / eng / ong / iang / ing / iong / uang / ueng 的韵尾），
# 比 n 更闷：F2 压到 1000，是它与 n 唯一可靠的听感差别。
MURMUR = {
    "m":  [250, 1100, 2300, 3300, 4000],
    "n":  [250, 1700, 2600, 3400, 4000],
    "ng": [250, 1000, 2300, 3300, 4000],
}

# 边音稳态共振峰（Hz）
LATERAL = [350, 1100, 2700, 3400, 4000]

# ==========================================================================
# 辅音表
# ==========================================================================
# kind       : plosive 塞音 / nasal 鼻音 / lateral 边音 / fricative 擦音
# place      : 对应 PLACE_LOCUS / VELAR_LOCUS / PLACE_BURST 的键
# voiced     : 是否浊音（本批普通话声母均为清音，鼻音/边音按响音处理）
# aspirated  : 是否送气（p t k 送气，b d g 不送气）
# closure    : 闭塞段时长 ms（全静音）
# burst      : 释放段的包络长度 ms（快起 + 指数衰减，真正的爆破只占前几毫秒）
# aspiration : 送气噪声时长 ms
# murmur     : 鼻音段时长 ms
# lateral    : 边音段时长 ms
# frication  : 擦音段时长 ms
# noise      : 'tract' 表示噪声经声道共振峰滤波；否则为 (lo, hi) 带通范围
# burst_scale: 起爆各成分的逐辅音电平倍率（默认 1.0）。送气音后面有 20ms
#              噪声托着，不送气音的起爆是孤立的，所以 d/g 压到 0.56（−5dB）
# thump_scale: 低频冲击的逐辅音倍率（默认 1.0）。d 用 0.3、g 用 0.5 ——
#              两者是分开试听后分别定的（demo/21）
CONSONANTS = {
    # b 的起爆比其他不送气音长一倍（12ms）。普通话 b 不送气，辅音段只有
    # 26ms，若起爆也取 6ms 就只剩一个听不清的瞬态；实测 12ms 才听得清。
    # d/g 加长会显得刻意，所以只有 b 用 12ms。
    "b": dict(kind="plosive", place="bilabial", voiced=False, aspirated=False,
              closure=50, burst=12, aspiration=6),
    "p": dict(kind="plosive", place="bilabial", voiced=False, aspirated=True,
              closure=60, burst=6, aspiration=20),
    "m": dict(kind="nasal",   place="bilabial", voiced=True,
              murmur=75),
    # d 的起爆只有 4ms（demo/24）：再短就把部位线索一起削掉了，6ms 又偏长。
    # 起爆段同时也是低频冲击的渲染窗口，缩短它会连冲击一起截短。
    "d": dict(kind="plosive", place="alveolar", voiced=False, aspirated=False,
              closure=45, burst=4, aspiration=6,
              burst_scale=0.56, thump_scale=0.3),
    "t": dict(kind="plosive", place="alveolar", voiced=False, aspirated=True,
              closure=55, burst=6, aspiration=20),
    "n": dict(kind="nasal",   place="alveolar", voiced=True,
              murmur=75),
    "l": dict(kind="lateral", place="lateral",  voiced=True,
              lateral=60),
    "g": dict(kind="plosive", place="velar",    voiced=False, aspirated=False,
              closure=50, burst=6, aspiration=6,
              burst_scale=0.56, thump_scale=0.5),
    "k": dict(kind="plosive", place="velar",    voiced=False, aspirated=True,
              closure=60, burst=6, aspiration=20),
    "h": dict(kind="fricative", place="glottal", voiced=False,
              frication=90, noise="tract"),
    # /s/ 是高频咝音：能量集中在 5kHz 以上。带宽取得低或滤波器阶数不够时，
    # 2~3kHz 会漏出可听能量 —— 那正是 /ʃ/（sh）的频段，听起来就变成 sh。
    "s": dict(kind="fricative", place="alveolar", voiced=False,
              frication=65, noise="sibilant"),
    # ---- 第二批声母：补齐普通话声母表 ----
    # f 是唇齿擦音，走声道滤波（没有咝音的强谱峰）。
    "f": dict(kind="fricative", place="labiodental", voiced=False,
              frication=90, noise="tract"),
    # 塞擦音 = 闭塞 + 起爆 + 咝音摩擦。不送气的摩擦段短，送气的长一倍。
    "z": dict(kind="affricate", place="alveolar", voiced=False, aspirated=False,
              closure=45, burst=6, frication=50, sib=SIB_S),
    "c": dict(kind="affricate", place="alveolar", voiced=False, aspirated=True,
              closure=50, burst=6, frication=85, sib=SIB_S),
    "zh": dict(kind="affricate", place="retroflex", voiced=False, aspirated=False,
               closure=45, burst=6, frication=50, sib=SIB_SH),
    "ch": dict(kind="affricate", place="retroflex", voiced=False, aspirated=True,
               closure=50, burst=6, frication=85, sib=SIB_SH),
    "sh": dict(kind="fricative", place="retroflex", voiced=False,
               frication=80, sib=SIB_SH),
    # r 是卷舌近音。它不阻塞气流，所以是近音而不是擦音；F3 压到 1700 是
    # 卷舌最硬的听感线索，与 er 的低 F3 同源。
    "r": dict(kind="approximant", F=[350.0, 1300.0, 1700.0, 3300.0, 4000.0],
              dur=65, gain=0.72, glide_gain=0.95),
    # j q x 是舌面前音 [tɕ] [tɕʰ] [ɕ]，阻塞点在齿龈之后、硬腭之前。
    "j": dict(kind="affricate", place="palatal", voiced=False, aspirated=False,
              closure=45, burst=6, frication=50, sib=SIB_X),
    "q": dict(kind="affricate", place="palatal", voiced=False, aspirated=True,
              closure=50, burst=6, frication=85, sib=SIB_X),
    "x": dict(kind="fricative", place="palatal", voiced=False,
              frication=80, sib=SIB_X),
}

# ==========================================================================
# VC 段的后继辅音
# ==========================================================================
# 中文 CVVC 规范：VC 段实际不包含成阻（闭塞），所以不送气的 b/d/g 与送气的
# p/t/k 在 VC 里无法区分，统一用送气形式。
#
#     「由于爆破音的VC中实际不包含辅音，因此以送气爆破音替代不送气爆破音」
#                                    —— mandarin-reclist / simplification.md
#
# 在 oto_NanoVC.ini 里可以直接验证：_ba_pa_ma_fa_da_ta_na_la 那条线的 VC
# 只有 a p / a m / a f / a t / a n / a l，既没有 a b 也没有 a d。
#
# 结果是 VC 侧的后继辅音从 11 类减到 8 类（p m t n l k h s）。
VC_INITIAL = {"b": "p", "d": "t", "g": "k"}


def vc_initials():
    """VC 段实际需要录制的后继辅音（去重后的送气形式）。"""
    return sorted({VC_INITIAL.get(c, c) for c in CONSONANTS})


# ==========================================================================
# 时长与电平
# ==========================================================================
VOWEL_ON_RAMP = 30      # 起音斜坡 ms
VOWEL_HOLD = 680        # 稳态 ms
VOWEL_TAIL = 100        # 收尾衰减 ms
FADE_OUT = 55           # 文件末尾淡化 ms

GLIDE = 32              # 辅音→元音的共振峰过渡时长 ms
# 塞音的过渡单独给 —— 实测参考的辅音段只有 6~46ms，用 32ms 的过渡会把
# 整个辅音拖长一倍。鼻音/边音/擦音不受影响。
PLOSIVE_GLIDE = 14

VC_VOWEL = 120          # VC 采样里保留的元音长度 ms
VC_GLIDE = 55           # 元音滑向辅音目标的时长 ms

# 各激励的相对增益（相对浊音段 RMS）
GAIN_MURMUR = 0.55
GAIN_NASAL_GLIDE = 0.80
GAIN_LATERAL = 0.70
GAIN_LATERAL_GLIDE = 0.90
GAIN_NASAL_GLIDE_VC = 0.75
GAIN_LATERAL_GLIDE_VC = 0.75
GAIN_LATERAL_VC = 0.60
# 塞音释放段（起爆 + 送气）共用一条连续包络，也共用一个总增益。
# 拆成两个增益的话，交界处必然出现台阶：起爆衰减到零、送气又从零重新起音，
# 听感上是两个独立事件（先闷响、再嘶声），而不是一次塞音释放。
# 辅音段总增益：同时缩放起爆脉冲、部位带通、经声道噪声与低频冲击。
# 单独调其中任何一个都改不动整体 —— 实测送气对辅音能量只贡献 0.1dB。
CONSONANT_GAIN = 1.15
GAIN_RELEASE = 0.32      # 释放段整体的经声道成分
GAIN_BURST = 0.25        # 起爆的部位带通（不走声道，保留部位线索）
# 起爆的瞬态脉冲：闭合突然释放，激励声道让它按共振峰振铃。
# 这一条是「像不像人」的关键 —— 纯滤波噪声无论怎么调频段都像合成器效果音。
GAIN_CLICK = 0.25
# 起爆脉冲的衰减时间常数 ms。越长，低频越足；越短，越像「嗒」。
CLICK_TAU_MS = 0.3
# 释放瞬间的低频冲击（不经过声道）。0 = 关。
# 参考声库的辅音段在 300Hz 以下是最强的一档（Kumi /pa/ 是 -5.0dB），
# 而脉冲经共振峰滤波器后低频被 F1 挡住，实测我们只有 -14.7dB。
THUMP_GAIN = 1.5
THUMP_FC = 250.0
THUMP_TAU_MS = 12.0
RELEASE_PLATEAU = 0.50   # 起爆衰减到的平台电平（= 送气的起始电平）
RELEASE_TAIL = 0.08      # 送气段末衰减到的比例（再由元音起音接上）

# 3. 送气对后接元音起始 F0 的抬升（比例）与回落时间常数。
# 实测重音テト：送气组 F0 起点比稳态高 +8.8/+10.9/+13.7Hz（pa/ta/ka），
# 不送气组只有 +1.9/+4.4/+4.4Hz（ba/da/ga）。这是送气送出的气流使声带
# 张力上升造成的，也是音调语言里辅音影响声调起点的那条线索。
ASP_F0_BOOST = 0.035
ASP_F0_TAU_MS = 60.0
RELEASE_SPILL = 45.0     # 释放段溢出到浊音段的长度 ms（做交叉淡化）
RELEASE_ATTACK_MS = 1.5  # 释放段起音时长 ms（起爆是瞬态，不能缓起）
RELEASE_TAU_MS = 3.5     # 起爆瞬态的衰减时间常数 ms

GAIN_FRICATIVE_S = 0.24  # /s/ 咝音
GAIN_FRICATIVE_H = 0.35  # /h/ 经声道噪声
GAIN_FRICATIVE_VC = 0.45
GAIN_FRICATIVE_GLIDE_VC = 0.60
FF_SPILL = 22.0          # 擦音溢出到浊音段的长度 ms
FRIC_ON_RAMP = 30.0      # 擦音起音时长 ms（擦音是逐渐逼近成阻位置，起音不该太陡）

# 以上 GAIN_* 都是「相对浊音段 RMS 的电平」—— 经声道的那几条已经做过
# 逐点路径归一化（见 render.assemble），可以直接按 20·log10(值) 换算。
