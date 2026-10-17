"""音节装配：把音素参数表变成波形，并回报段落边界供 oto.ini 使用。

三个入口
--------
render_vowel(v, f0)      独立元音
render_cv(c, v, f0)      辅音+元音（CVVC 的 CV 段）
render_vc(v, c, f0)      元音+辅音（CVVC 的 VC 过渡段）

统一的装配流程：
    段落计划 → 共振峰轨迹 → 激励包络 → 声道滤波 → 混入带通噪声 → 归一化
"""

from __future__ import annotations

import numpy as np

import dsp
import phonemes as ph
from config import (AMP_DRIFT_CORR_MS, AMP_DRIFT_STD, BANDWIDTH_SCALE,
                    BREATH_CORR_MS, BREATH_LEVEL, FORMANT_DRIFT,
                    FORMANT_DRIFT_CORR_MS, FORMANT_SCALE, FORMANT_SCALE_BY_INDEX, JITTER_CORR_MS,
                    JITTER_STD, PHASE_SEED, PEAK_CEILING, SHIMMER_CORR_MS,
                    SHIMMER_STD, SR, VOICED_RMS_DBFS, VOICED_SHELF_DB,
                    VOICED_SHELF_FC, VOICED_SHELF2_DB, VOICED_SHELF2_FC)
from config import (AIR_HP, AIR_LEVEL, AIR_LP, AIR_LP_ORDER, BYPASS_GAIN, PEAK_DB, PEAK_FC, PEAK_Q,
                    HARM_AIR_HP, HARM_AIR_LEVEL, HARM_AIR_LP, HARM_AIR_ORDER)


def _seg(dur, F, BW=None, voiced=0.0, noise_tract=0.0, noise_band=None,
         noise_order=2, glide=False, shape="flat", noise_lp=False,
         env=None, spill_n=0, noise_sib=0.0, rough=0.0, A=None,
         sib_hp=None, sib_peaks=None):
    """构造一个段落。

    dur         时长 ms
    F           本段共振峰目标（基准值，这里统一做女性化缩放）
    glide       True 时共振峰从上一段的目标线性滑到本段目标
    noise_band  (gain, (lo, hi)) —— 经带通后直接叠加到输出（不走声道滤波）
    noise_order 带通滤波器阶数
    shape       噪声包络形状：flat 平坦+首尾淡化 / decay 快起+指数衰减
    noise_lp    True 时 noise_tract 那一路先低通再进声道（爆破用）
    env         显式包络（形状，峰值 1），给出时覆盖 shape；允许长于本段，
                多出的部分会溢出到下一段，用来做噪声→浊音的交叉淡化
    spill_n     由 shape 生成的包络额外延伸的采样点数（同样用于交叉淡化）
    """
    # 女性化缩放集中在这里：元音、辅音 locus、鼻音、边音全部走同一条路，
    # 不会漏掉某一张表。带宽不跟着等比例放大，否则高频共振峰会过宽而糊掉。
    Fv = np.asarray(F, dtype=float)
    scale = np.resize(np.asarray(FORMANT_SCALE_BY_INDEX, dtype=float), Fv.shape)
    return dict(dur=float(dur),
                F=Fv * scale,
                BW=np.asarray(BW if BW is not None else ph.DEFAULT_BW,
                              dtype=float) * BANDWIDTH_SCALE,
                voiced=float(voiced), noise_tract=float(noise_tract),
                noise_band=noise_band, noise_order=noise_order,
                A=np.asarray(A if A is not None else ph.DEFAULT_A, dtype=float),
                glide=glide, shape=shape, noise_lp=noise_lp,
                env=env, spill_n=int(spill_n), noise_sib=float(noise_sib),
                rough=float(rough),
                sib_hp=sib_hp, sib_peaks=sib_peaks)


def _ms(n_ms):
    return max(1, int(round(n_ms / 1000.0 * SR)))


