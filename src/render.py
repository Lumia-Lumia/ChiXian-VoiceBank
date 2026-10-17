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


# 经声道噪声的谱倾斜（dB/倍频程）与幅度起伏深度。白噪 = 0 / 0。
# 真实气流噪声往高频掉、幅度起伏，见 dsp.tilted_noise 的说明。
NOISE_TILT = 0.0
NOISE_ROUGH = 0.35
# 不用白噪，改用「声门源相位随机化」得到的噪声：
# 谱形跟声门源一致（倾斜、随音高变化），但完全没有周期性。
# demo/18 在定稿参数下 A/B 后选定（白噪的辅音段低频更足但整体偏亮，这个更「气」）。
NOISE_FROM_SOURCE = True

# 鼻尾的目标共振峰与带宽，按 "n" / "ng" 分别覆盖。
# 空 dict = 用 lang.MURMUR[coda] + phonemes.DEFAULT_BW。
# 留出这个开关是因为实测我们的鼻音谱太暗：1400Hz 以上比参考低 20dB 以上，
# 听感是一团低频嗡鸣而不是 n。实验（demo/26）可以临时换成更宽带宽的一组。
# **必须按 n/ng 分开给**：两者唯一可靠的差别就是 F2（1700 vs 1000），
# 用一个共用的「亮鼻」会把 an 和 ang 变成同一个音。
# 实测（demo/26）：「亮鼻尾」通过了试听。旧值（MURMUR 原值 + 默认带宽）让
# 鼻尾在 800Hz 以上比参考低 20dB 以上，是一团低频嗡鸣。
CODA_F = {
    "n":  [400.0, 1600.0, 2500.0, 3400.0, 4000.0],
    "ng": [400.0, 1000.0, 2200.0, 3300.0, 4000.0],
}
CODA_BW = {
    "n":  [280.0, 250.0, 200.0, 220.0, 300.0],
    "ng": [280.0, 260.0, 200.0, 220.0, 300.0],
}


