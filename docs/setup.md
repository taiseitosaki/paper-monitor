# セットアップ手順

Claude Code のクラウドセッションで、このリポジトリを開いて行います。手順はどれも Claude に頼めます（「docs/setup.md に従ってセットアップして」）。

## 1. テーマを決める（Claude と相談しながら）

[`config/topic.json`](../config/topic.json) は空のひな形です。最初のセットアップでは、Claude が利用者に質問しながら一緒に埋めます。項目の意味は [configuration.md](configuration.md) にあります。

### Claude が進める手順

1. **テーマを聞く**: 監視したい研究テーマ、とくに追いたい論文・モデル・データセットの例（あれば3〜5本）、対象外にしたいもの、主に読む情報源（arXiv だけでよいか、medRxiv・bioRxiv・PubMed・OpenReview も要るか）、実行時刻とタイムゾーンを、まとめて短く聞く。わからない項目は Claude が案を出す。
2. **案を作る**: 答えをもとに、`library_name`・`field_ja`・`description_ja`・`categories`（3〜5個の分類と名前）・`scope`（対象・対象外・キー論文の範囲）・`search_terms`・`known_names` の案を書き、利用者に見せて直す。
3. **検索条件を作って試す**: `sources` の各項目（arXiv のカテゴリと題名の正規表現、medRxiv / bioRxiv の正規表現、PubMed の検索式、OpenReview の語群）を書き、取得スクリプトを直近1週間ほどで実行する。

   ```bash
   python3 -I scripts/arxiv_list.py /tmp/arxiv.json
   ```

   ```bash
   python3 -I scripts/medrxiv_fetch.py 2026-11-01 2026-11-07 /tmp/medrxiv.json
   ```

   ```bash
   python3 -I scripts/pubmed_fetch.py 7 /tmp/pubmed.json
   ```

   ```bash
   python3 -I scripts/openreview_fetch.py 2026-11-01 /tmp/openreview.json
   ```

4. **結果を見せて調整する**: 情報源ごとの件数と、印が付いた候補（`topic_match`・`priority`）の題名を見せる。利用者が挙げた例の論文や、明らかに関係する論文が漏れていないか、無関係なものが多すぎないかを一緒に確かめ、正規表現・検索式・語群を直して再実行する。利用者が納得するまで繰り返す。
5. **確定する**: 使わない情報源は `sources` から外し、[`prompts/daily.md`](../prompts/daily.md) の手順3からもそのスクリプトを外す。`library_url` は 2. の公開後に書くので空のままにする。

## 2. 研究ライブラリを公開する

`index.html` を Artifact として公開します。公開ファイルとして、リポジトリと同じパスで次を一緒に載せます。

- `config/topic.json`
- `spec/operating-spec.md`
- `templates/paper-template.html`
- `scripts/*`

capabilities は次のとおりです（db は閲覧者が読み、編集者だけが書ける。mcp は台帳のボタンが定期タスクを起動するため）。

```json
{
  "db": { "rules": [{ "path": "", "read": "view", "write": "admin" }] },
  "mcp": { "servers": [{ "server": "Claude Code Remote", "tools": ["fire_trigger"] }] }
}
```

公開できたら、その URL を `config/topic.json` の `library_url` に書き、同じ URL に再公開します（`build_page.py` は `library_url` が空だと止まります）。

## 3. 定期タスクを作る

[`prompts/`](../prompts/) の5つのプロンプトの `<LIBRARY_NAME>` と `<LIBRARY_URL>` を置き換えて、定期タスクを作ります。

| ファイル | スケジュール | モデル |
|---|---|---|
| `daily.md` | 毎日 | Sonnet |
| `weekly-digest.md` | 毎週日曜 | Sonnet |
| `ondemand.md` | なし（ボタンで起動） | Sonnet |
| `export-zip.md` | なし（ボタンで起動） | Opus |
| `discuss.md` | なし（ボタンで起動） | Opus |

どれも「起動ごとに新しいセッション」にします。ボタンで起動する3つは、作成後にタスクの ID（`trig_…`）をライブラリの db に書きます。

| db ドキュメント | 内容 |
|---|---|
| `config/ondemand` | `{"trigger_id": "<即時作成のタスク ID>"}` |
| `config/export` | `{"trigger_id": "<ZIP 保存のタスク ID>"}` |
| `config/discuss` | `{"trigger_id": "<議論のタスク ID>"}` |

これが無いと、台帳ページのボタンは「次の定期実行で作成します」と表示して、依頼の記録だけを残します。

## 4. 動作を確かめる

- 日次実行のタスクを手動で一度起動し、`runs/<日付>` に結果が記録され、台帳に論文が並ぶことを確かめます。
- 実行環境のネットワークが絞られている場合は、仕様 §1 のホストへの通信を許可します。

## テーマを変えるとき

`config/topic.json` を書き換えてライブラリに再公開するだけです。スクリプト・テンプレート・台帳ページは設定を読み直します。仕様書のテーマに依存する判断（対象判定・キー論文の範囲）も設定を参照しています。
