# 参考音源与规范 —— 调研笔记

> 2026-10-16。本文件记录已下载的资料位置与实证结论。

## 一、已下载的资料

```
ref/
  mandarin-reclist/          # 中文 CVVC 录音表 + oto 模板 + 完整文档（4.3 MB）
    Reclist/                 #   录音表本体（Full 88 行 / Lite 62 / Nano 60 / Extra 23）
    UTAU/Full|Lite|Nano/     #   oto_CV.ini / oto_VC.ini / presamp.ini 模板
    UTAU/ZH_CVVC_with_replace.cs   # OpenUtau 中文 CVVC 音素器源码
    docs/                    #   文档：recording / producing / pronunciation /
                             #         simplification / using / generator
  teto/                      # 重音テト 統合版（日语 CV+VCV，90.8 MB）
    重音テト音声ライブラリー/
      重音テトエクストラ     16 wav / 39 oto
      重音テト単独音(CV)    142 wav / 319 oto
      重音テト連続音(VCV)   249 wav / 887 oto
  hitsuboku-kumi-chn/        # Hitsuboku Kumi 中文 CVVC（稀疏检出，A4 音阶 1361 wav）
  extract_sjis.py            # 解压 Shift-JIS 文件名的 zip（UTAU 日语音源常见）
```

另有本机已装的 UTAU：**`D:\UTAU\`**，默认音源（デフォ子）在 `D:\UTAU\voice\uta\`。

Hitsuboku Kumi 只取了 A4 一个音阶（4 音阶全取要大 4 倍）。需要别的音阶时：

```
cd ref/hitsuboku-kumi-chn && git sparse-checkout add D4
```

**授权**：重音テト官方免费（非商用）；Hitsuboku Kumi 商用/再分发/改 oto.ini 均无需许可
（需保留名称、署名 Cubialpha、附链接、声明改动）；mandarin-reclist 为公开录音表。
初音ミク / 洛天依是商业制品，未下载。

本项目纲领写明「不使用任何录制音频」，这些音源**只作结构与规范参考，不取其采样**。

**下载踩过的坑**：本机直连时 GitHub 443 不通、其余站点仅 14~33 KB/s；开 VPN 后提到
400+ KB/s。大文件用 `curl -C - --retry 20 --retry-all-errors` 断点续传（中途断过一次）；
git clone 用 `--depth 1 --filter=blob:none --sparse` 并设 `http.version HTTP/1.1`
（默认 HTTP/2 会 `RPC failed; curl 92`）。

---

## 二、oto.ini 的字段语义（用三个真实声库实证）

格式：`wav文件名=别名, 左边界, 固定区长度, 右边界, 先行发声, 重叠`

对三个真实声库逐条比对 wav 实际时长：

| 声库 | 条目 | 「右边界距末尾」成立率 | 「右边界从 offset 起算」成立率 | 固定区 > 先行发声 |
|---|---|---|---|---|
| デフォ子（默认音源 CV） | 148 | **100%** | 9% | **100%** |
| 重音テト 単独音（CV） | 319 | **100%** | 9% | **100%** |
| 重音テト 連続音（VCV） | 887 | **100%** | 57% | **100%** |

### 结论一：固定区 = [左边界, 左边界+固定区长度]，从 offset 起算

若改成「从先行发声点起算」，成立率立刻掉到 9% / 57%。**这是确定的。**

### 结论二：右边界 = 距文件末尾的距离，且**符号会改变含义**

> **§这里我犯过一个错，值得记下来。§**

第一轮统计我用了 `|右边界|` 去做检验，成立率 100% / 95% / 100%，于是得出「UTAU 按
绝对值处理、符号无所谓」的结论 —— **错的**。`abs()` 把符号抹掉了，恰好两派写法都能
通过那个检验，所以检验本身没有区分力。

真实规则（OpenUtau 文档写得很明白）：

| 符号 | 含义 |
|---|---|
| **正值** | 距**文件末尾**的距离 |
| **负值** | 从 **offset 起算的长度** |

デフォ子、重音テト単独音用的都是正值，检验成立率 100%。

**这个错误在实际渲染时暴露了**：我们用 `-55`，含义变成「可用区只有 55ms 长」，
于是除纯元音外（固定区 40ms）全部采样被整个吃掉，UTAU 渲染出静音 ——
表现为「只有 `a` 有声音，`ba`/`ka`/`pa` 等全部无声」。改成 `+55` 后解决。

**教训**：统计检验要挑有区分力的量。用 `abs()` 会抹掉正是要检验的那个维度。

### 结论三：固定区长度恒大于先行发声（1354 条无一例外）

`oto.py` 早期版本令两者相等，注释理由是「两种解释在采样起点重合时等价」——
**那个理由是错的**，两者是互相独立的量。保留相等只是一个自洽的特例
（固定区恰好覆盖到元音起点），并非通例。注释已改。

### 顺带：Teto 的别名布局

同一个 wav 挂 1~3 条别名，用前缀区分使用场景：

```
_あ.wav=あ,24,56,73,5,20        ← 常规（跟在别的音后面）
_あ.wav=- あ,24,56,73,5,20      ← - 前缀
_あ.wav=* あ,78,100,73,50,100   ← * 前缀（句首）：offset 更靠后，跳过元音起音
```

文件名带 `_` 前缀是 UTAU 的文件命名习惯，**不是别名的一部分**。

---

## 三、中文 CVVC 的别名规范（来自 mandarin-reclist）

### 3.1 `#` 是音阶后缀占位符，不是别名的一部分

