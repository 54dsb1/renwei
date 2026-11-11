# -*- coding: utf-8 -*-
"""lint.py · 中文写作去 AI 味机械自检（humanize-zh v1.0）

只查"可机械判定"的项目；走神、判断失误、细节寄主这类义务项必须人工过 CORE §2.6。

用法
----
    python lint.py 稿件.md                     # 自动判文体
    python lint.py 稿件.md --genre args        # 指定文体 narr/args/offi
    python lint.py 稿件.md --profile my.json   # 用自校准档位
    python lint.py 稿件.md --json              # 机器可读输出
    python lint.py --dir 稿件目录/ --genre narr
    python lint.py --calibrate 人类语料/ --genre args --save-profile args.json

档位
----
    narr  叙事：故事、随笔、特写、纪实、公众号叙事文
    args  论说：评论、分析、说明文、报告、方案、演讲稿
    offi  公文：通知、总结、请示、会议纪要（只查腔调，多数节奏项不查）

退出码：0 全 PASS/WARN；1 存在 FAIL；2 参数或文件错误。
"""
import json
import re
import statistics
import sys
from pathlib import Path

GENRES = ("narr", "args", "offi")

# ---------------------------------------------------------------- 基础工具

CJK = re.compile(r"[\u4e00-\u9fff]")
SENT_END = re.compile(r"(?<=[。！？…])")
DLG_MARK = ("\u201c", "「", "\"")
MODAL = "呢吧啊嘛哦嗯呀啦咯呗诶"
SIMILE = "像|仿佛|如同|似的|宛如|犹如|好似"


def read_text(path):
    b = Path(path).read_bytes()
    for enc in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            continue
    return b.decode("utf-8", errors="ignore")


def body(path):
    """去掉 Markdown 标题行、分隔线、以及常见的备注区。"""
    t = read_text(path)
    lines = t.splitlines()
    if lines and lines[0].lstrip().startswith("#"):
        lines = lines[1:]
    b = "\n".join(lines)
    b = re.sub(r"(?m)^(?:---|===)\s*$", "", b)
    for mark in ("## 备注", "## 改写备忘", "## 手感备忘"):
        i = b.find(mark)
        if i >= 0:
            b = b[:i]
    return b.strip()


def cjk_len(s):
    return len(CJK.findall(s))


def disp_width(s):
    return sum(2 if ord(c) > 127 else 1 for c in s)


def pad(s, width):
    return s + " " * max(0, width - disp_width(s))


def paras_of(text):
    return [p.strip() for p in text.split("\n") if p.strip()]


def sents_of(text):
    return [s for s in SENT_END.split(text) if cjk_len(s) >= 1]


# ---------------------------------------------------------------- 指标计算

_TIME_MARK = re.compile(
    "凌晨|清晨|早上|上午|中午|下午|傍晚|晚上|夜里|半夜|"
    "周[一二三四五六日]|星期[一二三四五六日天]|"
    "[0-9一二三四五六七八九十]+点(?:[0-9一二三四五六七八九十]+分)?")

_BG_OPEN = re.compile(
    "随着[^。！？\\n]{0,24}(?:发展|推进|深入|加快|到来)|在当今|众所周知|自古以来|"
    "近年来|近年|进入[^。！？\\n]{0,8}时代|新时代以来|当下社会")

_SUBLIME = re.compile(
    "愿[^。！？\\n]{0,24}|未来可期|让我们一起|愿我们|祝愿|"
    "相信[^。！？\\n]{0,16}(?:会|一定|终将)|希望[^。！？\\n]{0,16}(?:都能|能够|可以)|"
    "每一个[^。！？\\n]{0,14}都")

_SUMUP = re.compile("总之|综上|归根结底|说到底|总的来看|总体而言|一言以蔽之|简而言之")
_META = re.compile(
    "本文认为|本文认为|本文|本节|接下来(?:我|我们)?(?:将|会|分)|如前述|如前所述|"
    "需要指出的是|这一点很重要|下面我们")
_NOTX = re.compile("不是[^。！？\\n]{1,20}?而是")
_NOTONLY = re.compile("不仅[^。！？\\n]{1,30}?而且|既[^。！？\\n]{1,24}?又|之所以[^。！？\\n]{1,24}?是因为")
_META_PHRASE = re.compile("值得注意的是|不难发现|不难看出|事实上|可以说|需要注意的是|由此可见|换句话说")
_FAKE = re.compile(
    "你有没有发现|让我们一起|我们都知道|相信你也|不妨想想|你是否也曾|"
    "你会不会也|很多人问我|经常有人问")