def _env_for(shape, n, spill_n=0):
    """噪声段落的包络。

    爆破不能用对称驼峰：那样峰值落在正中间，听起来是一声闷响而不是爆破。
    真实的爆破是瞬间起爆后迅速衰减，所以用 1.5ms 快起 + 指数衰减
    （段末约剩 2%）。
    """
    if shape == "decay":
        e = np.exp(-4.0 * np.arange(n) / max(n - 1, 1))
        a = min(n, _ms(1.5))
        e[:a] *= dsp.raised_cosine(a)
        return e
    if shape == "fric":
        # 擦音：起音要慢（8ms 太陡，听起来像突然出现），收尾交给 spill。
        f = min(n, _ms(ph.FRIC_ON_RAMP))
        e = np.ones(n + spill_n)
        if f > 1:
            e[:f] *= dsp.raised_cosine(f)
        if spill_n > 0:
            e[n:] *= dsp.raised_cosine(spill_n)[::-1]
        return e
    # flat：平坦，只做首尾短淡化；spill 段继续淡出，与下一段的浊音交叉
    f = min(n // 2, _ms(8))
    e = np.ones(n + spill_n)
    if f > 1:
        r = dsp.raised_cosine(f)
        e[:f] *= r
        # 有溢出段时不能再做段末淡出 —— 那会让包络在交界处先降到 0
        # 又跳回 1，留下一个凹口，正是 /s/ 听上去断开的原因
        if spill_n <= 0:
            e[n - f:n] *= r[::-1]
    if spill_n > 0:
        e[n:] *= dsp.raised_cosine(spill_n)[::-1]
    return e


def _release_env(n_total, n_burst, spill_n=0):
    """整个释放段的包络：起爆瞬态 + 送气，合成一条连续曲线（可溢出到下一段）。

    分成两段、各自带一次起音的话，听起来是两个独立事件 —— 先一下闷响，
    再一阵嘶声。真实的送气塞音是一条连续衰减：起爆瞬态随即转入送气噪声，
    中间没有台阶。所以这里让起爆衰减到平台电平（而不是衰减到零），
    送气从那个电平接着往下走，最后溢出一小段与浊音起始交叉淡化。
    """
    n_all = n_total + spill_n
    t = np.arange(n_all, dtype=float)
    a = max(1, _ms(ph.RELEASE_ATTACK_MS))
    tau = max(1.0, _ms(ph.RELEASE_TAU_MS))
    e = ph.RELEASE_PLATEAU + (1.0 - ph.RELEASE_PLATEAU) * np.exp(
        -np.maximum(t - a, 0.0) / tau)
    e[:a] *= dsp.raised_cosine(a)
    tail = np.clip((t - n_burst) / max(n_total - n_burst, 1.0), 0.0, 1.0)
    e *= 1.0 - (1.0 - ph.RELEASE_TAIL) * tail
    if spill_n > 0:
        e[n_total:] *= dsp.raised_cosine(spill_n)[::-1]
    return e


# ==========================================================================
# 装配核心
# ==========================================================================
def assemble(segments, f0, seed=PHASE_SEED, method=None, humanize=True):
    """把段落计划渲染成波形，返回 (waveform, bounds)。

    bounds 是各段落的采样点边界，长度 = 段落数 + 1。
    humanize=False 时关掉全部随机微扰，用于频谱测量与 oto.ini 调参 ——
    人性化会让声源带上 jitter，测量时拿未加扰动的声源做参考会对不上。
    """
    n_per = [_ms(s["dur"]) for s in segments]
    bounds = np.concatenate([[0], np.cumsum(n_per)]).astype(int)
    n = int(bounds[-1])
    n_formants = len(segments[0]["F"])

    # ---- 共振峰轨迹 ----
    track = np.zeros((n, n_formants, 3), dtype=float)
    prev_F = None
    for i, s in enumerate(segments):
        a, b = int(bounds[i]), int(bounds[i + 1])
        if s["glide"] and prev_F is not None:
            w = np.linspace(0.0, 1.0, b - a)[:, None]
            Fs = prev_F[None, :] * (1.0 - w) + s["F"][None, :] * w
        else:
            Fs = np.tile(s["F"], (b - a, 1))
        track[a:b, :, 0] = Fs
        track[a:b, :, 1] = s["BW"]
        track[a:b, :, 2] = s["A"]
        prev_F = s["F"]

    # ---- 音色漂移：每个共振峰独立地缓慢游走 ----
    # 乘一条慢速曲线而不是加常量偏移，这样共振峰之间的相对关系保持稳定，
    # 元音不会被漂移改掉音位。
    if humanize:
        for i in range(n_formants):
            d = dsp.slow_random(n, seed + 20 + i, FORMANT_DRIFT_CORR_MS)
            track[:, i, 0] *= 1.0 + d * FORMANT_DRIFT

    # ---- 激励包络 ----
    # 噪声段按各自的 shape 单独成形，所以这里不做全局首尾淡化，
    # 否则会把爆破的瞬间起爆抹成缓坡。
    env_voiced = np.zeros(n)
    env_tract = np.zeros(n)
    env_tract_lp = np.zeros(n)
    for i, s in enumerate(segments):
        a, b = int(bounds[i]), int(bounds[i + 1])
        env_voiced[a:b] = s["voiced"]
        if not s["noise_tract"]:
            continue
        env = s["env"]
        if env is None:
            env = _env_for(s["shape"], b - a, s["spill_n"])
        e = s["noise_tract"] * np.asarray(env, dtype=float)
        end = min(n, a + len(e))
        tgt = env_tract_lp if s["noise_lp"] else env_tract
        tgt[a:end] = np.maximum(tgt[a:end], e[:end - a])

    # ---- 音量起伏：shimmer（快）+ 自然渐弱渐强（慢）----
    if humanize:
        amp = (1.0
               + dsp.slow_random(n, seed + 12, SHIMMER_CORR_MS) * SHIMMER_STD
               + dsp.slow_random(n, seed + 13, AMP_DRIFT_CORR_MS) * AMP_DRIFT_STD)
        env_voiced *= amp

    env_voiced = dsp.apply_fades(env_voiced, env_voiced,
                                 ph.VOWEL_ON_RAMP, ph.FADE_OUT)

    # ---- 气声包络：跟着浊音走，但自己再缓慢起伏一次 ----
    if humanize:
        env_breath = (env_voiced * BREATH_LEVEL
                      * (1.0 + dsp.slow_random(n, seed + 31, BREATH_CORR_MS) * 0.4))
    else:
        env_breath = np.zeros(n)

    # ---- 浊音激励：f0 叠加微小音高不稳（jitter，非颤音）----
    if humanize:
        f0_curve = f0 * (1.0 + dsp.slow_random(n, seed + 11, JITTER_CORR_MS)
                         * JITTER_STD)
    else:
        f0_curve = None
    src = dsp.make_source(f0, n, method=method, seed=seed, f0_curve=f0_curve)

    # ---- 分两路滤波，保证噪声与浊音的相对电平可控 ----
    # 气声、送气、以及爆破的经声道成分都走这条：它们是在声门/阻碍处激发、
    # 被声道塑形的，走同一条路才会跟后面的元音融为一体。
    voiced_out = dsp.formant_cascade(src * env_voiced, track)
    # 旁路：留住被 5 级串联滤波器陡降掉的高频谐波
    voiced_out += BYPASS_GAIN * src * env_voiced
    # 共振峰之后再补一条高架，把存在感频段（2~8kHz）托起来
    voiced_out = dsp.peaking(voiced_out, PEAK_FC, PEAK_DB, PEAK_Q)
    voiced_out = dsp.high_shelf(voiced_out, VOICED_SHELF_FC, VOICED_SHELF_DB)
    voiced_out = dsp.high_shelf(voiced_out, VOICED_SHELF2_FC, VOICED_SHELF2_DB)

    # 基准：浊音段的 RMS。带通噪声与声道噪声都按这个基准定标
    ref = dsp.rms(voiced_out[env_voiced > 1e-6])
    if ref < 1e-9:
        ref = dsp.rms(voiced_out)

    # 经声道的噪声路径：**先滤波、再套包络**。
    #
    # 顺序反过来（先套包络再滤波）看着更物理，实际不能用：包络起伏比谐振器
    # 的建立时间还快时（爆破 20ms、送气 55ms，而 BW=80Hz 的谐振器要 12ms 建立），
    # 声道来不及给噪声上色，输出比标称低 12~15 dB。更麻烦的是这个损失随段落
    # 变化（实测送气 0.057、爆破 0.044、平坦的 /h/ 1.0），拿一个全局系数根本
    # 标不平，GAIN_* 就彻底失去意义。
    #
    # 先滤波则每次都是稳态响应，GAIN_* 严格等于「相对浊音段的电平」；
    # 代价是爆破也拿到了完整的声道着色 —— 而这恰好正是我们要的效果。
    #
    # 还要**逐点**归一化，不能用整段的 RMS：同一条串联谐振器在元音区的
    # 宽带增益（5 个高 Q 谐振器全开）比在辅音 locus 区高约 5 倍，只按
    # 整段归一化的话送气段实际电平只有标称的 1/5。
    def _noise_path(seed_i):
        y = dsp.formant_cascade(dsp.white(n, seed=seed_i), track)
        return y * (ref / np.maximum(dsp.local_rms(y), 1e-12))

    tract_out = _noise_path(seed + 1)
    # 爆破单独走一条低通支路：locus 上的 F4/F5 是给女声提亮用的，
    # 宽带噪声过它们会变成嘶声（实测 4~10kHz 只低 3.4dB）。
    tract_lp = dsp.lowpass(tract_out, ph.BURST_LP, order=ph.BURST_LP_ORDER)
    breath_out = _noise_path(seed + 30)

    # 空气感：高通后的噪声直接叠加，不经过声道滤波器
    air = dsp.highpass(dsp.white(n, seed=seed + 40), AIR_HP, order=2)
    air = dsp.lowpass(air, AIR_LP, order=AIR_LP_ORDER)
    ra = dsp.rms(air)
    if ra > 1e-12:
        air = air / ra * ref * AIR_LEVEL

    # 谐波空气：声源高通后直接叠加，同样绕过串联谐振器。
    # 与上面那条噪声空气互补 —— 噪声给「气息」，谐波给「光泽」。真实录音
    # 4kHz 以上两个成分都有；只放噪声会听成嘶声，只放谐波又会显得干。
    # 必须在 env_voiced 之内，否则辅音段也会漏出声源。
    harm_air = dsp.highpass(src, HARM_AIR_HP, order=HARM_AIR_ORDER)
    harm_air = dsp.lowpass(harm_air, HARM_AIR_LP, order=HARM_AIR_ORDER)
    rh = dsp.rms(harm_air[env_voiced > 1e-6]) if np.any(env_voiced > 1e-6) else 0.0
    if rh > 1e-12:
        harm_air = harm_air / rh * ref * HARM_AIR_LEVEL * env_voiced
    else:
        harm_air = np.zeros(n)

    out = (voiced_out
           + tract_out * env_tract
           + tract_lp * env_tract_lp
           + breath_out * env_breath
           + air * env_voiced
           + harm_air)

    # ---- 咝音（/s/）：谱形由高通 + 多个宽共振塑成，不走部位带通 ----
    for i, s in enumerate(segments):
        if not s["noise_sib"]:
            continue
        a, b = int(bounds[i]), int(bounds[i + 1])
        env = s["env"]
        if env is None:
            env = _env_for(s["shape"], b - a, s["spill_n"])
        env = np.asarray(env, dtype=float)
        length = min(len(env), n - a)
        if length <= 0:
            continue
        # 谱形可按段落覆盖：英语的 /S/ 必须比 /s/ 低一个倍频程附近，
        # 共用同一套谱形的话两者根本分不开。
        w = dsp.sibilant(dsp.white(length, seed=seed + 300 + i),
                         s["sib_peaks"] or ph.SIB_PEAKS,
                         s["sib_hp"] or ph.SIB_HP, ph.SIB_HP_ORDER)
        rw = dsp.rms(w)
        if rw > 1e-12:
            w /= rw
        # 湍流噪声不是恒定电平的，加一点慢速起伏，否则会听成「静电噪声」
        if s["rough"]:
            w *= 1.0 + s["rough"] * dsp.slow_random(
                length, seed + 400 + i, ph.SIB_ROUGH_CORR)
        out[a:a + length] += w * env[:length] * s["noise_sib"] * ref

    # ---- 带通噪声：爆破的部位线索 ----
    # 这部分刻意不走声道滤波器：爆破的紧凑频段和 /s/ 的高频集中，正是
    # 区分 g/k 与 d/t、区分 s 与 sh 的关键，经声道滤波反而会糊掉。
    for i, s in enumerate(segments):
        nb = s["noise_band"]
        if not nb:
            continue
        gain, (lo, hi) = nb
        a, b = int(bounds[i]), int(bounds[i + 1])
        env = s["env"]
        if env is None:
            env = _env_for(s["shape"], b - a, s["spill_n"])
        env = np.asarray(env, dtype=float)
        length = min(len(env), n - a)
        if length <= 0:
            continue
        w = dsp.bandpass(dsp.white(length, seed=seed + 100 + i), lo, hi,
                         order=s["noise_order"])
        rw = dsp.rms(w)
        if rw > 1e-12:
            w /= rw
        out[a:a + length] += w * env[:length] * gain * ref

    # 整段末尾再淡出一次，压掉滤波器余振
    n_out = min(_ms(ph.FADE_OUT), n)
    out[n - n_out:] *= dsp.raised_cosine(n_out)[::-1]

    out = dsp.normalize(out, ref, VOICED_RMS_DBFS, PEAK_CEILING)
    return out, bounds


# ==========================================================================
# 段落计划
# ==========================================================================
def _vowel_segments(v, lang=ph):
    V = lang.VOWELS[v]
    A = V.get("A")
    if "F2" not in V:
        return [
            _seg(ph.VOWEL_ON_RAMP, V["F"], V["BW"], voiced=1.0, A=A),
            _seg(ph.VOWEL_HOLD, V["F"], V["BW"], voiced=1.0, A=A),
            _seg(ph.VOWEL_TAIL, V["F"], V["BW"], voiced=1.0, A=A),
        ]
    # 双元音：前半段停在起点元音，后半段滑向终点。转折点由 DIPH_AT 控制 ——
    # 英语的双元音前段长、后段只是方向性的滑音，所以转折点放在偏后位置。
    hold = ph.VOWEL_HOLD * float(V.get("DIPH_AT", 0.45))
    back = ph.VOWEL_HOLD - hold + ph.VOWEL_TAIL
    return [
        _seg(ph.VOWEL_ON_RAMP, V["F"], V["BW"], voiced=1.0, A=A),
        _seg(hold, V["F"], V["BW"], voiced=1.0, A=A),
        _seg(back, V["F2"], V["BW"], voiced=1.0, glide=True, A=A),
    ]


def _locus(c, v, lang=ph):
    """辅音的共振峰轨迹起点。

    软腭音单独查 VELAR_LOCUS —— 它的 locus 随后接元音大幅变化，用固定值
    会让 /gu/ 听成 /du/、/ko/ 听成 /kio/。glottal 部位返回 None（沿用元音）。
    """
    C = lang.CONSONANTS[c]
    place = C.get("place")
    if place is None:          # 近音直接给自己的 F，没有部位 locus
        return None
    tbl = lang.PLACE_LOCUS_BY_VOWEL.get(place)
    if tbl is not None:
        return tbl[v]
    return lang.PLACE_LOCUS[place]


def _fric_seg(C, F, gain, spill_ms=None):
    """擦音段。

    gain 是相对浊音段 RMS 的噪声电平。浊擦音（英语的 v D z Z）同时带浊音
    成分 —— 真实的浊擦音是「声带振动 + 摩擦」并存，纯噪声听上去就是清擦音。
    """
    spill_n = _ms(ph.FF_SPILL if spill_ms is None else spill_ms)
    voiced = float(C.get("voicing", 0.0))
    sib = C.get("sib")
    if sib is None:
        return _seg(C["frication"], F, noise_tract=gain, shape="fric",
                    spill_n=spill_n, voiced=voiced)
    return _seg(C["frication"], F, noise_sib=gain, shape="fric",
                spill_n=spill_n, rough=ph.SIB_ROUGH, voiced=voiced,
                sib_hp=sib["hp"], sib_peaks=sib["peaks"])


def _release_segments(C, locus, F_fallback):
    """塞音的释放段：起爆 + 送气，共用一条连续包络。

    爆破拆成两部分，缺一不可：
      * 经声道的一份 —— 带上 locus 的共振峰色，听上去像从后面那个音里长出来的
      * 走部位带通的一份 —— 保留 g/k 与 d/t 的区分线索（齿龈爆破在高频、
        软腭爆破是中频紧凑的一团）

    两部分共用同一条包络，所以一起起爆、一起衰减，不会变成两个事件。
    """
    tgt = locus if locus is not None else F_fallback
    n_b = _ms(C["burst"])
    n_a = _ms(C["aspiration"])
    env = _release_env(n_b + n_a, n_b, _ms(ph.RELEASE_SPILL))
    # 带通要 4 阶：2 阶在 (1800, 3200) 的裙边会一直延伸到 4~6kHz，
    # 那正是爆破听上去「嘶」的来源。
    segs = [_seg(C["burst"], tgt,
                 noise_tract=ph.GAIN_RELEASE, noise_lp=True,
                 noise_band=(ph.GAIN_BURST, ph.PLACE_BURST[C["place"]]),
                 noise_order=C.get("noise_order", 4),
                 env=env[:n_b])]
    segs.append(_seg(C["aspiration"], tgt,
                     noise_tract=ph.GAIN_RELEASE, env=env[n_b:]))
    return segs


def _cv_segments(c, v, lang=ph):
    C = lang.CONSONANTS[c]
    V = lang.VOWELS[v]
    locus = _locus(c, v, lang)

    segs = []
    if C["kind"] == "plosive":
        segs.append(_seg(C["closure"], locus or V["F"], shape="flat"))  # 闭塞，静音
        segs.extend(_release_segments(C, locus, V["F"]))
        segs.append(_seg(ph.GLIDE, V["F"], V["BW"], voiced=1.0, glide=True))

    elif C["kind"] == "affricate":
        # 塞擦音 = 闭塞 + 起爆 + 咝音摩擦。摩擦段用咝音谱形，
        # 清浊由 voicing 决定（dZ 带浊音，tS 不带）。
        segs.append(_seg(C["closure"], locus or V["F"], shape="flat"))
        segs.append(_seg(C["burst"], locus or V["F"],
                         noise_band=(ph.GAIN_BURST, lang.PLACE_BURST[C["place"]]),
                         noise_order=4, shape="decay"))
        segs.append(_fric_seg(C, locus or V["F"], ph.GAIN_FRICATIVE_S))
        segs.append(_seg(ph.GLIDE, V["F"], V["BW"], voiced=1.0, glide=True))

    elif C["kind"] == "nasal":
        segs.append(_seg(C["murmur"], lang.MURMUR[c], voiced=ph.GAIN_MURMUR))
        segs.append(_seg(ph.GLIDE, V["F"], V["BW"],
                         voiced=ph.GAIN_NASAL_GLIDE, glide=True))

    elif C["kind"] == "lateral":
        segs.append(_seg(C["lateral"], lang.LATERAL, voiced=ph.GAIN_LATERAL))
        segs.append(_seg(ph.GLIDE, V["F"], V["BW"],
                         voiced=ph.GAIN_LATERAL_GLIDE, glide=True))

    elif C["kind"] == "approximant":
        # 近音（r w j）：稳态共振峰 + 滑向元音。与边音同理，只是共振峰
        # 来自辅音表自己的 F 字段。
        segs.append(_seg(C["dur"], C["F"], voiced=C["gain"]))
        segs.append(_seg(ph.GLIDE, V["F"], V["BW"],
                         voiced=C.get("glide_gain", 0.9), glide=True))

    elif C["kind"] == "fricative":
        segs.append(_fric_seg(C, locus or V["F"], ph.GAIN_FRICATIVE_S))
        segs.append(_seg(ph.GLIDE, V["F"], V["BW"], voiced=1.0, glide=True))

    # 元音主体
    segs.extend(_vowel_segments(v, lang))
    return segs


def _vc_segments(v, c, lang=ph):
    C = lang.CONSONANTS[c]
    V = lang.VOWELS[v]
    locus = _locus(c, v, lang)

    segs = [_seg(ph.VC_VOWEL, V["F"], V["BW"], voiced=1.0)]

    if C["kind"] == "plosive":
        segs.append(_seg(ph.VC_GLIDE, locus or V["F"], voiced=1.0, glide=True))
        segs.append(_seg(C["closure"], locus or V["F"], shape="flat"))  # 静音收尾

    elif C["kind"] == "affricate":
        segs.append(_seg(ph.VC_GLIDE, locus or V["F"], voiced=1.0, glide=True))
        segs.append(_seg(C["burst"], locus or V["F"],
                         noise_band=(ph.GAIN_BURST, lang.PLACE_BURST[C["place"]]),
                         noise_order=4, shape="decay"))
        segs.append(_fric_seg(C, locus or V["F"], ph.GAIN_FRICATIVE_VC))

    elif C["kind"] == "nasal":
        M = lang.MURMUR[c]
        segs.append(_seg(ph.VC_GLIDE, M, voiced=ph.GAIN_NASAL_GLIDE_VC, glide=True))
        segs.append(_seg(C["murmur"], M, voiced=ph.GAIN_MURMUR))

    elif C["kind"] == "lateral":
        segs.append(_seg(ph.VC_GLIDE, lang.LATERAL,
                         voiced=ph.GAIN_LATERAL_GLIDE_VC, glide=True))
        segs.append(_seg(C["lateral"], lang.LATERAL, voiced=ph.GAIN_LATERAL_VC))

    elif C["kind"] == "approximant":
        segs.append(_seg(ph.VC_GLIDE, C["F"], voiced=1.0, glide=True))
        segs.append(_seg(C["dur"], C["F"], voiced=C["gain"]))

    elif C["kind"] == "fricative":
        segs.append(_seg(ph.VC_GLIDE, locus or V["F"],
                         voiced=ph.GAIN_FRICATIVE_GLIDE_VC, glide=True))
        segs.append(_fric_seg(C, locus or V["F"], ph.GAIN_FRICATIVE_VC))

    return segs


# ==========================================================================
# 对外接口
# ==========================================================================
def render_vowel(v, f0, method=None, humanize=True, lang=ph):
    """独立元音。lang 传 english 则按英语表渲染（含双元音）。"""
    segs = _vowel_segments(v, lang)
    audio, bounds = assemble(segs, f0, seed=PHASE_SEED, method=method,
                             humanize=humanize)
    meta = dict(dur_ms=_total_ms(segs), vowel_ms=0.0, cons_ms=0.0,
                tail_ms=ph.VOWEL_TAIL)
    return audio, meta


def render_cv(c, v, f0, method=None, humanize=True, lang=ph):
    """CV 段：辅音 + 元音。元音起点 = 先行发声点。"""
    segs = _cv_segments(c, v, lang)
    audio, bounds = assemble(segs, f0, seed=PHASE_SEED + _hash(f"{c}{v}"),
                             method=method, humanize=humanize)
    cons_ms = sum(s["dur"] for s in segs[:-3])   # 末三段是元音
    meta = dict(dur_ms=_total_ms(segs), vowel_ms=cons_ms, cons_ms=cons_ms,
                tail_ms=ph.VOWEL_TAIL)
    return audio, meta


def render_vc(v, c, f0, method=None, humanize=True, lang=ph):
    """VC 段：元音 → 辅音，以辅音的成型态收尾。"""
    segs = _vc_segments(v, c, lang)
    audio, bounds = assemble(segs, f0, seed=PHASE_SEED + _hash(f"{v}_{c}"),
                             method=method, humanize=humanize)
    meta = dict(dur_ms=_total_ms(segs), vowel_ms=ph.VC_VOWEL,
                cons_ms=_total_ms(segs) - ph.VC_VOWEL, tail_ms=0.0)
    return audio, meta


# ==========================================================================
# 工具
# ==========================================================================
def _total_ms(segs):
    return float(sum(s["dur"] for s in segs))


def _hash(s):
    """稳定小整数，用于让每个音素有独立但可复现的噪声种子。"""
    h = 0
    for ch in s:
        h = (h * 131 + ord(ch)) & 0xFFFF
    return h


# ==========================================================================
# 快速试听：python render.py
# ==========================================================================
if __name__ == "__main__":
    F0_C4 = 261.6256
    print("渲染试听样例（C4）")
    for name, audio in [
        ("a", render_vowel("a", F0_C4)[0]),
        ("ba", render_cv("b", "a", F0_C4)[0]),
        ("pa", render_cv("p", "a", F0_C4)[0]),
        ("da", render_cv("d", "a", F0_C4)[0]),
        ("ga", render_cv("g", "a", F0_C4)[0]),
        ("gu", render_cv("g", "u", F0_C4)[0]),
        ("du", render_cv("d", "u", F0_C4)[0]),
        ("ko", render_cv("k", "o", F0_C4)[0]),
        ("sa", render_cv("s", "a", F0_C4)[0]),
        ("si", render_cv("s", "i", F0_C4)[0]),
        ("ma", render_cv("m", "a", F0_C4)[0]),
        ("la", render_cv("l", "a", F0_C4)[0]),
        ("a b", render_vc("a", "b", F0_C4)[0]),
    ]:
        dsp.write_wav(f"preview_{name.replace(' ', '_')}.wav", audio)
        print(f"  preview_{name.replace(' ', '_')}.wav  "
              f"{len(audio)/SR*1000:6.0f} ms  峰值 {np.abs(audio).max():.3f}")