def _seg(dur, F, BW=None, voiced=0.0, noise_tract=0.0, noise_band=None,
         noise_order=2, glide=False, shape="flat", noise_lp=False,
         env=None, spill_n=0, noise_sib=0.0, rough=0.0, A=None,
         sib_hp=None, sib_peaks=None, click=0.0, thump_scale=1.0,
         f0_boost=0.0, vowel=False):
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
                rough=float(rough), click=float(click),
                thump_scale=float(thump_scale), f0_boost=float(f0_boost),
                vowel=bool(vowel),
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

    # ---- 送气对后接元音 F0 的抬升 ----
    # 实测参考声库：送气塞音后的元音起始 F0 高 9~14Hz，约 100ms 内回落。
    # 不送气塞音只有 2~4Hz。这条线索在音调语言里很重要。
    f0mul = np.ones(n)
    for i, s in enumerate(segments):
        if not s["f0_boost"]:
            continue
        a0 = int(bounds[i])
        t = np.arange(n - a0) / SR
        f0mul[a0:] = np.maximum(
            f0mul[a0:], 1.0 + s["f0_boost"] * np.exp(-t / (ph.ASP_F0_TAU_MS / 1000.0)))

    # ---- 浊音激励：f0 叠加微小音高不稳（jitter，非颤音）----
    if humanize:
        f0_curve = f0 * (1.0 + dsp.slow_random(n, seed + 11, JITTER_CORR_MS)
                         * JITTER_STD)
    else:
        f0_curve = None
    if humanize and f0_curve is not None:
        f0_curve = f0_curve * f0mul
    elif np.any(f0mul != 1.0):
        f0_curve = f0 * f0mul
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
        if NOISE_FROM_SOURCE:
            nz = dsp.random_phase(src, seed_i)
        else:
            nz = dsp.tilted_noise(n, seed=seed_i, slope_db_oct=NOISE_TILT)
        if NOISE_ROUGH:
            # 湍流不是稳态的：幅度要有起伏，否则听成一条「嘶——」的电子噪声
            nz = nz * (1.0 + NOISE_ROUGH * dsp.slow_random(n, seed_i + 77, 25.0))
        y = dsp.formant_cascade(nz, track)
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

    # ---- 瞬态脉冲激励 ----
    # 真实的爆破不是「一段被带通滤过的白噪」，而是**闭合突然释放产生的瞬态**
    # 去激励声道，让共振腔自己按共振峰振铃。噪声过同一个滤波器只会得到
    # 「嘶」——滤波白噪的相位是随机的，激不出有结构的余振，听上去就是合成器
    # 效果音。这里改用一个极短（0.3ms 衰减）的脉冲，经同一组共振峰滤波器，
    # 得到的是一声带元音色彩的「啪」，共振峰带宽决定它响多久。
    for i, s in enumerate(segments):
        if not s["click"]:
            continue
        a, b = int(bounds[i]), int(bounds[i + 1])
        m = b - a
        if m <= 16:
            continue
        t = np.arange(m) / SR
        # 脉冲的衰减时间常数决定它的低频含量：0.3ms 的尖峰频谱平直，
        # 但经共振峰滤波器后只剩中频；参考声库的辅音段在 300Hz 以下
        # 是最强的一档，所以这里要能调。
        imp = np.exp(-t / (ph.CLICK_TAU_MS / 1000.0))
        imp[:2] *= np.array([0.5, 1.0])[:min(2, m)]
        y = dsp.formant_cascade(imp, track[a:b])
        ry = dsp.rms(y)
        if ry > 1e-12:
            # 0.4ms 起音，避免采样级阶跃带来的宽带「咔」
            ramp = min(m, _ms(0.4))
            y = y / ry * s["click"] * ref
            y[:ramp] *= dsp.raised_cosine(ramp)
            out[a:b] += y

            # 低频冲击：闭合突然释放产生的不只是高频瞬态，还有一次低频的
            # 压力冲击。参考声库的辅音段在 300Hz 以下是最强的一档，而脉冲
            # 走共振峰滤波器后低频被 F1 挡住了，所以这里单独补一条不经过
            # 声道的低频衰减。
            if ph.THUMP_GAIN:
                th = np.exp(-t / (ph.THUMP_TAU_MS / 1000.0))
                th = dsp.lowpass(th, ph.THUMP_FC, order=2)
                rth = dsp.rms(th)
                if rth > 1e-12:
                    th = th / rth * s["click"] * ph.THUMP_GAIN * s["thump_scale"] * ref
                    th[:ramp] *= dsp.raised_cosine(ramp)
                    out[a:b] += th

    # 整段末尾再淡出一次，压掉滤波器余振
    n_out = min(_ms(ph.FADE_OUT), n)
    out[n - n_out:] *= dsp.raised_cosine(n_out)[::-1]

    out = dsp.normalize(out, ref, VOICED_RMS_DBFS, PEAK_CEILING)
    return out, bounds


# ==========================================================================
# 段落计划
# ==========================================================================
def _first_vowel(v, lang=ph):
    """韵母的第一个音色目标（韵头，没有韵头就是韵腹）。

    辅音的 locus 过渡要落在这个音色上 —— /jia/ 是 j→i→a，不是直接 j→a。
    """
    F = getattr(lang, "FINALS", None)
    if F is not None and v in F:
        on = F[v].get("on") or []
        return on[0][0] if on else F[v]["nucleus"]
    return v


def _lerp(a, b, t):
    return np.asarray(a, dtype=float) * (1.0 - t) + np.asarray(b, dtype=float) * t