_JARGON = re.compile(
    "赋能|抓手|闭环|底层逻辑|生态位|生态|范式|颗粒度|组合拳|护城河|"
    "顶层设计|方法论|协同|沉淀|复用|打通|落地|对齐|维度|形成合力")
_DE_CHAIN = re.compile("的[^，。！？\\n]{1,5}的[^，。！？\\n]{1,5}的")
_AA = re.compile(r"([^，。！？\n]{2,4})，\1(?:[^，。！？\n]{0,6})?[。！？\n]")
_REP_V = re.compile(r"(.)过[^，。！？\n]{1,12}，\1过")
_MIRROR = re.compile("(.)了又(.)，\\2了又\\1")
_TOPEN = re.compile(r"([^，。！？]{1,6})，(?:还是|也是|又是)\1")
_SAMEHEAD = re.compile(
    r"([^，。！？\n]{2,3})[^，。！？\n]{0,8}[，,]\1[^，。！？\n]{0,8}[，,]\1")
_HEAD_STOP = set("我你他她它这那就都是不也都很又在有的了着过还")
_DUIZHANG = re.compile(
    "[^。！？\\n\\u201c照]{0,6}照(?!旧|样|常|例|片|按|相|顾|看|明|办|理|会|料|射|耀|亮|眼|"
    "面|门|墙|台|图|准|错|实|说|做|管|他|她|它|我|你)[^，。！？\\n]{1,4}，"
    "[^。！？\\n\\u201c]{1,8}照(?!旧|样|常|例|片|按|相|顾|看|明|办|理|会|料|射|耀|亮|眼|"
    "面|门|墙|台|图|准|错|实|说|做|管|他|她|它|我|你)[^，。！？\\n]{1,4}[。！？]")
_HUIHUAN = re.compile("没人[管理问睬][，,][^。！？\\n]{0,10}(?:也不|都没|也没)")
_XUANZHI = re.compile("至于是[^。！？\\n\\u201c]{0,16}(?:没讲|没说|没问|没提)")
_ORD3 = re.compile("先[^。！？\\n]{0,18}然后[^。！？\\n]{0,18}最后")
_GUANYU = re.compile("关于[^，。！？\\n]{1,10}，关于[^，。！？\\n]{1,10}")
_HANGXING = re.compile("干这行[^。！？\\n]{0,10}头一回")
_APH_ASSERT = re.compile("就是|没人|才知道|没人告诉|无人|不过是|无非是|才对|才怪")
_APH_ACT = re.compile("拿|提|搬|推|卷|塞|掏|摁|掐|补|系|解|盘|绞|洗|擦|翻|抄|写|画|数|切|倒|"
                      "撒|捆|走|坐|站|看|望|问|说|喊|转|开|压|停|想|记")

_DEFLECT = re.compile(
    "说不好|不好说|不好讲|看情况|再等等|等通知|等消息|到时候再说|到时候看|别多想|"
    "不好答|还没定|还没准|谁知道|不好确定|再看看|没个准|看安排")
_POLITE = re.compile(
    "客客气气|客气话|客套话|赔个不是|赔不是|笑眯眯|堆笑|陪着笑|满脸堆笑|职业笑容|"
    "礼貌地|客气地")
_SPEECH_V = re.compile(
    "(?<![没不别问我告])问(?!号|题|候|世|津)|(?<![没不别说])说(?!明|话|法|不定|着|服|白|实话|起来|一|长|短|笑|来|去|定)|"
    "(?<![没不别他])答(?!应|案|卷|疑)|(?<![没不别知])道(?![理具路谢])")
_QUOTED = re.compile("\u201c([^\u201d]{4,})\u201d")
_REGWORD = re.compile("按规定|按程序|依据|流程|审批|报批|备案|复核|留档|入档|口径|复现|归档|批示")

_NOTE = re.compile(
    "(?m)^\\s*#{1,3}\\s*(?:备注|改写备忘|手感备忘|说明)$|【待补】|【改】|TODO|待补充|"
    "语料标记|抽样说明")

_WEIGH = ["就", "是", "才", "还", "都", "把", "往", "被", "向", "对", "让", "给", "地"]


