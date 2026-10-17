"""A/B/C 三种声带源的客观对比与对照样本渲染。

    python src/experiments/compare_sources.py

输出：
    demo/01_声源方案/A_fmfb/   反馈 FM
    demo/01_声源方案/B_fm2/    两算子 FM
    demo/01_声源方案/C_fm2s/   两算子 FM + 包络平滑

每个目录里是同一组 a i u e o ba「a b」，可以直接 A/B 试听。
客观指标在终端里一并打印（梳齿深度、频带能量比）。
"""

import os
import sys

# 实验脚本在子目录里，而合成模块在上一级（src/）。从项目根目录运行时
# 脚本所在目录会被加进 sys.path，但 src/ 不会，所以这里补一条。
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import wave

import numpy as np

import dsp
import render
from config import SR
from _demo import fresh, write

F0_C4 = 261.6256
F0_AN = 100.0          # 分析用低音高：谱线间隔 100 Hz，足以分辨谐波
METHODS = [("A_fmfb", "fmfb", "反馈 FM"),
           ("B_fm2", "fm2", "两算子 FM"),
           ("C_fm2s", "fm2s", "两算子 FM+平滑")]
SAMPLE_SET = [("a", "vowel", "a"), ("i", "vowel", "i"), ("u", "vowel", "u"),
              ("e", "vowel", "e"), ("o", "vowel", "o"),
              ("ba", "cv", ("b", "a")), ("a b", "vc", ("a", "b"))]


def analyze(method):
    """返回 (梳齿标准差 dB, 梳齿最大 dB, 高频/低频能量比 dB)。"""
    y = dsp.make_source(F0_AN, SR * 2, method=method)
    seg = y[SR // 2:SR * 3 // 2] * np.hanning(SR)
    n = 4 * len(seg)
    S = np.abs(np.fft.rfft(seg, n))
    f = np.fft.rfftfreq(n, 1.0 / SR)
    A = np.array([S[np.argmin(np.abs(f - k * F0_AN))] for k in range(1, 41)])

    a = np.maximum(A, 1e-12)
    sm = np.convolve(a, np.ones(5) / 5, mode="same")
    d = 20 * np.log10(a[2:-2] / sm[2:-2])
    lo = np.sqrt((A[:4] ** 2).sum())      # 100-400 Hz
    hi = np.sqrt((A[20:40] ** 2).sum())   # 2-4 kHz
    return float(np.std(d)), float(np.max(np.abs(d))), float(20 * np.log10(hi / lo))


def save(path, audio):
    write(path, audio)      # 补静音，与其它实验脚本一致


def render_set(method, outdir):
    os.makedirs(outdir, exist_ok=True)
    for name, kind, arg in SAMPLE_SET:
        if kind == "vowel":
            audio, _ = render.render_vowel(arg, F0_C4, method=method)
        elif kind == "cv":
            audio, _ = render.render_cv(arg[0], arg[1], F0_C4, method=method)
        else:
            audio, _ = render.render_vc(arg[0], arg[1], F0_C4, method=method)
        save(os.path.join(outdir, f"{name}.wav"), audio)


OUT = os.path.join("demo", "01_声源方案")


def main():
    print("声带源自检：", end="")
    dsp._selftest()

    print("\n客观指标（谐波 1-40，f0=100Hz 分析）")
    print(f"  {'方案':<18}{'梳齿σ':>9}{'梳齿max':>10}{'高/低频比':>11}")
    for _, method, label in METHODS:
        s, mx, tilt = analyze(method)
        print(f"  {label:<18}{s:>8.1f}dB{mx:>9.1f}dB{tilt:>10.1f}dB")
    print("  参考：理想平滑谱 σ≈0。高/低频比用来判断三种方案的亮度是否可比 ——")
    print("  若相差超过约 6 dB，试听时会更倾向于选亮的那个，而不是更好听的那个。")

    print("\n渲染对照样本")
    fresh(OUT)          # 先清空，免得上一轮的变体残留
    for dirname, method, label in METHODS:
        outdir = os.path.join(OUT, dirname)
        render_set(method, outdir)
        print(f"  demo/01_声源方案/{dirname}/  {label}  {len(SAMPLE_SET)} 个文件")


if __name__ == "__main__":
    main()
