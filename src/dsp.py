"""DSP 原语：FM 声带源、串联共振峰谐振器、噪声、包络、归一化。

信号链：
    FM 对 ──贝塞尔展开──> 带限谐波激励 ──┐
                                        ├──> 串联二阶共振峰谐振器 ──> + 带通噪声 ──> 归一化
    白噪 ──(声门激励/带通)──────────────┘

设计取舍说明
------------
* 声带源不直接对 y=sin(f_c t + I sin(f_m t)) 求值时域波形，而是先用
  贝塞尔函数展开成谐波幅度，再按谐波频率逐条合成。原因：直接求值时
  高次边带会超过 Nyquist 产生混叠；贝塞尔展开可以精确截断到带限。
  两种算法在带限内完全等价（见 _selftest）。
* 共振峰用 Klatt 式二阶谐振器串联，系数逐块更新以支持共振峰过渡。
  谐振器频率固定在 Hz，与 f0 无关 —— 这正是纲领 三.5 要求的
  「变调不产生花栗鼠效应」。
"""

from __future__ import annotations

import math

import numpy as np
from scipy.signal import butter, lfilter, resample_poly, sosfilt
from scipy.special import jv

from config import (BAND_GUARD, FM2_I, FM2_PAIRS, FM2_TILT, FM2S_SMOOTH_OCT,
                    FM2S_TILT, FM_FB_BETA, FM_FB_OVERSAMPLE, PHASE_SEED,
                    SOURCE_METHOD, SOURCE_SHELF_DB, SOURCE_SHELF_FC, SR)


# ==========================================================================
# 1. 声带源
# ==========================================================================
def fm2_harmonics(f0, sr=SR, I=FM2_I, pairs=FM2_PAIRS, tilt=FM2_TILT,
                  guard=BAND_GUARD):
    """两算子 FM 的谐波幅度（纲领 三.1 原式）。

    推导：y = sin(ω_c t + I·sin(ω_m t)) = Σ_n J_n(I)·sin((ω_c + n·ω_m)t)
    取 ω_c = 2πk·f0、ω_m = 2πf0，各项频率恰为 f0 的整数倍 h = k+n。
    把 h<0 的项折回正频率（sin(-θ) = -sin(θ)），得

        A_m = J_{m-k}(I) - J_{-m-k}(I)

    h=0 的项 sin(0)=0，因此不产生直流分量。

    注意：单个 k 只点亮约 2I 条谐波，且 J_n(I) 在低次区有周期约 4 条
    谐波的深谷。对 k 求和相当于滑动平均，而滑动平均的传递函数必有零点 ——
    权重只能挪动零点、填不平，所以本函数输出的谱一定带梳齿。
    """
    max_h = int(guard * sr / f0)
    m = np.arange(1, max_h + 1)
    amps = np.zeros(max_h)
    for k in range(1, pairs + 1):
        amps += jv(m - k, I) - jv(-m - k, I)
    return amps * m.astype(float) ** (-tilt)


def smooth_harmonics(amps, oct_frac=FM2S_SMOOTH_OCT, min_width=4):
    """按倍频程带宽平滑谐波幅度，填平两算子 FM 的梳齿。

    窗口以谐波序数为对数轴（乘性宽度），低频端窄、高频端宽，与听觉临界带
    的划分一致；但低次谐波处必须补一个最小绝对宽度，否则梳齿最严重的那段
    反而几乎没被平滑到。

    注意取绝对值再平均：J_n(I) 是正负摆动的，直接对有符号值取均值会让相邻
    谐波相互抵消（实测会把第 6 次谐波压到 -32 dB）。幅度符号对应 180° 相位，
    而加法合成本来就用随机相位，所以丢弃符号没有影响。
    """
    m = np.arange(1, len(amps) + 1)
    a = np.abs(amps)
    out = np.empty_like(a)
    for i, mi in enumerate(m):
        half = max(mi * oct_frac / 2.0, min_width / 2.0)
        w = (m >= mi - half) & (m <= mi + half)
        out[i] = a[w].mean() if w.any() else a[i]
    return out