_DI_EXCL = re.compile("地方|地区|地址|地点|地上|地下|地图|地位|地理|地毯|地铁|地板")


def _di_density(text):
    """状语[地]按字计（jieba 常把"地"并入前词，词计会失真）。"""
    n = max(1, cjk_len(text))
    c = text.count("地") - len(_DI_EXCL.findall(text))
    return {"w_地": max(0, c) / n * 1e4}


def _char_density(text, words):
    """按字计（与人类基线口径一致：101-04 文档里的分位数就是字频）。

    不用分词：jieba 会把"就是/才能/但是"并成一个词，导致虚词频次系统性偏低一半，
    反而让正常人的稿子被判"缺词"。
    """
    n = max(1, cjk_len(text))
    return {f"w_{w}": text.count(w) / n * 1e4 for w in words}


def _sent_sd(sents):
    ls = [cjk_len(s) for s in sents if cjk_len(s) >= 2]
    if len(ls) < 10:
        return 0.0
    return statistics.pstdev(ls)


def _narr_only(text):
    """去掉直接引语，只留叙述位（用于修辞类检查）。"""
    t = re.sub("“[^”]*”", "", text)
    return re.sub("「[^」]*」", "", t)


def _aphor_count(text):
    t2 = re.sub("\u201c[^\u201d]*\u201d", "", text)
    hits = 0
    for s in re.split(r"[。！？\n]", t2):
        s = s.strip()
        if 0 < cjk_len(s) <= 18 and _APH_ASSERT.search(s) and not _APH_ACT.search(s):
            hits += 1
    return hits


