# ai_x_post

Xで発信するAIキャラクター「ぴっかちゃん」の中身です。

AI / IT / 技術ニュース系のRSSを読み、ぴっかちゃんの人格で1投稿を作り、自己チェックに通ったらXに投稿します。実行はGitHub Actionsのcronです。

## アーキテクチャ（MVP / 案1）

```
RSS取得 → トピック・テンプレ選択 → Claude生成 → 自己チェック → X投稿
```

- **RSS取得**: `feedparser` で5媒体から最新記事を集約
  - ITmedia AI+
  - Publickey
  - Zenn AIタグ
  - はてブTech ホットエントリ
  - TechCrunch Japan
- **テンプレ選択**: ぴっかちゃんの6種の投稿テンプレから重み付き抽選
- **テーマ選択**: AI 60% / IT 30% / ニュース 10% で発信テーマを選び、対応するソースから記事を選ぶ
- **生成**: `anthropic` SDKで Claude Sonnet 4.6 に投稿本文を生成させる
- **自己チェック**: NGリスト（ひよこ語・煽り・中身のない共感など）をClaudeで判定、NGなら最大3回まで再生成
- **投稿**: `tweepy` でX APIに投稿（OAuth 1.0a User Context）

将来的には「案3（git-as-brain）」に拡張予定：過去の投稿・興味トピックをリポジトリに蓄積し、ぴっかちゃんが "育つ" 構造にする。

## 人格

`prompts/pikka_chan.md` がぴっかちゃんの人格仕様（Claudeへのシステムプロンプト）です。

- 一人称「うち」
- ソフトな関西弁
- AIやITを初心者にやさしく伝える
- バズより長期の信頼

## セットアップ

### 必要なsecrets（GitHub Actions）

- `ANTHROPIC_API_KEY`
- `X_API_KEY`
- `X_API_SECRET`
- `X_ACCESS_TOKEN`
- `X_ACCESS_TOKEN_SECRET`

### ローカル実行

```bash
uv sync
export ANTHROPIC_API_KEY=...
export X_API_KEY=...
export X_API_SECRET=...
export X_ACCESS_TOKEN=...
export X_ACCESS_TOKEN_SECRET=...
AI_X_POST_DRY_RUN=1 uv run ai-x-post   # 投稿せずに動作確認
uv run ai-x-post                         # 実投稿
```

## スケジュール

GitHub Actions cron で 1日3回（JST 8:00 / 12:30 / 19:00）。手動実行も可能（`workflow_dispatch`、dry run オプション付き）。