def _final_segments(f, lang=ph):
    """韵母：韵头 → 韵腹（整段向韵尾滑）→ 鼻尾 → 收尾。

    韵腹这一段同时承担「撑住长音」和「向韵尾过渡」两件事：共振峰按
    u^FIN_GLIDE_CURVE 从韵腹滑向韵尾，前段几乎不动、越靠尾部越快。
    旧版是「撑满 680ms 静止的韵腹 + 末尾 130ms 滑过去」，前半段完全是 a，
    听感是一个静止的 a 突然变成 ai（demo/25 用户反馈）。

    鼻尾没有单独的「滑音段」—— 它和韵尾滑音用的是同一条曲线，只是目标换成
    MURMUR 的共振峰，滑到位后再保持 CODA_MS。这样 an / ang 是逐渐鼻化的，
    而不是「一段 a 后面接一个 n」。
    """
    V = lang.VOWELS
    on = f.get("on") or []
    nuc = f["nucleus"]
    off = f.get("off") or []
    coda = f.get("coda")
    first = on[0][0] if on else nuc

    # 韵头：ON_RAMP 那一段是**静止**在介音上的（也就是 w / y 本身），
    # 然后花 FIN_ON_MS 滑到韵腹。
    #
    # 坑：滑音段的目标必须写**韵腹**而不是介音自己 —— 写介音的话这一段
    # glide 的是 u→u，原地不动，真正的 u→a 会落到下一段，摊满整个 680ms
    # 的韵腹（wa / wo 实测就是这个症状：过渡一直不结束）。
    # glide_all 的韵母连起音都不该在起点上停留 —— 10ms 只是为了不爆音
    ramp_ms = 10.0 if f.get("glide_all") else ph.VOWEL_ON_RAMP
    segs = [_seg(ramp_ms, V[first]["F"], V[first]["BW"],
                 voiced=1.0, vowel=True)]
    if on:
        # 介音的静止停留（默认为 0）。üe / üan 需要它：ü 与 i 的共振峰只差
        # 250Hz，过渡段再长也只是「一次滑音」，驻留一段才听得出是 ü。
        hold = float(f.get("on_hold", 0.0))
        if hold > 0:
            segs.append(_seg(hold, V[first]["F"], V[first]["BW"],
                             voiced=1.0, vowel=True))
        dur = ph.FIN_ON_MS if ph.FIN_ON_MS is not None else on[0][1]
        for key, _ms in on[1:]:
            segs.append(_seg(dur, V[key]["F"], V[key]["BW"], voiced=1.0,
                             glide=True, vowel=True))
        segs.append(_seg(dur, V[nuc]["F"], V[nuc]["BW"], voiced=1.0,
                         glide=True, vowel=True))

    N = V[nuc]
    # 韵尾优先于鼻尾：üan 的滑行目标是 ɛ，鼻尾接在滑行之后（不是直接
    # 从 ü 滑到 n —— 那样会跳过韵腹）。
    if off:
        target_F = V[off[-1][0]]["F"]
        target_BW = V[off[-1][0]]["BW"]
    elif coda:
        target_F = CODA_F.get(coda) or lang.MURMUR[coda]
        target_BW = CODA_BW.get(coda) or ph.DEFAULT_BW
    else:
        target_F = None

    # glide_all：**整条韵母就是一次滑行**，起点和终点都不停留。
    # 韵腹段和收尾段合起来全部用于过渡，曲线由 f["curve"] 决定
    # （1.0 = 匀速）。üe / üan 用这个 —— 它们不该有静止的 ü。
    if target_F is not None and f.get("glide_all"):
        total = ph.VOWEL_HOLD + ph.VOWEL_TAIL
        curve = float(f.get("curve", 1.0))
        step = total / ph.FIN_GLIDE_STEPS
        for k in range(1, ph.FIN_GLIDE_STEPS + 1):
            t = (k / ph.FIN_GLIDE_STEPS) ** curve
            segs.append(_seg(step, _lerp(N["F"], target_F, t),
                             _lerp(N["BW"], target_BW, t),
                             voiced=1.0, glide=True, vowel=True))
        if coda:
            M = CODA_F.get(coda) or lang.MURMUR[coda]
            MBW = CODA_BW.get(coda)
            segs.append(_seg(ph.CODA_MS, M, MBW, voiced=1.0,
                             glide=True, vowel=True))
            segs.append(_seg(ph.VOWEL_TAIL, M, MBW, voiced=1.0,
                             glide=True, vowel=True))
        return segs

    if target_F is None:
        segs.append(_seg(ph.VOWEL_HOLD, N["F"], N["BW"], voiced=1.0,
                         glide=True, vowel=True))
    else:
        # 韵尾滑音占韵腹的比例，可逐韵母覆盖。üe 要「ü 撑住、尾部才滑向 ɛ」，
        # 不能用全局的 0.87（那会让滑音从 13% 处就开始）。
        span = float(f.get("span", ph.FIN_GLIDE_SPAN))
        flat = ph.VOWEL_HOLD * (1.0 - span)
        glide = ph.VOWEL_HOLD * span
        if flat > 0.5:
            segs.append(_seg(flat, N["F"], N["BW"], voiced=1.0,
                             glide=True, vowel=True))
        step = glide / ph.FIN_GLIDE_STEPS
        for k in range(1, ph.FIN_GLIDE_STEPS + 1):
            t = (k / ph.FIN_GLIDE_STEPS) ** ph.FIN_GLIDE_CURVE
            segs.append(_seg(step, _lerp(N["F"], target_F, t),
                             _lerp(N["BW"], target_BW, t),
                             voiced=1.0, glide=True, vowel=True))

    if coda:
        M = CODA_F.get(coda) or lang.MURMUR[coda]
        MBW = CODA_BW.get(coda)
        segs.append(_seg(ph.CODA_MS, M, MBW, voiced=1.0, glide=True, vowel=True))
        segs.append(_seg(ph.VOWEL_TAIL, M, MBW, voiced=1.0, glide=True, vowel=True))
    else:
        last = V[off[-1][0]] if off else N
        segs.append(_seg(ph.VOWEL_TAIL, last["F"], last["BW"], voiced=1.0,
                         glide=True, vowel=True))
    return segs