def metrics(text):
    n = max(1, cjk_len(text))
    paras = paras_of(text)
    pn = max(1, len(paras))
    sents = sents_of(text)
    sn = max(1, len(sents))

    one = sum(1 for p in paras if len([s for s in SENT_END.split(p) if cjk_len(s) >= 1]) <= 1)
    short = sum(1 for p in paras if cjk_len(p) <= 15)
    dlg_paras = [p for p in paras if any(k in p for k in DLG_MARK) and cjk_len(p) < 160]
    dl = sum(1 for p in paras if any(k in p for k in DLG_MARK) and cjk_len(p) < 160)
    comma = sum(p.count("\uff0c") for p in paras)
    plen = [cjk_len(p) for p in paras if cjk_len(p) > 0]
    pmean = sum(plen) / max(1, len(plen))
    pcv = (statistics.pstdev(plen) / pmean) if len(plen) > 2 and pmean else 0.0

    slen = [cjk_len(s) for s in sents]
    run3 = max((sum(slen[i:i + 3]) / 3 for i in range(len(slen) - 2)), default=0.0)

    # 开头/结尾
    head = text[:600]
    first = paras[0] if paras else ""
    tail, acc = [], 0
    for p in reversed(paras):
        tail.insert(0, p)
        acc += cjk_len(p)
        if acc >= 400:
            break
    tail_text = "\n".join(tail)
    last = paras[-1] if paras else ""

    # 对话内容
    is_dlg = [bool(any(k in p for k in DLG_MARK) and cjk_len(p) < 160) for p in paras]
    deflect = {}
    for p, d in zip(paras, is_dlg):
        if d:
            for m in _DEFLECT.findall(p):
                deflect[m] = deflect.get(m, 0) + 1
    long_ans = sum(1 for i in range(1, len(paras))
                   if is_dlg[i] and is_dlg[i - 1] and "？" in paras[i - 1] and cjk_len(paras[i]) >= 50)
    pack = 0
    for sent in re.split(r"[。！？…\n]", text):
        if "\u201c" in sent or not sent.strip():
            continue
        s2 = re.sub("说道|问道|答道|叫道|喊道|笑道|骂道|吼道|叹道|回道", "说", sent)
        if len(_SPEECH_V.findall(s2)) >= 2:
            pack += 1
    qa_run = cur = 0
    for i in range(1, len(paras)):
        if is_dlg[i - 1] and "？" in paras[i - 1] and is_dlg[i]:
            cur += 1
            qa_run = max(qa_run, cur)
        elif is_dlg[i - 1]:
            cur = 0
    quoted = _QUOTED.findall(text)
    qseen = {}
    for q in quoted:
        qseen[q] = qseen.get(q, 0) + 1
    reg_in_dlg = 0
    dlg_chars = 0
    for p, d in zip(paras, is_dlg):
        if d:
            dlg_chars += cjk_len(p)
            reg_in_dlg += len(_REGWORD.findall(p))

    narr = _narr_only(text)
    m = {
        "cjk": n,
        "ascii_quote": float(text.count('"')),
        "ascii_single": float(text.count("'")),
        "ellip_dots": float(len(re.findall(r"\.{2,}", text))),
        "dash_1e4": len(re.findall("\u2014\u2014|--", text)) / n * 1e4,
        "bang_1e4": text.count("\uff01") / n * 1e4,
        "ques_1e4": text.count("\uff1f") / n * 1e4,
        "ellip_1e4": text.count("\u2026\u2026") / n * 1e4,
        "para_mean": pmean,
        "para_cv": pcv,
        "sent_mean": n / sn,
        "sent_sd": _sent_sd(sents),
        "comma_per_sent": comma / sn,
        "one_sent": one / pn,
        "short15": short / pn,
        "max3run": run3,
        "dlg_para": dl / pn,
        "simile_1e4": len(re.findall(SIMILE, text)) / n * 1e4,
        "modal_1e4": sum(text.count(c) for c in MODAL) / n * 1e4,
        # 结构位
        "open_para1": float(cjk_len(first)),
        "open_bg": float(len(_BG_OPEN.findall(head))),
        "end_para": float(cjk_len(last)),
        "end_sublime": float(len(_SUBLIME.findall(last))),
        # 修辞
        "r_aa": float(len(_AA.findall(narr))),
        "r_repv": float(len(_REP_V.findall(narr))),
        "r_mirror": float(len(_MIRROR.findall(text))),
        "r_topin": float(len(_TOPEN.findall(narr))),
        "r_samehead": float(sum(1 for mm in _SAMEHEAD.finditer(narr)
                                if mm.group(1)[0] not in _HEAD_STOP)),
        "r_duizhang": float(len(_DUIZHANG.findall(text))),
        "r_huihuan": float(len(_HUIHUAN.findall(text))),
        "r_xuanzhi": float(len(_XUANZHI.findall(text))),
        "r_notx_1k": len(_NOTX.findall(text)) / n * 1000,
        "r_notonly_1k": len(_NOTONLY.findall(text)) / n * 1000,
        "r_metaphrase": float(len(_META_PHRASE.findall(text))),
        "r_sumup": float(len(_SUMUP.findall(text))),
        "r_fake": float(len(_FAKE.findall(text))),
        "r_aphor": float(_aphor_count(text)),
        "r_ord3": float(len(_ORD3.findall(text))),
        "r_guanyu": float(len(_GUANYU.findall(text))),
        "r_hangxing": float(len(_HANGXING.findall(text))),
        # 内容
        "c_jargon_1k": len(_JARGON.findall(text)) / n * 1000,
        "c_meta_1k": len(_META.findall(text)) / n * 1000,
        "c_dechain": float(len(_DE_CHAIN.findall(text))),
        "c_num_1k": len(re.findall(r"\d+(?:\.\d+)?", text)) / n * 1000,
        "g_note": 0.0,  # 需要查原文，lint_one 中覆写
        # 对话
        "d_deflect": float(sum(deflect.values())),
        "d_deflect_dup": float(sum(1 for v in deflect.values() if v >= 2)),
        "d_polite": float(len(_POLITE.findall(text))),
        "d_longans": float(long_ans),
        "d_pack": float(pack),
        "d_qarun": float(qa_run),
        "d_quotedup": float(sum(1 for v in qseen.values() if v >= 2)),
        "d_regword": (reg_in_dlg / max(1, dlg_chars)),
        "q_timemark": float(len(_TIME_MARK.findall(head))),
    }
    m.update(_char_density(text, _WEIGH))
    m.update(_char_density(text, ["得", "着", "了", "过", "又", "跟"]))
    m.update(_di_density(text))
    return m



# ---------------------------------------------------------------- 检查表
# (key, label, unit, kind, {genre: (fail, warn)})   kind: max/min/eq0
# None 表示该文体不查此项

