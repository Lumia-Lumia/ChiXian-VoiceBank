"""实验脚本的输出目录与写文件工具。

每个实验脚本独占 `demo/` 下的一个主题目录。**每次运行前必须先清空** ——
脚本只往里写、从不删除的话，一旦改了变体名，旧变体仍留在磁盘上，
新旧两套混在同一个目录里，试听时分不清哪组是哪组。

这个坑反复出现过三次（out/ 的残留 WAV、demo/click、demo/09_噪声源），
所以统一到这里，脚本开头调用一次 `fresh(OUT)` 即可。

写文件统一走 `write()`：**前后各补 100ms 静音**。爆破音的起音紧贴第 0 采样，
播放器一开声就碰上硬边、尾巴还会被截断；补上一个前后等长的静音段之后，
可以直接用普通媒体播放器逐条点开，既不会错过开头，也不会听出咔哒声。
"""

import os
import shutil

import numpy as np

import config as C
import dsp

PAD_HEAD_MS = 100.0
PAD_TAIL_MS = 100.0


def fresh(path):
    """清空并重建目录。返回该路径。"""
    if os.path.isdir(path):
        shutil.rmtree(path)
    os.makedirs(path, exist_ok=True)
    return path


def write(path, audio):
    """写试听样本：前后补静音。"""
    n0 = int(round(PAD_HEAD_MS / 1000.0 * C.SR))
    n1 = int(round(PAD_TAIL_MS / 1000.0 * C.SR))
    padded = np.concatenate([np.zeros(n0), np.asarray(audio, dtype=float),
                             np.zeros(n1)])
    dsp.write_wav(path, padded)