def _vowel_segments(v, lang=ph):
    F = getattr(lang, "FINALS", None)
    if F is not None and v in F:
        return _final_segments(F[v], lang)
    V = lang.VOWELS[v]
    A = V.get("A")
    if "F2" not in V:
        return [
            _seg(ph.VOWEL_ON_RAMP, V["F"], V["BW"], voiced=1.0, A=A, vowel=True),
            _seg(ph.VOWEL_HOLD, V["F"], V["BW"], voiced=1.0, A=A, vowel=True),
            _seg(ph.VOWEL_TAIL, V["F"], V["BW"], voiced=1.0, A=A, vowel=True),
        ]
    # 双元音：前半段停在起点元音，后半段滑向终点。转折点由 DIPH_AT 控制 ——
    # 英语的双元音前段长、后段只是方向性的滑音，所以转折点放在偏后位置。
    hold = ph.VOWEL_HOLD * float(V.get("DIPH_AT", 0.45))
    back = ph.VOWEL_HOLD - hold + ph.VOWEL_TAIL
    return [
        _seg(ph.VOWEL_ON_RAMP, V["F"], V["BW"], voiced=1.0, A=A, vowel=True),
        _seg(hold, V["F"], V["BW"], voiced=1.0, A=A, vowel=True),
        _seg(back, V["F2"], V["BW"], voiced=1.0, glide=True, A=A, vowel=True),
    ]


# 逐元音的 locus 表只给了 a o e i u 五个基准值。ü / ɛ / 舌尖元音用最接近的
# 基准值代替（ü→i、ɛ→e、i0/ir→i、er→e），否则 nüe / lüe 这类音节会查表失败。
_LOCUS_FALLBACK = {"v": "i", "E": "e", "i0": "i", "ir": "i", "er": "e"}


def _locus(c, v, lang=ph):
    """辅音的共振峰轨迹起点。

    软腭音单独查 VELAR_LOCUS —— 它的 locus 随后接元音大幅变化，用固定值
    会让 /gu/ 听成 /du/、/ko/ 听成 /kio/。glottal 部位返回 None（沿用元音）。

    韵母取**韵头**的音色：/jia/ 的过渡落在 i 上，不是直接落到 a。
    """
    C = lang.CONSONANTS[c]
    place = C.get("place")
    if place is None:          # 近音直接给自己的 F，没有部位 locus
        return None
    tbl = lang.PLACE_LOCUS_BY_VOWEL.get(place)
    if tbl is not None:
        key = _first_vowel(v, lang)
        return tbl[_LOCUS_FALLBACK.get(key, key)]
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