N = None
CHECKS = [
    # ---- 字符与标点 ----
    ("ascii_quote", "ASCII 双引号", "处", "eq0", {"narr": (0, 0), "args": (0, 0), "offi": (0, 0)}),
    ("ascii_single", "ASCII 单引号", "处", "eq0", {"narr": (0, 0), "args": (0, 0), "offi": (0, 0)}),
    ("ellip_dots", "英文省略号...", "处", "eq0", {"narr": (0, 0), "args": (0, 0), "offi": (0, 0)}),
    ("dash_1e4", "破折号", "/万字", "max", {"narr": (10, 5), "args": (10, 5), "offi": (6, 3)}),
    ("bang_1e4", "感叹号", "/万字", "max", {"narr": (68, 45), "args": (40, 25), "offi": (20, 10)}),
    ("ques_1e4", "问号", "/万字", "min", {"narr": (22, 30), "args": N, "offi": N}),
    # ---- 节奏 ----
    ("para_mean", "段均字数", "字", "max", {"narr": (70, 45), "args": (90, 60), "offi": (120, 85)}),
    ("para_cv", "段长变异系数", "", "min", {"narr": (0.45, 0.60), "args": (0.40, 0.55), "offi": N}),
    ("sent_mean", "句长均值", "字", "min", {"narr": (18.0, 20.5), "args": (20, 24), "offi": N}),
    ("sent_sd", "句长标准差", "", "min", {"narr": (10.0, 13.0), "args": (8.0, 11.0), "offi": N}),
    ("comma_per_sent", "逗号/句", "", "min", {"narr": (0.80, 1.15), "args": (1.05, 1.15), "offi": (1.0, 1.1)}),
    ("one_sent", "单句成段占比", "", "min", {"narr": (0.15, 0.25), "args": (0.10, 0.18), "offi": (0.08, 0.15)}),
    ("short15", "≤15字短段占比", "", "min", {"narr": (0.10, 0.15), "args": (0.06, 0.10), "offi": N}),
    ("max3run", "最长连续三句均值", "字", "max", {"narr": (60, 45), "args": (85, 70), "offi": N}),
    # ---- 词法 ----
    ("w_就", "虚词[就]", "/万字", "min", {"narr": (20, 30), "args": (10, 18), "offi": (6, 12)}),
    ("w_是", "虚词[是]", "/万字", "min", {"narr": (70, 95), "args": (55, 80), "offi": N}),
    ("w_才", "虚词[才]", "/万字", "min", {"narr": (3, 6), "args": (2, 4), "offi": N}),
    ("w_还", "虚词[还]", "/万字", "max", {"narr": (55, 38), "args": (45, 32), "offi": N}),
    ("w_把", "把字句", "/万字", "max", {"narr": (32, 22), "args": (36, 26), "offi": N}),
    ("w_往", "介词[往]", "/万字", "max", {"narr": (16, 9), "args": (14, 8), "offi": N}),
    ("w_被", "被字句", "/万字", "min", {"narr": (4, 9), "args": N, "offi": N}),
    ("w_向", "介词[向]", "/万字", "min", {"narr": (3, 6), "args": N, "offi": N}),
    ("w_对", "介词[对]", "/万字", "min", {"narr": (13, 20), "args": N, "offi": N}),
    ("w_让", "使令[让]", "/万字", "min", {"narr": (4, 8), "args": N, "offi": N}),
    ("w_给", "介词[给]", "/万字", "min", {"narr": (3, 7), "args": N, "offi": N}),
    ("w_地", "状语[地]", "/万字", "min", {"narr": (0, 8), "args": (4, 9), "offi": N}),
    ("simile_1e4", "比喻词", "/万字", "max", {"narr": (20, 16.5), "args": (12, 8), "offi": (6, 3)}),
    ("modal_1e4", "语气词", "/万字", "min", {"narr": (8, 14), "args": N, "offi": N}),
    # ---- 修辞与设计感 ----
    ("r_aa", "AA复读 X，X。", "处", "max", {"narr": (1, 0), "args": (1, 0), "offi": (1, 0)}),
    ("r_repv", "二连同动词 X过，又X过", "处", "max", {"narr": (1, 0), "args": (1, 0), "offi": N}),
    ("r_mirror", "镜像四字格 X了又Y", "处", "max", {"narr": (1, 0), "args": (1, 0), "offi": N}),
    ("r_topin", "顶针叠句 X，还是X", "处", "max", {"narr": (1, 0), "args": (1, 0), "offi": N}),
    ("r_samehead", "三连排比/同头轮举", "处", "max", {"narr": (2, 1), "args": (3, 2), "offi": (3, 2)}),
    ("r_duizhang", "对仗收束 A照X B照Y", "处", "eq0", {"narr": (0, 0), "args": (0, 0), "offi": (0, 0)}),
    ("r_huihuan", "回环否定 没人管它它也不叫", "处", "max", {"narr": (3, 2), "args": (2, 1), "offi": N}),
    ("r_xuanzhi", "悬置句 至于是…没讲", "处", "max", {"narr": (2, 1), "args": (1, 0), "offi": N}),
    ("r_notx_1k", "句式[不是X而是Y]", "/千字", "max", {"narr": (2, 1), "args": (2, 1), "offi": (1.5, 0.8)}),
    ("r_notonly_1k", "句式[不仅…而且/既…又]", "/千字", "max", {"narr": (2, 1), "args": (2.5, 1.5), "offi": (2, 1)}),
    ("r_metaphrase", "套话[值得注意的是/事实上]", "处", "max", {"narr": (2, 1), "args": (4, 2), "offi": (4, 2)}),
    ("r_sumup", "总结句[总之/综上]", "处", "max", {"narr": (2, 1), "args": (3, 1), "offi": (3, 2)}),
    ("r_fake", "假互动[你有没有发现]", "处", "eq0", {"narr": (0, 0), "args": (0, 0), "offi": (0, 0)}),
    ("r_aphor", "金句/警句", "处", "max", {"narr": (2, 1), "args": (4, 2), "offi": N}),
    ("r_ord3", "骨架[先…然后…最后]", "处", "eq0", {"narr": (0, 0), "args": (0, 0), "offi": (0, 0)}),
    ("r_guanyu", "排比[关于X，关于Y]", "处", "eq0", {"narr": (0, 0), "args": (0, 0), "offi": (0, 0)}),
    ("r_hangxing", "套路[干这行+头一回]", "处", "eq0", {"narr": (0, 0), "args": N, "offi": N}),
    # ---- 结构位 ----
    ("open_para1", "首段字数", "字", "max", {"narr": (60, 30), "args": (100, 60), "offi": (120, 80)}),
    ("open_bg", "开篇背景套话", "处", "eq0", {"narr": (0, 0), "args": (0, 0), "offi": (0, 0)}),
    ("end_para", "末段字数", "字", "max", {"narr": (80, 50), "args": (160, 110), "offi": (160, 110)}),
    ("end_sublime", "末段升华/号召", "处", "eq0", {"narr": (0, 0), "args": (0, 0), "offi": (0, 0)}),
    # ---- 内容 ----
    ("c_jargon_1k", "抽象行话", "/千字", "max", {"narr": (2, 1), "args": (3, 1.5), "offi": (4, 2.5)}),
    ("c_meta_1k", "元注释[本文/接下来]", "/千字", "max", {"narr": (1, 0.5), "args": (2, 1), "offi": (2, 1)}),
    ("c_dechain", "连续[的]字链", "处", "max", {"narr": (2, 1), "args": (3, 1), "offi": (3, 2)}),
    ("c_num_1k", "阿拉伯数字密度", "/千字", "max", {"narr": (5, 3), "args": N, "offi": N}),
    ("g_note", "提纲/备注泄漏", "处", "eq0", {"narr": (0, 0), "args": (0, 0), "offi": (0, 0)}),
    # ---- 对话（仅在 narr 且对白段 ≥10% 时启用）----
    ("d_deflect", "含糊话术", "处", "max", {"narr": (3, 2), "args": N, "offi": N}),
    ("d_deflect_dup", "含糊话术复用", "处", "eq0", {"narr": (0, 0), "args": N, "offi": N}),
    ("d_polite", "客套表演词", "处", "max", {"narr": (4, 3), "args": N, "offi": N}),
    ("d_longans", "≥50字长答轮", "轮", "max", {"narr": (5, 3), "args": N, "offi": N}),
    ("d_pack", "对话打包句", "句", "max", {"narr": (3, 2), "args": N, "offi": N}),
    ("d_qarun", "严丝合缝问答连", "连", "max", {"narr": (3, 3), "args": N, "offi": N}),
    ("d_quotedup", "台词逐字复读", "处", "eq0", {"narr": (0, 0), "args": N, "offi": N}),
    ("d_regword", "规章词进对白占比", "", "max", {"narr": (0.08, 0.05), "args": N, "offi": N}),
]

