# ai_x_post

Xで発信するAIキャラクター「ぴっかちゃん」の中身です。

AI / IT / 技術ニュース系のRSSを読み、ぴっかちゃんの人格で1投稿を作り、自己チェックに通ったらXに投稿します。実行は **Claude Routines**（Anthropicクラウド側のスケジューラ）です。

## アーキテクチャ

```
Claude Routine (cron)
   ↓ サンドボックスでBash実行
   ├─ curlでRSS取得
   ├─ $RANDOM でテーマ・テンプレ抽選
   ├─ Claude自身が投稿生成・自己チェック
   └─ MCP経由で post_tweet 呼び出し
        ↓
   Cloudflare Workers (mcp-server/)
        ↓ OAuth 1.0a署名
   X API → 投稿
```

- **Routine**: `prompts/routine_instruction.md` を実行プロンプトとして登録。1日5回（JST 8:00 / 12:00 / 15:00 / 18:00 / 21:00）発火
- **MCPサーバー**: Cloudflare Workers上に自前実装（`mcp-server/`）。`post_tweet` ツール1個を提供
- **生成・チェック**: Routine実行Claude自身が同セッション内で実施（Anthropic API課金は発生しない）

## 構成ファイル

```
prompts/
  routine_instruction.md  # Routineに登録する実行プロンプト本体
  pikka_chan.md           # 人格仕様の元ドキュメント（参照用）
mcp-server/               # Cloudflare Workers MCPサーバー
  src/index.ts            # post_tweet 実装（OAuth 1.0a署名込み）
  wrangler.toml
```

## 人格

`prompts/pikka_chan.md` がぴっかちゃんの人格仕様の元ドキュメント。`routine_instruction.md` にはこのエッセンスが組み込まれています。

- 一人称「うち」
- ソフトな関西弁
- AIやITを初心者にやさしく伝える
- バズより長期の信頼

## セットアップ

### Workers側

```bash
cd mcp-server
npm install
# secrets登録（初回のみ）
npx wrangler secret put MCP_AUTH_TOKEN
npx wrangler secret put X_API_KEY
npx wrangler secret put X_API_SECRET
npx wrangler secret put X_ACCESS_TOKEN
npx wrangler secret put X_ACCESS_TOKEN_SECRET
# デプロイ
npx wrangler deploy
```

### Connector登録（claude.ai側）

`https://claude.ai/code/customize` から MCP Connector を登録：

- Name: `x-mcp`
- URL: `https://x-mcp-server.<account>.workers.dev/<MCP_AUTH_TOKEN>`
  - URL末尾にトークンを埋め込む方式（Workers側で path / Authorization どちらでも認証OK）

### Routine作成

`https://claude.ai/code/routines` から：

- Prompt: `prompts/routine_instruction.md` の中身を貼る
- Schedule: `0 23,3,6,9,12 * * *`（UTC）= JST 8:00/12:00/15:00/18:00/21:00
- Connector: `x-mcp` を選択

## 運用メモ

- マニュアル実行直後のブラウザリロードはRoutineが消える疑惑あり、避けること
- Connector接続検証で「Couldn't reach the MCP server」が出ても動いてる場合あり（リロードで解消）
- Routine削除はWeb UIからのみ（API不可）
