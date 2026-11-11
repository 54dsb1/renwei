---
name: renwei
display_name: 人味 · 中文写作去 AI 味
display_name_en: Renwei — Humanize Chinese Writing
description: 把 AI 写的中文改写成读起来像人写的，适用于除诗歌与法定文书格式外的各类中文书面表达——评论、公众号、随笔、说明文、报告、方案、演讲稿、邮件、产品文案、人物特写、纪实。给出可执行的结构、词法、节奏、语用、内容五层规则，配一个文体自适应的机械自检脚本（叙事/论说/公文三档，支持用同体裁人类样本自校准阈值）。当用户说“去 AI 味”“太像 AI 写的”“读起来没有人味”“帮我润色得像人写的”“这段话太模板了”，或需要批量审校 AI 生成的中文文本时使用。
description_zh: 覆盖评论、报告、随笔、文案、演讲等各类中文书面表达，按叙事/论说/公文三档定档，用可校准的机械自检加人味配给，把 AI 稿改成读起来像人写的。
description_en: Rewrites AI-generated Chinese prose so it reads human — essays, reports, commentary, proposals, speeches, emails, copy and features. Picks one of three register presets (narrative / argumentative / official), runs a calibratable mechanical lint, then applies habit-level human touches.
examples_zh:
- "把我这篇公众号文章去一下 AI 味，读起来太模板了"
- "这份季度总结太像机器写的，帮我改成人话"
- "用我的十篇旧稿做基线，校准之后再改这篇稿子"
examples_en:
- "Make this WeChat article sound less like AI — it reads like a template."
- "This quarterly report sounds machine-written. Rewrite it like a person would."
- "Calibrate against ten of my old pieces, then rewrite this draft."
version: 1.0.0
author: burningtoken-skillforge
agent_created: true
tags: [中文, 写作, 改写, 去AI味, 风格校准, 文体自适应]
---

# 人味 · 中文通用写作去 AI 味（v1.0）

## 一句话

AI 的每个字都在工作，人的字有三分之一在社交、走神、重复、显摆、犯错。**改写不是把句子改漂亮，是把"效率"降下来。**

## 何时用

- 稿子被说"太工整""像机器写的""一股 AI 味"；
- AI 初稿要发出去（公众号、报告、方案、演讲、邮件、文案）；
- 需要一批文本过一致性审校。

不适用：诗歌、歌词、法定文书格式本身（红头通知、合同条款这类"格式即内容"的部分）。公文体只对"行文腔调"做粗筛，不对格式提要求。

## 起点是定档，不是改字

同一条规则在三种文体里方向相反。**先判断这是哪一档，再决定拿什么尺子量**：

| 档 | 文体 | 主要特征 | 尺子重点 |
|---|---|---|---|
| `narr` 叙事 | 故事、随笔、特写、纪实、公众号叙事文 | 有人、有事、有时间线 | 句长变异、段落呼吸、细节密度、人味配给 |
| `args` 论说 | 评论、分析、说明文、报告、方案、演讲稿 | 有观点、有论证、有信息层级 | 论证词密度、抽象名词、对仗与排比、结构对称 |
| `offi` 公文 | 通知、总结、请示、会议纪要 | 有格式、有称谓、有条款 | 只查腔调（模板句、四字格堆叠），不查节奏 |

拿不准就默认 `args`；只要文中有 3 处以上成段对白，用 `narr`。

## 执行流水线（按顺序，不跳步）

| 步骤 | 做什么 |
|---|---|
| 0 定档 | 判断 `narr`/`args`/`offi`。**手边有同体裁人类样本（2-3 篇）就先跑 `python scripts/lint.py --calibrate 语料目录` 生成该文体的真实档位**——这是本 skill 最重要的一步，比任何默认阈值都可靠 |
| 1 写前手感 | 从同体裁人类文章里各抽 2000-3000 字，抄最长句与最短句、数每段几句、看它怎么开头怎么收尾、有没有跑题。产 5-8 行手感备忘贴在稿头；先看人写的，再动笔 |
| 2 机检画像 | `python scripts/lint.py 稿件.md --genre args`（或 narr/offi），列出 FAIL 项 |
| 3 改写 | 顺序：①FAIL 清零（按 CORE §1 分组速查）②语用与人味（CORE §2.6，每 3000 字挑 4-6 条做实）③结构位单独过（CORE §2.1-2.3：开头/结尾/段落呼吸）④内容层（细节、数字、对话，CORE §2.4-2.5） |
| 4 复测 | FAIL=0；`python scripts/spo_check.py 稿件.md` 落 70-90% 带（60-70 与 >90 需人工复核）；七问自检（CORE §3）全过 |
| 5 人读 | 从后往前读一遍，读不出"作者在展示手艺"才算过 |

**关键经验：机械指标是下限（不做会露馅），语用手感是上限（做了才像人）。拿上限去换下限，越改越差。**

## 文件索引

| 文件 | 内容 |
|---|---|
| `CORE.md` | **必读，唯一执行表**：§0 纪律 / §1 机械层速查（按组给处置口径）/ §2 写作层（开头·结尾·段落·细节·数字·对话·人味配给）/ §3 七问自检 / §4 验收 |
| `references/01-基线与定档.md` | 阈值从哪来、三档默认值表、怎么用样本校准、哪些数不能追 |
| `references/02-AI味指纹图谱.md` | 六个层面告诉你"为什么读起来像 AI"，用于诊断而不是套规则 |
| `references/03-叙述七病.md` | 句子和词都改干净之后剩下的七种病，每条带对照例 |
| `references/04-指标反噬实录.md` | 指标调到全绿反而判得更差的实测记录与方法论 |
| `references/05-改写对照.md` | 三段逐层改写示范（`args`/`narr`/`offi` 各一），每段附处置理由表 |
| `scripts/lint.py` | 机械自检，62 项；三档内置 + 样本校准；全部数值阈值的唯一事实源 |
| `scripts/spo_check.py` | 主谓宾完整句占比（防"电报体/断片"） |

## 最容易犯的五个错（实测踩过）

1. **假精炼**：`这个地方`改`这里`，`因为`改`故`。越干净越像机器，中文的冗余是体温。
2. **指标当 KPI**：指标全调绿，读起来反而更假。指标只排雷，不做目标函数。
3. **细节变挂件**：细节一段一个摆过去，文章就停了。细节要由动作、因果、场景带出来。
4. **结尾升华**：`愿每一个努力的人都被看见`、`未来可期`、`让我们一起……`。AI 最舍不得放下的就是最后那口气。
5. **结构对称**：三段式、每段三句、每节三点、首尾呼应。人对齐不了这么整齐。

## 验收标准（详见 CORE §4）

`lint.py` FAIL=0 ｜ spo 70-90% ｜ 七问全过 ｜ 人读一票否决 ｜ 全文不存在"删掉也不损失信息"的句子超过三成