> 每个标注后边都有一个 `#`，这是方便后续**替换音阶后缀**的地方。

单音阶声库里 `ba#` 就写作 `ba`。**我们的命名没问题。**

### 3.2 VC 别名 = 「前一音节的韵母」+「后一音节的声母」

```
a p#      i0 q#      eng y#      en e#      i sh#      ir ou#
```

前半是前一音节的**完整韵母**（不只是元音）。我们目前只有 5 个单韵母，
所以 `a b` / `i p` 这类写法**在现有范围内是正确的**；加复韵母以后才需要展开。

### 3.3 §重要§ VC 里不送气塞音要被送气塞音替代

> 由于爆破音的 VC 中实际不包含辅音，因此**以送气爆破音替代不送气爆破音**

即 **b→p、d→t、g→k**。在 `oto_NanoVC.ini` 的 `_ba_pa_ma_fa_da_ta_na_la` 那条线里
只有 `a p` / `a m` / `a f` / `a t` / `a n` / `a l`，**没有 `a b` 也没有 `a d`**。

我们的 VC 集合是 5 元音 × 11 声母 = 55，其中 b/d/g 的 15 条是多余的，应为 40 条。

### 3.4 规模参考

| | CV 总数 | 韵尾 | VC 后续类 |
|---|---|---|---|
| CVVC_Full | **274** | 23 | 18 辅音 + 6 零声母元音 = 24 |
| CVVC_Lite / Nano | 259 | 14 / 13 | 同上 |

VC 的 18 个辅音是：`c ch f h k l m n p q r s sh t V w x y`
（`V` 是半元音 ü，`y`/`w` 是 i-/u- 介音单独成音节时的辅音）。
6 个零声母元音：`a ao e ei ou er`。

我们目前只有 11 个声母（b p m d t n l g k h s）→ VC 侧实际只对应
**8 类**（p m t n l k h s）。

### 3.5 其它约定

- **`ü` 在 oto 文件里写作 `v`**（`y`/`w`/`v` 都是半元音）
- **`i0`**（zi/ci/si）与 **`ir`**（zhi/chi/shi/ri）是两个舌尖元音，我们完全没有
- 一条录音线 = 8 个音节连续念，靠 offset 切片。**对引擎而言「一音节一文件」等效**，
  我们是合成，保持现状即可
