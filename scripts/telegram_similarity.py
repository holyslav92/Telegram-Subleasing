"""
Анти-повтор: сравнение текстов постов по opening hook, n-граммам и шаблонным фразам.
"""

import re
from difflib import SequenceMatcher

from telegram_post_history import strip_html

# Шаблонные заходы, которые нельзя повторять
BANNED_OPENING_HOOKS = [
    "ищете жильё в тюмени без суеты при заезде",
    "планируете визит в тюмень",
    "знаете даты предстоящей поездки",
]

BOILERPLATE_PHRASES = [
    "бесконтактный заезд 24/7",
    "прямые цены",
    "отзывы гостей",
    "официальном сайте",
]


def normalize_text(text: str) -> str:
    t = strip_html(text).lower()
    t = re.sub(r"\s+", " ", t).strip()
    return t


def opening_hook(text: str, max_len: int = 140) -> str:
    plain = normalize_text(text)
    for sep in (".", "!", "?"):
        idx = plain.find(sep)
        if 0 < idx < max_len:
            return plain[: idx + 1]
    return plain[:max_len]


def content_tokens(text: str) -> set[str]:
    """Токены без boilerplate — для сравнения смысла."""
    plain = normalize_text(text)
    for phrase in BOILERPLATE_PHRASES:
        plain = plain.replace(phrase, " ")
    words = re.findall(r"[а-яёa-z]{4,}", plain)
    return set(words)


def bigrams(text: str) -> set[str]:
    words = re.findall(r"[а-яёa-z]{3,}", normalize_text(text))
    return {f"{words[i]} {words[i+1]}" for i in range(len(words) - 1)}


def similarity_score(text_a: str, text_b: str) -> float:
    """0..1 — чем выше, тем похожее."""
    a, b = normalize_text(text_a), normalize_text(text_b)
    if not a or not b:
        return 0.0
    ratio = SequenceMatcher(None, a, b).ratio()
    ta, tb = content_tokens(a), content_tokens(b)
    if not ta or not tb:
        jaccard = 0.0
    else:
        jaccard = len(ta & tb) / len(ta | tb)
    bg_a, bg_b = bigrams(a), bigrams(b)
    bg = len(bg_a & bg_b) / max(len(bg_a | bg_b), 1)
    hook_match = 1.0 if opening_hook(a) == opening_hook(b) else 0.0
    return 0.35 * ratio + 0.35 * jaccard + 0.2 * bg + 0.1 * hook_match


def check_similarity_against_corpus(
    text: str,
    corpus: list[dict],
    threshold: float = 0.42,
) -> tuple[bool, list[str]]:
    """
    True = слишком похоже на что-то из corpus.
    corpus entries: {title, text_html/body, id, published_at}
    """
    reasons: list[str] = []
    hook = opening_hook(text)
    for banned in BANNED_OPENING_HOOKS:
        if banned in hook:
            reasons.append(f"шаблонный заход: «{banned}»")

    for entry in corpus:
        other = entry.get("text_html") or entry.get("body") or entry.get("title") or ""
        if not other:
            continue
        score = similarity_score(text, other)
        if score >= threshold:
            label = entry.get("id") or entry.get("title", "?")[:40]
            reasons.append(f"похоже на «{label}» (score={score:.2f})")
        other_hook = opening_hook(other)
        if hook and other_hook and hook == other_hook:
            label = entry.get("id") or "?"
            reasons.append(f"тот же opening hook, что у «{label}»")
    return (len(reasons) > 0, reasons)


def variants_too_similar(variants: list[str], max_pair: float = 0.55) -> list[str]:
    """Проверка, что 3 варианта реально различаются."""
    reasons: list[str] = []
    for i in range(len(variants)):
        for j in range(i + 1, len(variants)):
            score = similarity_score(variants[i], variants[j])
            if score >= max_pair:
                reasons.append(f"варианты {i+1} и {j+1} слишком похожи (score={score:.2f})")
    return reasons
