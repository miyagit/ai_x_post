from __future__ import annotations

import json
import os
import re

from anthropic import Anthropic


MODEL = "claude-sonnet-4-6"

MAX_LENGTH = 140


CHECK_PROMPT = """あなたは「ぴっかちゃん」というキャラクターの投稿をチェックする編集者です。
以下の投稿案が、ぴっかちゃんの発信ルールを守れているか判定してください。

# チェック項目（どれか1つでも該当したらNG）
1. ひよこ語（〜ぴよ、〜ぴ、等）が使われている
2. コテコテすぎる関西弁（〜やで！〜やねん！〜ちゃうねん！を多用、など）
3. 上から目線の表現（「教えてあげる」「〜しなさい」など）
4. 幼すぎる口調
5. テンションが高すぎる（「！！！」連発、絵文字過多など）
6. 中身のない共感だけ（「わかる〜！」だけで情報がない）
7. 必要以上に強い断定（「絶対〜」「100%〜」を根拠なく）
8. 炎上狙いの煽り
9. 誰かを見下す表現
10. 上記に加え、一人称が「うち」になっていない（「私」「僕」などを使っている）

# 投稿案
{post}

# 出力
以下のJSON形式のみを出力してください。前置き・解説・コードブロックは不要です。
{{"ok": true/false, "reason": "NGの場合のみ理由を簡潔に"}}
"""


def _length_ok(post: str) -> tuple[bool, str]:
    if len(post) > MAX_LENGTH:
        return False, f"文字数オーバー ({len(post)}/{MAX_LENGTH})"
    if not post.strip():
        return False, "空の投稿"
    return True, ""


def _extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"JSON not found in response: {text}")
    return json.loads(match.group(0))


def check(post: str) -> tuple[bool, str]:
    ok, reason = _length_ok(post)
    if not ok:
        return False, reason

    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        messages=[{"role": "user", "content": CHECK_PROMPT.format(post=post)}],
    )
    text = response.content[0].text.strip()
    result = _extract_json(text)
    return bool(result.get("ok")), str(result.get("reason", ""))
