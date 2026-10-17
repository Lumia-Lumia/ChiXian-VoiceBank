"""普通话音节表与拼音拆分。

音节的清单取自 mandarin-reclist 的 `presamp.ini`（CVVC_Full 的 VOWEL 段），
共 416 个 —— 这是该规范认定「普通话里真实存在」的全部音节，包含 biang /
dia / din / rua / cei / kei / tei / zhei / shei / sei / lo 这些罕见组合。

拆分的任务是把**拼写**还原成**声母 + 韵母**：

    zhuang  → zh + uang
    jue     → j  + ve      （j/q/x 后面的 u 实际是 ü）
    liu     → l  + iou     （iu / ui / un 是缩写）
    zhi     → zh + ir      （舌尖后）
    zi      → z  + i0      （舌尖前）
    you     → "" + iou     （y/w 只是零声母音节的拼写规则）

零声母音节（a / ya / wa / yu …）没有辅音，直接渲染韵母本身，多个拼写可以
共用一个采样，靠别名区分。
"""

# 声母（按长度排序，保证 zh/ch/sh 先于 z/c/s 匹配）
INITIALS = ["zh", "ch", "sh", "b", "p", "m", "f", "d", "t", "n", "l",
            "g", "k", "h", "j", "q", "x", "r", "z", "c", "s"]

# 零声母：y / w 开头以及纯元音开头的写法 → 韵母
ZERO_Y = {
    "yi": "i", "ya": "ia", "ye": "ie", "yao": "iao", "you": "iou",
    "yan": "ian", "yin": "in", "yang": "iang", "ying": "ing",
    "yong": "iong", "yo": "io", "yai": "ia",
    "yu": "v", "yue": "ve", "yuan": "van", "yun": "vn",
}
ZERO_W = {
    "wu": "u", "wa": "ua", "wo": "uo", "wai": "uai", "wei": "uei",
    "wan": "uan", "wen": "uen", "wang": "uang", "weng": "ueng",
}
ZERO_VOWEL = {
    "a": "a", "o": "o", "e": "e", "ai": "ai", "ei": "ei", "ao": "ao",
    "ou": "ou", "an": "an", "en": "en", "ang": "ang", "eng": "eng", "er": "er",
}

# 拼音缩写。j/q/x 后面写 u，实际是 ü。
JQX = {"u": "v", "ue": "ve", "uan": "van", "un": "vn"}
NL = {"ue": "ve", "ve": "ve"}          # lüe / nüe 的两种写法
ABBREV = {"iu": "iou", "ui": "uei", "un": "uen"}

# 舌尖元音：只出现在这三组声母后面
APICAL_RETROFLEX = {"zh", "ch", "sh", "r"}
APICAL_DENTAL = {"z", "c", "s"}

# 416 个合法音节（空格分隔，方便肉眼核对条数）
_ALL = """
a ai an ang ao ba bai ban bang bao bei ben beng bi bian biang biao bie bin bing
bo bu ca cai can cang cao ce cei cen ceng cha chai chan chang chao che chen cheng
chi chong chou chu chua chuai chuan chuang chui chun chuo ci cong cou cu cuan cui
cun cuo da dai dan dang dao de dei den deng di dia dian diang diao die din ding diu
dong dou du duan dui dun duo e ei en eng er fa fan fang fei fen feng fo fou fu ga
gai gan gang gao ge gei gen geng gong gou gu gua guai guan guang gui gun guo ha hai
han hang hao he hei hen heng hong hou hu hua huai huan huang hui hun huo ji jia jian
jiang jiao jie jin jing jiong jiu ju juan jue jun ka kai kan kang kao ke kei ken
keng kong kou ku kua kuai kuan kuang kui kun kuo la lai lan lang lao le lei leng li
lia lian liang liao lie lin ling liu lo long lou lu luan lue lun luo lv ma mai man
mang mao me mei men meng mi mian miao mie min ming miu mo mou mu na nai nan nang
nao ne nei nen neng ni nia nian niang niao nie nin ning niu nong nu nuan nue nun
nuo nv ou pa pai pan pang pao pei pen peng pi pian piao pie pin ping po pou pu qi
qia qian qiang qiao qie qin qing qiong qiu qu quan que qun ran rang rao re ren
reng ri rong rou ru rua ruan rui run ruo sa sai san sang sao se sei sen seng sha
shai shan shang shao she shei shen sheng shi shou shu shua shuai shuan shuang shui
shun shuo si song sou su suan sui sun suo ta tai tan tang tao te tei teng ti tian
tiao tie ting tong tou tu tuan tui tun tuo wa wai wan wang wei wen weng wo wu xi
xia xian xiang xiao xie xin xing xiong xiu xu xuan xue xun ya yai yan yang yao ye
yi yin ying yong you yu yuan yue yun za zai zan zang zao ze zei zen zeng zha zhai
zhan zhang zhao zhe zhei zhen zheng zhi zhong zhou zhu zhua zhuai zhuan zhuang
zhui zhun zhuo zi zong zou zu zuan zui zun zuo
"""

SYLLABLES = _ALL.split()


def split(s):
    """把一个拼音音节拆成 (声母, 韵母)。零声母时声母为空串。

    声母和韵母的键都是 ASCII 字符串：声母对应 `phonemes.CONSONANTS`
    （zh / ch / sh / z / c / s / j / q / x / r / f / …），韵母对应
    `phonemes.FINALS`。
    """
    if s in ZERO_Y:
        return "", ZERO_Y[s]
    if s in ZERO_W:
        return "", ZERO_W[s]
    if s in ZERO_VOWEL:
        return "", ZERO_VOWEL[s]

    ini = ""
    rest = s
    for cand in INITIALS:
        if s.startswith(cand):
            ini, rest = cand, s[len(cand):]
            break

    if ini in ("j", "q", "x"):
        rest = JQX.get(rest, rest)
        if rest == "iu":
            rest = "iou"      # jiu / qiu / xiu：这里的 iu 是 iou，不是 ü
    else:
        if ini in ("n", "l"):
            rest = NL.get(rest, rest)
        rest = ABBREV.get(rest, rest)

    if rest == "i":
        if ini in APICAL_RETROFLEX:
            rest = "ir"
        elif ini in APICAL_DENTAL:
            rest = "i0"

    return ini, rest


def table():
    """[(别名, 声母, 韵母), ...]，顺序与 reclist 一致。"""
    return [(s,) + split(s) for s in SYLLABLES]