- `Extra` 表是句首/句尾/长音专用素材（`_a_IN_a_OUT_a_L_R`）

---

## 四、对我们的结论

1. **合成路线与产物布局不用改。**
2. **别名体系**：现有范围内基本正确，需要修正的是 **VC 要剔除 b/d/g 三条**（→ p/t/k）。
3. **要扩张才需要动的**：补 `i0` / `ir` / 复韵母 / 其余声母（z c s zh ch sh j q x f r）。
4. **`oto.py` 的 consonant 语义要改注释**，并考虑把「固定区长度」与「先行发声」
   拆成两个独立参数。
5. **右边界符号**在 SetParam 里确认一次。


---

## 五、工程文件（.ust）与英/俄声库（2026-10-17）

```
ref/
  TETO-English-150401.zip   83.8 MB  重音テト英语音源（官方，Delta 系，**带 presamp.ini**）
  Emerald V.3.6.0.zip      280.5 MB  俄语 CVC RUS，A3/C4/D#4，含 Eng 文件夹
  VCCV-RUS/                          俄语 VCCV 录音表 + oto.ini + LyricInputHelper 词典
  hhskt_ru_phonemizer/               OpenUTAU 俄语 G2P（C#），俄语音素表参考
  ust/
    zh/    32 个  来自 github.com/oxygen-dioxide/utau-projects，拼音别名
    en/    34 个  7 部英文作品，X-SAMPA 别名
    ru/    25 个  4 首俄语歌，CVC 别名
    other/  6 个  日语，误命中
```

### 英文工程里能对上的别名形态

`Old Town Road` 的歌词是 `& -I @ A E E- I R`，`We are Number One` 是
`-ba R ba bi du lE` —— 正是 Delta 式 `CV` / `- CV` / `V C` / `V C-` 的写法，
和我们 `english.py` 的实现一致。可以直接拿来验证 oto 参数。

### 俄语用 CVC，不是 CVVC

从 `New Darling CVC rus/Main1.ust` 读出的别名：

    -za | ab' | b'i | it | ta | ak | ka | an- | f'e | et | ta | a~-G3 | -qu | uk- | ro

规律：
* **`'` 表示软辅音**（palatalization），如 `b'i`、`f'e`、`at'-`
* **`-` 后缀表示词尾**（相当于 `V C-`），如 `an-`、`uk-`、`az-`
* `~` 表示鼻化，`R` 是休止符
* 元音直接跟在辅音后面，没有 CVVC 那种「V C」中间段 —— 所以俄语是 **CVC**

这和英文的 Delta CVVC 不同，做俄语时不能照搬英语的结构。

### 俄语资源怎么找

公开配布的俄语 UST 很少，搜索引擎基本搜不到。有效的路径是：

1. 先找到俄语声库/翻唱的发布视频（Rutube 比 YouTube 好抓，描述里的链接直接
   写在 HTML 里，不用解析 JS）
2. 从视频描述里的 mediafire/mega 链接取
3. `keirokeer.carrd.co` 这类作者主页会链到更多

踩过的坑：
* **MediaFire 的直链藏在文件页 HTML 里**（`https://download####.mediafire.com/...`），
  但连续快速请求会被拒，请求之间要留 4 秒左右
* **文件名要取 URL 里 `/file/<key>/<文件名>/file` 的倒数第二段**，
  取 basename 会得到 "file"，多个下载互相覆盖
* Google Drive 的 `uc?export=download` 遇到非公开文件会跳登录页
* mega.nz 不能直接 curl，要按它的 API + AES-CTR 解密，本批放弃了那两个

### Windows 自带 tar 能解 RAR

本机没装 WinRAR / 7-Zip，但 `C:\Windows\System32	ar.exe`（libarchive）支持
RAR v5：

    C:/Windows/System32/tar.exe -xf 包.rar

