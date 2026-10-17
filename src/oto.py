"""oto.ini 生成。

格式
----
    wav文件名=别名,左边界,固定区长度,右边界,先行发声,重叠      （单位均为 ms）

参数含义（用本机真实声库 D:\\UTAU\\voice\\uta 的 148 条实证，见 ref/NOTES.md）
----------------------------------------------------------------------------
左边界 offset        : 采样在 wav 里从哪儿开始，切掉开头的头静音/噪声
固定区 fixed         : **从 offset 起算**的长度。固定区 = [offset, offset+fixed]，
                     这段不做时长拉伸，用来保住辅音与过渡
右边界 blank         : 从**文件末尾往前**量的距离，限制可用终点。本项目用负值，
                     与社区主流写法一致（默认音源用正值，疑按绝对值处理，
                     仍待 SetParam 目视确认）
先行发声 preutterance : 音符起点对齐到采样的哪个位置；它之前的部分作为前导，
                     会盖到上一个音符上做交叉淡化。**参考点是元音核心**，
                     不是整个辅音
重叠 overlap         : 与上一个音符的交叠长度

实证要点
--------
* 固定区是**从 offset 起算**的 —— 100% 的真实条目满足
  `offset+固定区 < 时长-右边界`；若改成从先行发声点起算，只剩 9% 成立
* 真实声库里**固定区长度恒大于先行发声**（100%）。本文件早期版本令两者
  相等，理由是「两种解释在采样起点重合时等价」—— 那个理由是错的，两者是
  互相独立的量。这里保留相等只是一个**自洽的特例**（固定区恰好覆盖到元音
  起点），并非通例

重要：数值取自合成脚本回报的段落边界（不是猜的），但仍需用 SetParam 按听感
微调（纲领 TODO 第 7 步）。
"""

# 右边界（cutoff）必须写**正值** —— 正值表示「距文件末尾的距离」。
#
# 符号会改变含义：正值是从末尾往前量，负值是从 offset 起算的长度。两者差别
# 极大 —— 写 -55 会变成「可用区只有 55ms 长」，于是所有固定区超过 55ms 的
# 采样（即除纯元音外的全部）都被整个吃掉，渲染出静音。
#
# 这个坑真实踩过一次：用 |cutoff| 做统计检验会把符号抹掉，从而得出「UTAU 按
# 绝对值处理」的错误结论。デフォ子与重音テト用的都是正值。
FADE_TRIM = 55    # 从文件末尾往前裁掉的收尾淡化长度 ms，同 phonemes.FADE_OUT

VOWEL_PU = 40     # 独立元音的先行发声 ms
VC_PU_RATIO = 1.0 # VC 的先行发声 = 采样内保留的元音长度


def params_for(kind, meta):
    """按采样类型给出 oto 参数。

    kind : 'vowel' | 'cv' | 'vc'
    meta : render 回报的段落边界信息（含 vowel_ms / cons_ms）
    """
    if kind == "vowel":
        return dict(offset=0.0, consonant=VOWEL_PU,
                    preutterance=VOWEL_PU, overlap=VOWEL_PU * 0.5,
                    cutoff=FADE_TRIM)

    if kind == "cv":
        # 固定区 = [0, 元音起点]，即整个辅音+过渡段都不被拉伸；先行发声点
        # 同时取元音起点，让元音核心落在音符上。两者相等在这里是自洽的特例
        # —— 真实声库里固定区恒大于先行发声，若日后要分开，改这里即可。
        pu = max(float(meta["vowel_ms"]), 30.0)
        return dict(offset=0.0, consonant=pu, preutterance=pu,
                    overlap=min(pu * 0.5, 60.0), cutoff=FADE_TRIM)

    # VC：采样开头那段元音是前导（与上一个音符交叠），所以先行发声取元音长度
    pu = max(float(meta["vowel_ms"]) * VC_PU_RATIO, 30.0)
    return dict(offset=0.0, consonant=pu, preutterance=pu,
                overlap=min(pu * 0.35, 45.0), cutoff=FADE_TRIM)


def format_line(filename, alias, p):
    return "%s=%s,%d,%d,%d,%d,%d" % (
        filename, alias,
        round(p["offset"]), round(p["consonant"]), round(p["cutoff"]),
        round(p["preutterance"]), round(p["overlap"]))


def write_oto(path, lines):
    """写 oto.ini。

    用 cp932（Shift-JIS）编码 —— 这是 UTAU 期望的编码。本声库的别名目前
    全是 ASCII（拼音 + 空格），两种编码下字节相同；统一成 cp932 是为了
    以后加中文别名时不会踩坑。行尾用 CRLF，同样是 UTAU 的习惯。
    """
    text = "\n".join(lines) + "\n"
    with open(path, "w", encoding="cp932", newline="\r\n") as f:
        f.write(text)
    return len(lines)