RELEASE_GLIDE = True


def _release_segments(C, locus, F_fallback, vowel_F=None, vowel_BW=None):
    """塞音的释放段：起爆 + 送气，共用一条连续包络。

    爆破拆成两部分，缺一不可：
      * 经声道的一份 —— 带上 locus 的共振峰色，听上去像从后面那个音里长出来的
      * 走部位带通的一份 —— 保留 g/k 与 d/t 的区分线索（齿龈爆破在高频、
        软腭爆破是中频紧凑的一团）

    两部分共用同一条包络，所以一起起爆、一起衰减，不会变成两个事件。

    RELEASE_GLIDE 为真时，送气段本身就在往元音滑（`glide=True`），而不是
    先送气到固定 locus、再单独用一段 GLIDE 过渡过去。真实语音里共振峰
    过渡就是在送气期间同时发生的。
    """
    tgt = locus if locus is not None else F_fallback
    n_b = _ms(C["burst"])
    n_a = _ms(C["aspiration"])
    env = _release_env(n_b + n_a, n_b, _ms(ph.RELEASE_SPILL))
    # 带通要 4 阶：2 阶在 (1800, 3200) 的裙边会一直延伸到 4~6kHz，
    # 那正是爆破听上去「嘶」的来源。
    # 起爆强度层级：文献（牛津）给出 voiceless aspirated > voiceless unaspirated
    # > voiced。逐辅音的倍率放在 CONSONANTS 里，默认 1.0。
    # 辅音段的**总增益**：起爆脉冲、部位带通、经声道噪声、低频冲击一起缩放。
    # 单独提 GAIN_RELEASE 没用 —— 实测送气对辅音能量的贡献只有 0.1dB，
    # 因为它在 46ms 里电平本就低，而脉冲和低频冲击是瞬态、能量集中。
    g = ph.CONSONANT_GAIN
    bs = float(C.get("burst_scale", 1.0)) * g
    segs = [_seg(C["burst"], tgt,
                 noise_tract=ph.GAIN_RELEASE * g, noise_lp=True,
                 noise_band=(ph.GAIN_BURST * bs,
                             C.get("burst_band") or ph.PLACE_BURST[C["place"]]),
                 noise_order=C.get("noise_order", 4),
                 click=ph.GAIN_CLICK * bs,
                 thump_scale=C.get("thump_scale", 1.0), env=env[:n_b])]
    if RELEASE_GLIDE and vowel_F is not None:
        segs.append(_seg(C["aspiration"], vowel_F, vowel_BW,
                         noise_tract=ph.GAIN_RELEASE * g, env=env[n_b:],
                         glide=True))
    else:
        segs.append(_seg(C["aspiration"], tgt,
                         noise_tract=ph.GAIN_RELEASE * g, env=env[n_b:]))
    return segs


def _cv_segments(c, v, lang=ph):
    C = lang.CONSONANTS[c]
    V = lang.VOWELS[_first_vowel(v, lang)]
    locus = _locus(c, v, lang)

    segs = []
    if C["kind"] == "plosive":
        segs.append(_seg(C["closure"], locus or V["F"], shape="flat"))  # 闭塞，静音
        segs.extend(_release_segments(C, locus, V["F"], V["F"], V["BW"]))
        boost = ph.ASP_F0_BOOST if C.get("aspirated") else ph.ASP_F0_BOOST * 0.3
        segs.append(_seg(ph.PLOSIVE_GLIDE, V["F"], V["BW"], voiced=1.0, glide=True,
                         f0_boost=boost))

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
    V = lang.VOWELS[_first_vowel(v, lang)]
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
    # 元音段由 _vowel_segments 打上 vowel=True —— 韵母会展开成不定长段数，
    # 不能再按「末三段」数。
    cons_ms = sum(s["dur"] for s in segs if not s["vowel"])
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
