"""量参考声库里爆破音的结构，用来对照调我们自己的爆破参数。

    python src/experiments/plosive_ref.py

对每个样本量四件事：

    闭合   从有声/有噪开始到起爆之间的低电平段长度
    起爆   起爆峰的相对电平（dB，相对元音稳态）与谱质心
    送气   起爆到元音稳定之间的长度，以及这段的电平走向
    升沿   起爆峰之后多少毫秒进入元音

只做测量，不写文件。
"""

import os
import sys
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SR = 44100
FRAME = 0.005          # 包络帧长 5ms


def load(path):
    with wave.open(path, "rb") as w:
        n = w.getnframes()
        sw = w.getsampwidth()
        raw = w.readframes(n)
        ch = w.getnchannels()
    if sw == 1:                         # 8 位 WAV 是无符号的，128 为零点
        x = (np.frombuffer(raw, dtype=np.uint8).astype(float) - 128.0) / 128.0
    elif sw == 2:
        x = np.frombuffer(raw, dtype="<i2").astype(float) / 32768.0
    elif sw == 3:                       # 24 位：补一个字节再按 32 位读
        b = np.frombuffer(raw, dtype=np.uint8)
        b = b[:len(b) // 3 * 3].reshape(-1, 3)
        v = (b[:, 0].astype(np.int32)
             | (b[:, 1].astype(np.int32) << 8)
             | (b[:, 2].astype(np.int32) << 16))
        v = np.where(v >= 1 << 23, v - (1 << 24), v)
        x = v.astype(float) / float(1 << 23)
    else:
        x = np.frombuffer(raw, dtype="<i4").astype(float) / 2 ** 31
    if ch == 2:
        x = x.reshape(-1, 2).mean(1)
    return x


def envelope(x):
    hop = int(SR * FRAME)
    n = len(x) // hop
    return np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(1))


def centroid(x):
    if len(x) < 256:
        return 0.0
    s = x * np.hanning(len(x))
    S = np.abs(np.fft.rfft(s))
    f = np.fft.rfftfreq(len(s), 1 / SR)
    return float((f * S ** 2).sum() / max((S ** 2).sum(), 1e-20))


def profile(x):
    env = envelope(x)
    if env.max() <= 0:
        return None
    level = float(np.percentile(env, 90))     # 元音电平（中位数会被收尾衰减拉低）
    if level <= 0:
        return None
    # 起爆起点：第一帧超过元音的 5%
    on = int(np.argmax(env > level * 0.05))
    # 元音起点：其后连续 20ms 都超过元音的 60%
    hold = int(0.02 / FRAME)
    vowel = len(env) - 1
    for i in range(on + 1, max(on + 1, len(env) - hold)):
        if np.all(env[i:i + hold] > level * 0.6):
            vowel = i
            break
    # 起爆峰：起点之后 40ms 内、元音之前
    hi = min(vowel, on + int(0.04 / FRAME))
    bp = on + int(np.argmax(env[on:max(hi, on + 1)]))
    # 质心只取起爆那一小段，避免把后面的元音算进来
    a = int(on * FRAME * SR)
    b = min(len(x), int(bp * FRAME * SR) + int(0.004 * SR))
    cen = centroid(x[a:b])
    return dict(
        onset_ms=on * FRAME * 1000,
        burst_ms=bp * FRAME * 1000,
        vowel_ms=vowel * FRAME * 1000,
        asp_ms=max(0.0, (vowel - bp) * FRAME * 1000),
        burst_db=20 * np.log10(max(env[bp], 1e-9) / level),
        centroid=cen,
    )


def show(tag, path):
    p = profile(load(path))
    if p is None:
        print(f"  {tag:8} 空文件")
        return
    print(f"  {tag:5} 起爆@{p['burst_ms']:4.0f}ms  "
          f"电平 {p['burst_db']:+5.1f}dB   "
          f"→元音 {p['asp_ms']:4.0f}ms   "
          f"质心 {p['centroid']:5.0f}Hz")


TETO = "ref/banks/teto/重音テト音声ライブラリー/重音テト単独音"
KUMI = "ref/banks/hitsuboku-kumi-chn/A4"


def main():
    print("重音テト（日语 CV，D#4）")
    for kana, name in [("ぱ", "pa"), ("た", "ta"), ("か", "ka"),
                       ("ば", "ba"), ("だ", "da"), ("が", "ga"), ("あ", "a")]:
        p = os.path.join(TETO, f"_{kana}.wav")
        if os.path.exists(p):
            show(name, p)

    print("\nHitsuboku Kumi（中文 CVVC，A4）")
    for syl in ["ba", "pa", "da", "ta", "ga", "ka"]:
        p = os.path.join(KUMI, f"_{syl}_{syl}.wav")
        if os.path.exists(p):
            show(syl, p)

    print("\n本声库（中文，D#4）")
    for syl in ["ba", "pa", "da", "ta", "ga", "ka"]:
        p = f"out/chixian/D#4/{syl}.wav"
        if os.path.exists(p):
            show(syl, p)


if __name__ == "__main__":
    main()
