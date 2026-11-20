# テーマ設定（config/topic.json）の項目

| 項目 | 使われる場所 | 内容 |
|---|---|---|
| `library_name` | 台帳ページの見出し・タブ名、ZIP とコーパスの名前 | ライブラリの正式名 |
| `short_name` | 解説ページの「← ライブラリへ」リンク、Digest の題名 | 短い名前 |
| `field_ja` | 解説ページ内チャットの役割設定（「あなたは〈field_ja〉の論文読解を支援する研究者です」） | 分野名 |
| `description_ja` | 台帳ページの説明文 | 1〜2文 |
| `library_url` | 解説ページのライブラリへのリンク | 公開後に書く。空のままだと `build_page.py` が止まる |
| `timezone` | 実行日の日付（`runs/<日付>`）、Digest の週 | IANA のタイムゾーン名 |
| `schedule_ja` | 台帳ページ上部の表示 | 実行スケジュールの説明 |
| `categories` | 台帳の「分類」列、解説の分類、コーパスの一覧 | `{"記号": "名前"}`。台帳の `categories` にはこの記号だけを入れる |
| `scope.include` / `scope.exclude` | 対象判定（仕様 §2） | 対象にする研究・しない研究の条件 |
| `scope.key_paper_scope` | キー論文の範囲（仕様 §4.3） | テーマと無関係な一般論文を除くための条件 |
| `scope.preprints` | 対象判定 | プレプリントの扱い |
| `search_terms` | 探索の語群（仕様 §2） | 人と Claude が読むための語の一覧 |
| `known_names` | WebSearch での補完（仕様 §2） | 代表的なモデル名・データセット名など |
| `sources.arxiv.categories` | `arxiv_list.py` | 一覧を取る arXiv カテゴリ |
| `sources.arxiv.title_regex` | `arxiv_list.py` | 題名に一致すると `topic_match` が付く正規表現（大文字小文字を区別しない） |
| `sources.medrxiv.server` | `medrxiv_fetch.py` | `medrxiv` か `biorxiv` |
| `sources.medrxiv.topic_regex` / `method_regex` | `medrxiv_fetch.py` | 題名と抄録に対する正規表現。両方に一致すると `priority` |
| `sources.pubmed.term` | `pubmed_fetch.py` | PubMed の検索式 |
| `sources.openreview.terms` | `openreview_fetch.py` | OpenReview で1語ずつ検索する語群 |
| `chat_example_question` | 解説ページのチャットの例題（テンプレートの既定値） | 汎用の質問例 |

- 正規表現は Python の `re` の書式です。JSON の中なので `\b` は `\\b` と書きます。
- 取得スクリプトは `--config <path>` か環境変数 `TOPIC_CONFIG` で別の設定ファイルを読めます。
- 台帳ページ（`index.html`）は、公開ファイルの `config/topic.json` を読んで名前・説明・分類を表示します。読めないときは汎用の既定値で表示します。