def fmfb_source(f0, n, sr=SR, beta=FM_FB_BETA, oversample=FM_FB_OVERSAMPLE,
                f0_curve=None):
    """反馈 FM：y[n] = sin(φ[n] + β·y[n-1])。

    β→1 时谱形趋近锯齿波的 1/n 衰减，谐波列平滑无梳齿 —— 这正是纲领
    「用纯正弦运算产生谐波列，替代锯齿波声带源」想要的结果。β 越小谱越暗。

    f0_curve 给出逐采样点的瞬时基频，相位由此累积（∫f0 dt），用于承载
    人性化的音高不稳（jitter）。注意这里没有周期性颤音 —— 颤音交给
    UTAU 编辑器，烘进采样会与它打架。

    代价：递归式无闭式解，边带无限延伸，必须先以 oversample 倍率生成、
    再抗混叠降采样，否则 44.1kHz 直出会有约 -23 dB 的非谐波残余。
    """
    m = n * oversample
    if f0_curve is None:
        ph = 2.0 * np.pi * f0 * np.arange(m) / (sr * oversample)
    else:
        # f0_curve 在 1× 速率上给出，先插值到过采样率再累加相位
        f = np.interp(np.arange(m) / oversample, np.arange(n), f0_curve)
        ph = np.cumsum(2.0 * np.pi * f / (sr * oversample))

    def gen():
        prev = 0.0
        for x in ph:
            prev = math.sin(x + beta * prev)
            yield prev

    y = np.fromiter(gen(), dtype=np.float64, count=m)
    if oversample > 1:
        y = resample_poly(y, 1, oversample)
    if len(y) < n:
        y = np.pad(y, (0, n - len(y)))
    return y[:n]


def peaking(x, fc, gain_db, q=0.8, sr=SR):
    """RBJ 钟形峰值滤波器：在 fc 附近提升 gain_db，两端回到 0dB。

    这是补「某个频段缺一块」的正确工具。高架（high_shelf）只提升转折点以上
    的整个频段，用它去补 1.2~2.5kHz 的凹陷，会连带把 5~10kHz 顶得更吵。
    """
    if not gain_db:
        return x
    A = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * np.pi * fc / sr
    alpha = np.sin(w0) / (2.0 * q)
    cw = np.cos(w0)
    b = np.array([1 + alpha * A, -2 * cw, 1 - alpha * A])
    a = np.array([1 + alpha / A, -2 * cw, 1 - alpha / A])
    return lfilter(b / a[0], a / a[0], np.asarray(x, dtype=np.float64))


def high_shelf(x, fc, gain_db, sr=SR):
    """RBJ 高架滤波器：fc 以上提升 gain_db，以下基本不变。

    反馈 FM 的谱倾斜由 β 决定，但 β 只能提供约 9 dB 的亮度调节范围，
    不够「明亮少女」用，所以高频表现主要靠这条 shelf。
    """
    if not gain_db:
        return x
    A = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * np.pi * fc / sr
    alpha = np.sin(w0) / 2.0 * np.sqrt(2.0)
    cos_w0 = np.cos(w0)
    sqA = np.sqrt(A)

    b = np.array([A * ((A + 1) + (A - 1) * cos_w0 + 2 * sqA * alpha),
                  -2 * A * ((A - 1) + (A + 1) * cos_w0),
                  A * ((A + 1) + (A - 1) * cos_w0 - 2 * sqA * alpha)])
    a = np.array([(A + 1) - (A - 1) * cos_w0 + 2 * sqA * alpha,
                  2 * ((A - 1) - (A + 1) * cos_w0),
                  (A + 1) - (A - 1) * cos_w0 - 2 * sqA * alpha])
    return lfilter(b / a[0], a / a[0], np.asarray(x, dtype=np.float64))


def additive_source(f0, n, amps, sr=SR, seed=PHASE_SEED):
    """按谐波幅度做加法合成，长度 n。

    每条谐波用独立随机初相位：所有谐波同相会让波形出现窄脉冲尖峰，
    听感发「嗡」；随机相位把它摊平成正常的嗓音波形。
    """
    h = np.arange(1, len(amps) + 1)
    t = np.arange(n, dtype=np.float64) / sr
    rng = np.random.default_rng(seed)
    phase = rng.uniform(0.0, 2.0 * np.pi, len(amps))
    grid = np.sin(2.0 * np.pi * np.outer(h, t) * f0 + phase[:, None])
    return (amps[:, None] * grid).sum(axis=0)


def make_source(f0, n, method=None, seed=PHASE_SEED, f0_curve=None,
                brighten=True):
    """按指定方案生成单位 RMS 的声带源波形。"""
    method = method or SOURCE_METHOD
    if method == "fmfb":
        y = fmfb_source(f0, n, f0_curve=f0_curve)
    elif method == "fm2":
        y = additive_source(f0, n, fm2_harmonics(f0), seed=seed)
    elif method == "fm2s":
        y = additive_source(f0, n,
                            smooth_harmonics(fm2_harmonics(f0, tilt=FM2S_TILT)),
                            seed=seed)
    else:
        raise ValueError(f"未知的声带源方案: {method}")
    if brighten:
        y = high_shelf(y, SOURCE_SHELF_FC, SOURCE_SHELF_DB)
    r = rms(y)
    return y / r if r > 1e-12 else y


