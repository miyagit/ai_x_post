from __future__ import annotations

import os
import random
from pathlib import Path

from anthropic import Anthropic

from ai_x_post.rss import Entry


MODEL = "claude-sonnet-4-6"

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"
PERSONA_PATH = PROMPTS_DIR / "pikka_chan.md"


TEMPLATES: dict[str, float] = {
    "気づき共有型": 0.30,
    "わかりやすく整理型": 0.25,
    "初心者のつまずき代弁型": 0.20,
    "比較してあげる型": 0.10,
    "ニュースひとこと整理型": 0.10,
    "ひとこと共感＋学び型": 0.05,
}


THEME_WEIGHTS: dict[str, float] = {"AI": 0.6, "IT": 0.3, "news": 0.1}

SOURCE_THEME: dict[str, str] = {
    "ITmedia AI+": "AI",
    "Zenn AIタグ": "AI",
    "Publickey": "IT",
    "はてブTech": "IT",
    "TechCrunch Japan": "news",
}


def _load_persona() -> str:
    return PERSONA_PATH.read_text(encoding="utf-8")


def pick_template() -> str:
    names = list(TEMPLATES.keys())
    weights = list(TEMPLATES.values())
    return random.choices(names, weights=weights, k=1)[0]


def pick_entry(entries: list[Entry]) -> Entry:
    themes = list(THEME_WEIGHTS.keys())
    weights = list(THEME_WEIGHTS.values())
    chosen_theme = random.choices(themes, weights=weights, k=1)[0]

    candidates = [e for e in entries if SOURCE_THEME.get(e.source) == chosen_theme]
    if not candidates:
        candidates = entries
    return random.choice(candidates)


def generate(entries: list[Entry]) -> tuple[str, Entry, str]:
    entry = pick_entry(entries)
    template = pick_template()
    persona = _load_persona()

    user_prompt = f"""以下の記事を元に、「{template}」のテンプレートで投稿を1件作ってください。

# 記事情報
- タイトル: {entry.title}
- ソース: {entry.source}
- リンク: {entry.link}
- 概要: {entry.summary[:500]}

# 制約
- 日本語で書く
- 140文字以内（改行含む）を目安にする
- URLは本文に含めない（別途付与される）
- ハッシュタグは基本使わない
- 投稿本文のみ出力する（前置き・解説・引用符・コードブロックは不要）
"""

    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=persona,
        messages=[{"role": "user", "content": user_prompt}],
    )
    text = response.content[0].text.strip()
    return text, entry, template
