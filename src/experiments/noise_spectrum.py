"""比较各声库「送气段」的噪声谱形。

    python src/experiments/noise_spectrum.py

动机：白噪声是等能量每赫兹、高斯分布、完全稳态的。真实的湍流噪声不是：
气流通过收缩处产生的噪声有频谱倾斜（低频多、高频少），而且幅度是起伏的。
把白噪直接喂进声道滤波器，听起来就是「电子设备」而不是「人」。

这里量的是送气段的**谱斜率**（以 100~300Hz 为 0dB 参考），用来看
参考声库的噪声往高频衰减得多快，以及我们差多少。

注意：Kumi 的 8 位 WAV 有 +0.18 直流偏置，必须先去掉再算频谱。
"""

import os
import wave

import numpy as np

SR = 44100
BANDS = [(100, 300), (300, 600), (600, 1200), (1200, 2400), (2400, 4800), (4800, 9600)]

TETO = "ref/banks/teto/重音テト音声ライブラリー/重音テト単独音"
KUMI = "ref/banks/hitsuboku-kumi-chn/A4"
EME = "ref/banks/emerald/Emerald V.3.6.0/D#4"


def load(path):
    with wave.open(path, "rb") as w:
        sw, ch = w.getsampwidth(), w.getnchannels()
        raw = w.readframes(w.getnframes())
    if sw == 1:
        x = (np.frombuffer(raw, np.uint8).astype(float) - 128.0) / 128.0
    elif sw == 2:
        x = np.frombuffer(raw, "<i2").astype(float) / 32768.0
    elif sw == 3:
        b = np.frombuffer(raw, np.uint8)
        b = b[:len(b) // 3 * 3].reshape(-1, 3)
        v = (b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8)
             | (b[:, 2].astype(np.int32) << 16))
        v = np.where(v >= 1 << 23, v - (1 << 24), v)
        x = v.astype(float) / float(1 << 23)
    else:
        x = np.frombuffer(raw, "<i4").astype(float) / 2 ** 31
    if ch == 2:
        x = x.reshape(-1, 2).mean(1)
    return x - x.mean()          # 去直流


def bands(x):
    if len(x) < 512:
        return None
    s = x * np.hanning(len(x))
    S = np.abs(np.fft.rfft(s)) ** 2
    f = np.fft.rfftfreq(len(s), 1 / SR)
    out = []
    for lo, hi in BANDS:
        out.append(10 * np.log10(S[(f >= lo) & (f < hi)].sum() + 1e-20))
    base = out[0]
    return [v - base for v in out]


def tone(x):
    """过零率：噪声接近 0.5，浊音低得多。用来确认取到的是噪声段。"""
    if len(x) < 2:
        return 0.0
    return float(np.mean(np.abs(np.diff(np.signbit(x).astype(np.int8)))))


def show(tag, x):
    b = bands(x)
    if b is None:
        print(f"  {tag:12} 太短")
        return
    print(f"  {tag:12} " + " ".join(f"{v:7.1f}" for v in b) + f"   ZCR {tone(x):.2f}")


def main():
    print("送气段谱形（相对 100-300Hz，dB），以及过零率（噪声≈0.5）")
    print(f"  {'':12} " + " ".join(f"{lo}-{hi}".rjust(7) for lo, hi in BANDS))

    # 参考：手动定位元音前的噪声段（各声库位置已实测）
    refs = [
        ("Teto日 ka", f"{TETO}/_か.wav", 40, 60),
        ("Teto日 ta", f"{TETO}/_た.wav", 31, 37),
        ("Kumi中 pa", f"{KUMI}/_pa_pa.wav", 720, 760),
        ("Kumi中 ta", f"{KUMI}/_ta_ta.wav", 690, 730),
        ("Eme俄 pa", f"{EME}/papap.wav", 1500, 1545),
    ]
    for tag, p, a, b in refs:
        if not os.path.exists(p):
            continue
        x = load(p)[int(a * SR / 1000):int(b * SR / 1000)]
        show(tag, x)

    print()
    print("本声库（中文）：起爆之后 20~60ms")
    import render
    for s in ("pa", "ta", "ka"):
        audio, _ = render.render_cv(s[0], s[1], 311.127, humanize=False)
        o = int(60 * SR / 1000) if s[0] == "p" else int(55 * SR / 1000)
        show(f"我们 {s}", audio[o + int(20e-3 * SR):o + int(60e-3 * SR)])

    print()
    print("纯白噪对照（同样 40ms）：")
    show("白噪", np.random.default_rng(0).normal(size=int(0.04 * SR)))


if __name__ == "__main__":
    main()
