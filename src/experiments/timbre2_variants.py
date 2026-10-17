"""三档高频方案对比，输出到 demo/timbre2/。

背景：逐频带实测发现，我们与参考的差距**不在 1~3kHz，而在 4kHz 以上**
（全线低 19~26dB）。所以这一轮改的是：

  * 压掉 2.5~4kHz 的多余能量（PEAK_DB 从 +12 改成 -4）
  * 新增谐波空气（声源高通后直接叠加，给「光泽」）
  * 提高噪声空气并降到 4kHz 高通（给「气息」）

三档只在两个空气路径的配比上不同，其余完全一样：
    V1_平衡   谐波 0.14 / 噪声 0.010
    V2_谐波   谐波 0.22 / 噪声 0.006   更「金属光泽」
    V3_气息   谐波 0.09 / 噪声 0.020   更「气声」
"""

import os
import sys

# 实验脚本在子目录里，而合成模块在上一级（src/）。从项目根目录运行时
# 脚本所在目录会被加进 sys.path，但 src/ 不会，所以这里补一条。
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

import config as C
import dsp
import render

OUT = os.path.join("demo", "timbre2")

VARIANTS = {
    "V1_平衡": dict(harm=0.14, air=0.010),
    "V2_谐波": dict(harm=0.22, air=0.006),
    "V3_气息": dict(harm=0.09, air=0.020),
}

# 每种方案各渲一遍元音与几个带辅音的音节
ITEMS = ["a", "i", "u", "e", "o", "ba", "da", "ga", "sa", "ta"]


def main():
    for name, p in VARIANTS.items():
        d = os.path.join(OUT, name)
        os.makedirs(d, exist_ok=True)
        render.HARM_AIR_LEVEL = p["harm"]
        render.AIR_LEVEL = p["air"]
        for it in ITEMS:
            if len(it) == 1:
                x, _ = render.render_vowel(it, 262.0)
            else:
                x, _ = render.render_cv(it[0], it[1], 262.0)
            x = dsp.normalize(x, dsp.rms(x), C.VOICED_RMS_DBFS, C.PEAK_CEILING)
            dsp.write_wav(os.path.join(d, f"{it}.wav"), x)
        print(f"{name}: {len(ITEMS)} 个样本")
    print(f"输出目录：{OUT}")


if __name__ == "__main__":
    main()