# 对话相关键（无对白时跳过）
_DLG_KEYS = {c[0] for c in CHECKS if c[0].startswith("d_")}


# ---------------------------------------------------------------- 判定

def judge(kind, val, fail, warn):
    if kind == "eq0":
        return "PASS" if val <= 0 else "FAIL"
    if kind == "max":
        if val > fail:
            return "FAIL"
        return "WARN" if val > warn else "PASS"
    # min
    if val < fail:
        return "FAIL"
    return "WARN" if val < warn else "PASS"


def detect_genre(m):
    if m.get("dlg_para", 0) >= 0.10:
        return "narr"
    return "args"


def threshold(entry, genre, profile):
    key, label, unit, kind, T = entry
    if profile and key in profile:
        p = profile[key]
        return p.get("kind", kind), float(p["fail"]), float(p["warn"])
    t = T.get(genre) if isinstance(T, dict) else None
    if t is None:
        return None
    return kind, float(t[0]), float(t[1])


def lint_one(path, genre=None, profile=None, as_json=False):
    text = body(path)
    if cjk_len(text) < 300:
        print(f"[skip] {path}: 正文过短（<300 汉字）")
        return 0
    m = metrics(text)
    m["g_note"] = float(len(_NOTE.findall(read_text(path))))

    g = genre or detect_genre(m)
    if g not in GENRES:
        g = "args"

    # 密度类指标在短稿上没有统计意义（一个词就是 40/万字），<1200 字只查结构类
    short_doc = m["cjk"] < 1200

    rows, n_fail, n_warn, n_skip = [], 0, 0, 0
    for entry in CHECKS:
        key, label, unit, kind, _T = entry
        th = threshold(entry, g, profile)
        if th is None:
            n_skip += 1
            continue
        if key in _DLG_KEYS and m.get("dlg_para", 0) < 0.10:
            n_skip += 1
            continue
        if short_doc and (unit in ("/万字", "/千字") or key.endswith("_1k")):
            n_skip += 1
            continue
        k, fail, warn = th
        v = m.get(key)
        if v is None:
            n_skip += 1
            continue
        st = judge(k, v, fail, warn)
        if st == "FAIL":
            n_fail += 1
        elif st == "WARN":
            n_warn += 1
        show = ("%.2f" % v) if isinstance(v, float) else str(v)
        if key in ("one_sent", "short15", "dlg_para", "para_cv", "d_regword"):
            show = "%.2f" % v
        rows.append((st, label, show, unit))

    # 主谓宾（引导项）
    spo_line = None
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import spo_check
        ratio, ok, total, _ = spo_check.check(path)
        spo_line = (spo_check.verdict(ratio), "%.1f%%" % (ratio * 100), ok, total)
    except Exception:
        pass

    if as_json:
        print(json.dumps({
            "file": str(path), "genre": g, "cjk": m["cjk"],
            "fail": n_fail, "warn": n_warn, "skip": n_skip,
            "spo": (spo_line[1] if spo_line else None),
            "rows": [{"state": r[0], "label": r[1], "value": r[2], "unit": r[3]} for r in rows],
        }, ensure_ascii=False, indent=2))
        return n_fail

    print("\n=== %s | %d 字 | 文体=%s ===" % (Path(path).name, m["cjk"], g))
    w1, w2, w3 = 6, 26, 12
    for st, label, show, unit in rows:
        print("  %s %s %s %s" % (pad(st, w1), pad(label, w2), pad(show, 8), pad(unit, 6)))
    if spo_line:
        mark = "·" + spo_line[0] if spo_line[3] >= 20 else "·参考"
        print("  %s %s %s" % (pad(mark, w1), pad("主谓宾完整句(引导)", w2),
                              pad(spo_line[1], 8)))
    print("  ---- FAIL %d | WARN %d | 跳过 %d（该文体不查／无对白／短稿不查密度）"
          % (n_fail, n_warn, n_skip))
    if short_doc:
        print("  提示：正文 %d 字，密度类指标（每万/千字）已跳过；"
              "短稿请重结构与人读，别按密度数改。" % m["cjk"])
    if n_fail:
        bad = [r[1] for r in rows if r[0] == "FAIL"]
        print("  必改：%s" % "、".join(bad))
    return n_fail