# ==========================================================================
# 2. 共振峰：Klatt 式二阶谐振器串联
# ==========================================================================
def resonator_coeffs(F, BW, sr=SR):
    """单个二阶谐振器的 (b, a) 系数，直流增益归一化为 1。"""
    r = np.exp(-np.pi * BW / sr)
    B = 2.0 * r * np.cos(2.0 * np.pi * F / sr)
    C = -r * r
    A = 1.0 - B - C
    return np.array([A]), np.array([1.0, -B, -C])


def formant_cascade(x, track, sr=SR, block=64):
    """串联共振峰滤波，支持逐采样点的参数轨迹。

    track : (n, n_formants, 2) —— 每个采样点的 [中心频率, 带宽]。
    系数每 block 个采样更新一次并从新档位继续（lfilter 的 zi 状态跨块保留），
    这样共振峰滑动时不会产生段落断点。
    """
    n = len(x)
    n_formants = track.shape[1]
    out = np.empty(n, dtype=np.float64)
    state = [np.zeros(2) for _ in range(n_formants)]
    for s in range(0, n, block):
        e = min(s + block, n)
        f = track[(s + e) // 2]
        seg = np.asarray(x[s:e], dtype=np.float64)
        for i in range(n_formants):
            b, a = resonator_coeffs(f[i, 0], f[i, 1], sr)
            seg, state[i] = lfilter(b, a, seg, zi=state[i])
        out[s:e] = seg
    return out


def formant_parallel(x, track, sr=SR, block=64):
    """并联共振峰滤波器组。

    track : (n, n_formants, 3) —— 每个采样点的 [中心频率, 带宽, 增益]

    每个共振峰**独立**谐振，按各自的增益加权求和。与 formant_cascade 的关键
    区别：串联结构里各峰的相对幅度由前级滤波器的衰减顺带决定，无法指定；
    并联结构里它是显式参数，可以直接拟合到目标谱。

    声源与噪声都走同一条并联支路，保证辅音和元音在同一套声道模型里。
    """
    n = len(x)
    nf = track.shape[1]
    xs = np.asarray(x, dtype=np.float64)
    out = np.zeros(n, dtype=np.float64)
    state = [np.zeros(2) for _ in range(nf)]
    for s0 in range(0, n, block):
        e = min(s0 + block, n)
        f = track[(s0 + e) // 2]
        seg = xs[s0:e]
        acc = np.zeros(e - s0)
        for i in range(nf):
            b, a = resonator_coeffs(f[i, 0], f[i, 1], sr)
            y, state[i] = lfilter(b, a, seg, zi=state[i])
            acc += f[i, 2] * y
        out[s0:e] = acc
    return out


# ==========================================================================
# 3. 噪声
# ==========================================================================
def white(n, seed=0):
    """单位方差白噪。"""
    return np.random.default_rng(seed).standard_normal(n)


def bandpass(x, lo, hi, order=2, sr=SR):
    """巴特沃斯带通，用于擦音与爆破噪声的成形。"""
    lo = max(lo, 20.0)
    hi = min(hi, sr * 0.49)
    sos = butter(order, [lo, hi], btype="band", fs=sr, output="sos")
    return sosfilt(sos, x)


def lowpass(x, fc, order=2, sr=SR):
    sos = butter(order, fc, btype="low", fs=sr, output="sos")
    return sosfilt(sos, x)


def highpass(x, fc, order=2, sr=SR):
    sos = butter(order, fc, btype="high", fs=sr, output="sos")
    return sosfilt(sos, x)


def sibilant(x, peaks, hp, hp_order=4, sr=SR):
    """把白噪塑成咝音（/s/）。

    不能只用窄带通滤白噪 —— 那样得到的是「哨音 / 静电噪声」：带限白噪的谱
    太平、太窄，没有真实咝音的峰谷结构。真实 /s/ 是高通的陡坡挡住 /ʃ/ 频段，
    再由前腔的几个宽共振叠出 5~10kHz 的起伏。
    """
    y = highpass(x, hp, order=hp_order, sr=sr)
    for F, BW in peaks:
        b, a = resonator_coeffs(F, BW, sr)
        y = lfilter(b, a, y)
    return y


# ==========================================================================
# 4. 包络与工具
# ==========================================================================
def rms(x):
    x = np.asarray(x, dtype=np.float64)
    return float(np.sqrt(np.mean(x * x))) if x.size else 0.0


def write_wav(path, x, sr=SR):
    """写 44.1kHz / 16bit / 单声道 WAV（标准库 wave，不需要 soundfile）。"""
    import wave

    pcm = np.clip(np.asarray(x, dtype=np.float64), -1.0, 1.0)
    pcm = (pcm * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return len(pcm)


def raised_cosine(n):
    """0→1 的升余弦斜坡，长度 n。"""
    if n <= 1:
        return np.ones(max(n, 0))
    return 0.5 - 0.5 * np.cos(np.pi * np.arange(n) / (n - 1))


def local_rms(x, win_ms=40.0, sr=SR):
    """平滑的局部 RMS 包络。

    用来把经声道的噪声逐点归一化：同一条串联谐振器，在元音区（5 个高 Q
    谐振器全开）的宽带增益，比在辅音 locus 区高好几倍。只按整段的 RMS
    归一化的话，送气/爆破段会比标称低约 14 dB。
    """
    x = np.asarray(x, dtype=np.float64)
    w = max(1, int(round(win_ms / 1000.0 * sr)))
    if w <= 1:
        return np.abs(x)
    pad = w // 2
    xp = np.pad(x, pad, mode="edge")
    p = np.convolve(xp * xp, np.ones(w) / w, mode="same")[pad:pad + len(x)]
    return np.sqrt(np.maximum(p, 0.0))


def slow_random(n, seed, corr_ms, sr=SR):
    """生成一条慢速随机曲线：均值 0、标准差 1、相关长度约 corr_ms。

    做法是在低速率上抽独立高斯样本再线性插值。人性化的各种微扰
    （音高不稳、音量起伏、共振峰漂移）都用它，区别只在相关长度：
    3.5ms 对应声门周期级抖动，80ms 对应声道形状的缓慢游走。
    """
    rng = np.random.default_rng(seed)
    hop = max(1, int(round(corr_ms / 1000.0 * sr)))
    nk = n // hop + 3
    k = rng.standard_normal(nk)
    x = np.arange(n) / hop
    i0 = np.floor(x).astype(int)
    frac = x - i0
    y = k[i0] * (1.0 - frac) + k[i0 + 1] * frac
    s = float(np.std(y))
    return y / s if s > 1e-12 else y


def apply_fades(sig, env, fade_in_ms, fade_out_ms, sr=SR):
    """对激励包络做整体首尾淡化。

    淡入从第一个非零采样点之后开始（而不是文件开头），
    这样塞音的闭塞段不会被破坏。
    """
    env = env.copy()
    nz = np.flatnonzero(env > 1e-6)
    if nz.size:
        start = nz[0]
        n_in = min(int(fade_in_ms / 1000 * sr), len(env) - start)
        if n_in > 1:
            env[start:start + n_in] *= raised_cosine(n_in)
    n_out = min(int(fade_out_ms / 1000 * sr), len(env))
    if n_out > 1:
        env[len(env) - n_out:] *= raised_cosine(n_out)[::-1]
    return env


def normalize(sig, ref_rms, target_dbfs, peak_ceiling):
    """按参考段的 RMS 统一电平，再套峰值保护。

    用参考段（浊音部分）而不是整段来定增益，
    这样同一批文件里「元音/辅音」的相对强弱不会被归一化抹平。
    """
    if ref_rms < 1e-12:
        return sig
    target = 10.0 ** (target_dbfs / 20.0)
    out = sig * (target / ref_rms)
    peak = float(np.max(np.abs(out))) if out.size else 0.0
    if peak > peak_ceiling:
        out *= peak_ceiling / peak
    return out


# ==========================================================================
# 自检
# ==========================================================================
def _selftest():
    """校验两算子 FM 的贝塞尔展开式与直接求值是否等价（带限内）。"""
    sr, f0, k, I = SR, 261.6256, 1, 1.35
    n = sr
    t = np.arange(n) / sr
    direct = np.sin(2 * np.pi * k * f0 * t + I * np.sin(2 * np.pi * f0 * t))

    amps = fm2_harmonics(f0, sr=sr, I=I, pairs=k, tilt=0.0)
    h = np.arange(1, len(amps) + 1)
    grid = np.sin(2 * np.pi * np.outer(h, t) * f0)
    recon = amps @ grid

    err = float(np.max(np.abs(direct - recon)))
    print(f"FM 展开自检：谐波数 {len(amps)}，"
          f"max|直接求值 - 贝塞尔重构| = {err:.3e}")
    return err


if __name__ == "__main__":
    _selftest()
