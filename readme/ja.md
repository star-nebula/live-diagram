# live-diagram · 生きているアーキテクチャ図

[English](../README.md) | [简体中文](zh-CN.md) | **日本語** | [한국어](ko.md) | [Español](es.md) | [Português](pt-BR.md) | [Русский](ru.md)

> **JSON 設定ファイル 1 つ**から、レイアウト固定の「常に稼働している」アーキテクチャ図を生成：配線を流れるパケット、スクロールするログ、カウンタ、状態遷移するゲージ、順番に光るアラート。**H.264 mp4**（X / 小紅書 / TikTok / Bilibili）や**ブラウザでそのまま開けるライブ Web ページ**として出力できます。[AI エージェントスキル](../SKILL.md)としても動作します。

![preview](../docs/media/memory-vault-panel.webp)

*ループ再生：このスキルで描画した AI Memory Vault のライブパネル（GitHub ダークテーマ、数値はイメージ）。*

## コンセプト

[ythx-101/live-panel-skill](https://github.com/ythx-101/live-panel-skill) の**手法**を参考に、コードはすべて独自実装：

- **レイアウトは動かない。動くのはシステムの状態** —— どの 1 フレーム切り出しても完成した図になる。
- **決定論的レンダリング** —— `window.seek(t)` に公開され、すべての変化は `t` の純関数（時計・乱数・CSS アニメーション不使用）。フレームは再現・検証可能。
- **どこも同じ真実** —— ログは状態機が自動生成。数値は画面のどこでも一致。
- **実データがない場合は「示意」と明記**。

## テーマ（`theme.preset`）

`github-dark` / `github-light`（GitHub 公式カラーパレット）・`blueprint`（青図面風）・`terminal-dark`（ターミナル風）・`light-pastel`（パステル風）。キャンバス：`4:5` / `3:4` / `1:1` / `9:16` / `16:9`。

## 使い方

必要環境：Python 3.8+（標準ライブラリのみ）、Chrome/Chromium/Edge、ffmpeg。

```bash
python scripts/livediagram.py render --config my.json --out my.mp4 --html-out my.html --crf 10 --preset slow
python scripts/livediagram.py check  --config my.json --out-dir frames --repeat
python scripts/livediagram.py build  --config my.json --out page.html
```

AI スキルとして：このフォルダをエージェントの skills ディレクトリ（`~/.zcode/skills/` など）に置くだけ。

## ドキュメント

[SKILL.md](../SKILL.md)（ワークフロー）・[motion-grammar.md](../references/motion-grammar.md)（動作文法）・[config-schema.md](../references/config-schema.md)（設定リファレンス）・[サンプル](../examples/rag-pipeline/)。詳細は英語版 [README](../README.md) と中国語版 [zh-CN](zh-CN.md)。

## ライセンス

[MIT](../LICENSE) ・ 動作文法の元ネタ：[@thedelost](https://x.com/thedelost) のクリップ（独自実装、コード未流用）。