# ---------------------------------------------------------------- 校准

def _pct(vals, q):
    v = sorted(vals)
    if not v:
        return 0.0
    k = (len(v) - 1) * q
    lo = int(k)
    hi = min(lo + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (k - lo)


def calibrate(folder, genre, save=None):
    files = [p for p in sorted(Path(folder).iterdir())
             if p.suffix.lower() in (".md", ".txt") and p.is_file()]
    if not files:
        print("目录里没有 .md/.txt 文件：%s" % folder)
        return 2
    rows = []
    for f in files:
        t = body(f)
        if cjk_len(t) < 300:
            continue
        d = metrics(t)
        d["g_note"] = float(len(_NOTE.findall(read_text(f))))
        rows.append(d)
    if len(rows) < 3:
        print("有效样本不足 3 篇（当前 %d），分位数没有意义。请补样本。" % len(rows))
        return 2
    total = sum(r["cjk"] for r in rows)
    print("样本 %d 篇，共 %d 字，文体按 %s 校准" % (len(rows), total, genre))
    if total < 5000:
        print("警告：样本总量不足 5000 字，分位数不稳定，建议补样本。")
    print("\n%-26s %8s %8s %8s %8s" % ("指标", "P25", "中位", "P75", "IQR比"))
    profile = {}
    for entry in CHECKS:
        key, label, unit, kind, _T = entry
        vals = [r[key] for r in rows if isinstance(r.get(key), (int, float))]
        if len(vals) < 3:
            continue
        p25, med, p75 = _pct(vals, 0.25), _pct(vals, 0.5), _pct(vals, 0.75)
        iqr = p75 - p25
        ratio = (p75 / p25) if p25 > 0 else float("inf")
        print("%-26s %8.2f %8.2f %8.2f %8s" % (label, p25, med, p75,
                                              ("%.1f" % ratio) if ratio != float("inf") else "—"))
        if kind == "eq0":
            profile[key] = {"kind": "eq0", "fail": 0, "warn": 0}
            continue
        if p25 == 0 and p75 == 0:
            profile[key] = {"kind": "eq0", "fail": 0, "warn": 0}
            continue
        if kind == "max":
            profile[key] = {"kind": "max", "fail": round(p75 + 0.5 * iqr, 2), "warn": round(p75, 2)}
        else:
            profile[key] = {"kind": "min", "fail": round(max(0.0, p25 - 0.5 * iqr), 2),
                            "warn": round(p25, 2)}
    print("\n瞄准带=[P25,P75]，验收带=[P25-0.5IQR, P75+0.5IQR]。"
          "若某指标 P75/P25 > 3，说明它是风格变量，建议从 profile 里删掉。")
    if save:
        Path(save).write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
        print("已保存：%s" % save)
    return 0


# ---------------------------------------------------------------- 入口

def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0

    genre = None
    profile = None
    save = None
    as_json = "--json" in args
    files, folder, calib_dir = [], None, None

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--genre" and i + 1 < len(args):
            genre = args[i + 1].lower()
            if genre not in GENRES:
                print("未知文体：%s（可选 narr/args/offi）" % genre)
                return 2
            i += 2
        elif a == "--profile" and i + 1 < len(args):
            profile = json.loads(Path(args[i + 1]).read_text(encoding="utf-8"))
            i += 2
        elif a == "--save-profile" and i + 1 < len(args):
            save = args[i + 1]
            i += 2
        elif a == "--calibrate" and i + 1 < len(args):
            calib_dir = args[i + 1]
            i += 2
        elif a == "--dir" and i + 1 < len(args):
            folder = args[i + 1]
            i += 2
        elif a == "--json":
            i += 1
        elif a.startswith("--"):
            print("未知参数：%s" % a)
            return 2
        else:
            files.append(a)
            i += 1

    if calib_dir:
        return calibrate(calib_dir, genre or "args", save)

    if folder:
        files = [str(p) for p in sorted(Path(folder).glob("*.md"))] + \
                [str(p) for p in sorted(Path(folder).glob("*.txt"))]
    if not files:
        print(__doc__)
        return 2

    total_fail = 0
    for f in files:
        if not Path(f).exists():
            print("[skip] 文件不存在：%s" % f)
            continue
        total_fail += lint_one(f, genre, profile, as_json)
    if not as_json:
        print("\nFAIL 项合计：%d" % total_fail)
    return 1 if total_fail else 0


if __name__ == "__main__":
    sys.exit(main())
