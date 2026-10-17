"""系统测量各参考声库里爆破音的结构。

    python src/experiments/plosive_study.py

不用 oto.ini 的先行发声 —— 实测发现各家声库的 offset 落点不一致
（Kumi 的 offset 落在辅音前约 60ms 的静音里，Teto英语的先行发声
对应的是闭合段而不是元音起点）。改为从信号本身定义：

    元音起点 = 包络第一次连续 30ms 高于元音电平一半的位置
    辅音起点 = 该点之前第一次超过元音电平 5% 的位置

注意两个坑：
* **Kumi 的 8 位 WAV 有 +0.18 的直流偏置**，不去直流的话整段会被 DC 主导，
  测出来的「质心 5Hz」全是假的
* 元音电平取 75 百分位而不是中位数 —— 中位数会被长静音拉低
"""

import os

import numpy as np

SR = 44100
FRAME_MS = 2.0

BANKS = {
    "Teto日": ("ref/banks/teto/重音テト音声ライブラリー/重音テト単独音", "cp932",
               {"pa": "_ぱ.wav", "ta": "_た.wav", "ka": "_か.wav",
                "ba": "_ば.wav", "da": "_だ.wav", "ga": "_が.wav"}),
    "Teto英": ("ref/banks/teto-en/重音テト音声ライブラリー/重音テト英語音源", "cp932",
               {"pa": "_pau+_pau+_p-.wav", "ta": "_tau+_tau+_t-.wav",
                "ka": "_kau+_kau+_k-.wav", "ba": "_bau+_bau+_b-.wav",
                "da": "_dau+_dau+_d-.wav", "ga": "_gau+_gau+_g-.wav"}),
    "Kumi中": ("ref/banks/hitsuboku-kumi-chn/A4", "cp932",
               {s: f"_{s}_{s}.wav" for s in ("pa", "ta", "ka", "ba", "da", "ga")}),
    "Eme俄": ("ref/banks/emerald/Emerald V.3.6.0/D#4", "utf-8",
              {s: f"{s}a{s[1]}a{s[1]}.wav" for s in ("pa", "ta", "ka", "ba", "da", "ga")}),
}

BANDS = [(0, 500), (500, 1000), (1000, 2000), (2000, 4000), (4000, 8000), (8000, 16000)]


def load(path):
    import wave
    with wave.open(path, "rb") as w:
        sw = w.getsampwidth()
        raw = w.readframes(w.getnframes())
        ch = w.getnchannels()
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
    return x - x.mean()


def envelope(x, ms=FRAME_MS):
    hop = int(SR * ms / 1000)
    n = len(x) // hop
    return np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(1))


def find_vowel(env):
    level = float(np.percentile(env, 75))
    hold = int(30 / FRAME_MS)
    for i in range(len(env) - hold):
        if np.all(env[i:i + hold] > level * 0.5):
            return i, level
    return len(env) - 1, level


def spectrum(x):
    if len(x) < 64:
        return None
    s = x * np.hanning(len(x))
    S = np.abs(np.fft.rfft(s)) ** 2
    f = np.fft.rfftfreq(len(s), 1 / SR)
    t = S.sum() + 1e-30
    return [10 * np.log10(S[(f >= lo) & (f < hi)].sum() / t + 1e-20) for lo, hi in BANDS], (f * S).sum() / t


def analyse(tag, path):
    x = load(path)
    env = envelope(x)
    vi, level = find_vowel(env)
    if vi <= 2:
        print(f"  {tag:8} 找不到辅音段")
        return
    pre = env[:vi]
    on = int(np.argmax(pre > level * 0.05))
    hop = int(SR * FRAME_MS / 1000)
    cons = x[on * hop:vi * hop]
    spec = spectrum(cons)
    db = 20 * np.log10(max(env[on:vi].max(), 1e-12) / max(level, 1e-12)) if vi > on else 0
    asp = 20 * np.log10(max(env[max(on, vi - int(50 / FRAME_MS)):vi].mean(), 1e-12) / max(level, 1e-12))
    cen = spec[1] if spec else 0
    shape = "".join(f"{20 * np.log10(max(v, 1e-12) / max(level, 1e-12)):5.0f}"
                    for v in env[on:vi + 4][:26])
    print(f"  {tag:8} 辅音 {(vi - on) * FRAME_MS:5.0f}ms  峰 {db:6.1f}dB  "
          f"尾段 {asp:6.1f}dB  质心 {cen:5.0f}Hz")
    print(f"  {'':8} {shape}")


def main():
    print("元音电平 = 包络 75 百分位；dB 均相对它。每格 2ms。\n")
    for bank, (d, enc, files) in BANKS.items():
        print(f"=== {bank} ===")
        for lab, fn in files.items():
            p = os.path.join(d, fn)
            if os.path.exists(p):
                analyse(lab, p)
        print()


if __name__ == "__main__":
    main()
