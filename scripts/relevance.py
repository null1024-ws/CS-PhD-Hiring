"""Classify whether a hiring note is CS-related."""

from __future__ import annotations

import re

CS_RE = re.compile(
    r"""
    \bnlp\b|自然语言|大语言模型|\bllm\b|计算机视觉|\bcv\b|
    \bmlsys\b|机器学习|深度学习|machine\s+learning|计算机系统|系统方向|
    系统安全|网络安全|\bsecurity\b|可信|
    \bhci\b|人机交互|机器人|\brobotics\b|
    数据挖掘|编程语言|编译器|计算机体系结构|操作系统|
    软件工程|程序分析|\bagent\b|强化学习|
    理论计算机|算法
    """,
    re.I | re.X,
)

NOTCS_RE = re.compile(
    r"""
    细胞培养|湿实验|有机合成|蛋白质纯化|动物实验|
    土木工程|结构力学|公司金融|资本市场|
    临床手术|外科|护理学
    """,
    re.I | re.X,
)

AMBIGUOUS_RE = re.compile(r"人工智能|\bai\b|智能", re.I)


def classify_relevance(text: str) -> str:
    """Return cs / review / notcs. Ambiguous text must not be cs."""
    has_cs = bool(CS_RE.search(text or ""))
    has_notcs = bool(NOTCS_RE.search(text or ""))
    has_ambiguous = bool(AMBIGUOUS_RE.search(text or ""))
    if has_cs and has_notcs:
        return "review"
    if has_notcs and has_ambiguous:
        return "review"
    if has_cs:
        return "cs"
    if has_notcs:
        return "notcs"
    return "review"
