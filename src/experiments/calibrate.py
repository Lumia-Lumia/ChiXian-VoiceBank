"""用参考声库的谱包络反解并联共振峰的增益。

     python src/experiments/calibrate.py

思路：并联结构的输出谱是 Y(f) = X(f) · Σ A_i·|H_i(f)|，对 A_i 是线性的。
把参考声库的实测包络当作目标 T(f)，就有 Σ A_i·|H_i(f)| = T(f)/X(f)，
一个最小二乘问题，5 个未知数、几十个频点。
"""

import os
import sys

# 实验脚本在子目录里，而合成模块在上一级（src/）。从项目根目录运行时
# 脚本所在目录会被加进 sys.path，但 src/ 不会，所以这里补一条。
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import wave

import numpy as np

import dsp
import phonemes as ph
from config import FORMANT_SCALE_BY_INDEX, SR


def harmonic_env(path):
    """返回参考采样的谐波包络 (频率, 幅度dB)，以 300Hz 处归零。"""
    with wave.open(path, "rb") as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(float) / 32768
        sr = w.getframerate()
    s = x[int(len(x) * 0.4):int(len(x) * 0.4) + 8192]
    ac = np.correlate(s, s, "full")[len(s) - 1:]
    lo, hi = int(sr / 900), int(sr / 80)
    f0 = float(sr / (lo + np.argmax(ac[lo:hi])))
    seg = x[int(len(x) * 0.30):int(len(x) * 0.80)]
    seg = seg * np.hanning(len(seg))
    N = 8 * len(seg)
    S = np.abs(np.fft.rfft(seg, N))
    f = np.fft.rfftfreq(N, 1 / sr)
    ns = np.arange(1, int(16000 / f0) + 1)
    A = np.array([S[np.argmin(np.abs(f - n * f0))] for n in ns], dtype=float)
    k = 6
    pad = np.pad(A, k, mode="edge")
    A = np.convolve(pad, np.ones(2 * k + 1) / (2 * k + 1), mode="same")[k:-k]
    fr = ns * f0
    return fr, A


def source_env(f0=261.6256, freqs=None):
    """我们声源在各频率上的幅度（fm_harmonics 给出的是各次谐波的幅度）。"""
    amps = dsp.fm2_harmonics(f0, tilt=0.0)  # 干净的声源幅度
    # 用 |H| 形状：反馈 FM 谱近似 1/n，这里直接用 1/n 作源谱
    h = np.arange(1, len(amps) + 1)
    return h * f0, 1.0 / h


def resonator_mag(F, BW, freqs, sr=SR):
    """二阶谐振器在给定频率上的幅度响应。"""
    r = np.exp(-np.pi * BW / sr)
    z = np.exp(-2j * np.pi * freqs / sr)
    b = (1 - 2 * r * np.cos(2 * np.pi * F / sr) + r * r)
    a = 1 - 2 * r * np.cos(2 * np.pi * F / sr) * z + r * r * z * z
    return np.abs(b / a)


def fit_gains(F, BW, fr_ref, A_ref, freqs):
    """解 Σ A_i·|H_i(f)| = T(f)/X(f)。"""
    target = np.interp(freqs, fr_ref, A_ref)
    # 源谱：1/n 形状，按 f0 换算
    src = 1.0 / np.maximum(freqs / 261.6256, 1.0)
    ratio = target / np.maximum(src, 1e-12)
    ratio = ratio / ratio.max()
    M = np.stack([resonator_mag(F[i], BW[i], freqs) for i in range(len(F))], axis=1)
    sol, *_ = np.linalg.lstsq(M, ratio, rcond=None)
    return sol


def main():
    teto = None
    for d in os.listdir("ref/banks/teto"):
        p = os.path.join("ref/banks/teto", d)
        if os.path.isdir(p):
            teto = os.path.join(p, "重音テト単独音")
    files = {"a": "_あ.wav", "i": "_い.wav", "u": "_う.wav", "e": "_え.wav", "o": "_お.wav"}
    freqs = np.arange(250, 8001, 50)
    scale = np.asarray(FORMANT_SCALE_BY_INDEX, dtype=float)
    print("解出的并联共振峰增益（可粘贴进 phonemes.py）：")
    for v, fn in files.items():
        F = np.asarray(ph.VOWELS[v]["F"], dtype=float) * scale
        BW = np.asarray(ph.VOWELS[v]["BW"], dtype=float) * 1.10
        fr, A = harmonic_env(os.path.join(teto, fn))
        g = fit_gains(F, BW, fr, A, freqs)
        g = g / g.max()
        print(f'    "{v}": A=[{", ".join(f"{x:.3f}" for x in g)}],')


if __name__ == "__main__":
    main()
