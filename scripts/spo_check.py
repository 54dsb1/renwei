# -*- coding: utf-8 -*-
"""spo_check.py · 主谓宾完整句占比检查（humanize-zh v1.0）

【为什么查这一项】
改写稿最容易犯的毛病不是"用词像 AI"，而是**断片**：一句话没有主语，
或者只有名词堆叠，读起来像电报、像字幕、像分镜表。
"一件一件，念，问，批。""听得见，插不上嘴。""搁置……"
这类句子单看有味道，连着来三十句，读者会被拖垮。

【口径】
按句切分（。！？……），逐句判断是否存在"显性主语 + 谓语"：
  主语：谓语之前出现名词/代词（n* / r*）；时间、处所、机构名可作话题主语
  谓语：出现动词（v*）或形容词谓语（a*）
长度 < 4 字的句子（"嗯。""啪。""那他呢？"）不进入分母——
人类语料里这类短应答同样高频，计入会失真。

【人类实测基线（2026-11，8 篇中文人类叙事切片，各 4000-6000 字）】
  区间 60.8%–75.1%，中位 68.0%

【判定】（带状验收，对齐上述人类带）
  70%–90%  PASS（人类中位带；短答/承前省略是已验证的人类形态，不再逼高）
  60%–70%  WARN（贴人类带下缘，人工复核是否真有断片）
  <60%     FAIL（断片/电报体护栏——本项指标的原始防御目的）
  >90%     WARN（过度完整提示：把"每个字都在工作"写成常态，本身是 AI 形态）
注意：本项**不是硬门槛**，权重与其他指标相同。人类文本有大量合法的
零指代、承前省略、话题句、对话短答。先读顺，再看数。
论说文/公文的长句多、连接词多，这一项通常自然落在 70-85%，不必特别处理。

用法：
    python spo_check.py 文件.md [文件2.md ...]
    python spo_check.py --detail 文件.md     # 列出不完整句
"""
import re
import sys

try:
    import jieba.posseg as pseg
except ImportError:  # pragma: no cover
    print("需要 jieba：pip install jieba")
    raise SystemExit(2)

SENT_END = "。！？…"
SUBJ_TAGS = ("n", "r")
VERB_TAGS = ("v",)
ADJ_TAGS = ("a",)
TOPIC_TAGS = ("t", "nt", "ns", "nz")


def load_body(path):
    t = open(path, encoding="utf-8").read()
    t = re.split(r"\n##\s*(?:备注|改写备忘|手感备忘)", t)[0]
    t = re.sub(r"^#.*$", "", t, flags=re.M)
    t = t.replace("---", "")
    return t


def split_sentences(text):
    out, buf = [], ""
    for ch in text:
        if ch == "\n":
            if buf.strip():
                out.append(buf.strip())
            buf = ""
        elif ch in SENT_END:
            buf += ch
            if buf.strip():
                out.append(buf.strip())
            buf = ""
        else:
            buf += ch
    if buf.strip():
        out.append(buf.strip())
    return [s for s in out if re.search(r"[\u4e00-\u9fff]", s)]


def _is(tag, prefixes):
    return any(tag.startswith(p) for p in prefixes)


def sentence_ok(sent):
    """返回 (True/False/None, 原因)"""
    raw = sent.strip("“”‘’ ")
    core = re.sub(r"[^\u4e00-\u9fff0-9A-Za-z]", "", raw)
    if len(core) < 4:
        return None, "too-short"

    words = [(w, f) for w, f in pseg.cut(core) if w.strip()]
    if not words:
        return None, "empty"

    verb_i = -1
    for i, (w, f) in enumerate(words):
        if _is(f, VERB_TAGS) or _is(f, ADJ_TAGS):
            verb_i = i
            break
    if verb_i < 0:
        return False, "无谓语"

    if any(_is(f, SUBJ_TAGS) for w, f in words[:verb_i]):
        return True, ""
    if verb_i > 0 and _is(words[0][1], TOPIC_TAGS):
        return True, ""
    return False, "无显性主语（断片或零指代）"


def check(path):
    body = load_body(path)
    total = ok = 0
    bad = []
    for sent in split_sentences(body):
        r, why = sentence_ok(sent)
        if r is None:
            continue
        total += 1
        if r:
            ok += 1
        else:
            bad.append((sent, why))
    ratio = ok / total if total else 0.0
    return ratio, ok, total, bad


def verdict(ratio):
    if 0.70 <= ratio <= 0.90:
        return "PASS"
    if ratio >= 0.60:
        return "WARN"
    return "FAIL"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    detail = "--detail" in sys.argv
    if not args:
        print(__doc__)
        return
    for p in args:
        ratio, ok, total, bad = check(p)
        print(f"{verdict(ratio)}\t{ratio*100:5.1f}%\t{ok}/{total}\t{p}")
        if detail:
            for s, why in bad[:40]:
                print(f"      × {s}   [{why}]")


if __name__ == "__main__":
    main()
