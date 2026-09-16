# Short Ad Maker

商品画像・URL・短い説明から、企画、AI素材、ナレーション、全文字幕、BGM、効果音を組み、Reels / TikTok / YouTube Shorts向けの縦型MP4まで仕上げるCodex Skillです。

## インストール

Codexに次のように依頼します。

> `https://github.com/fuuuuuuma/short-ad-maker` のスキルをインストールして

または、Skill Installerを直接実行します。

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo fuuuuuuma/short-ad-maker \
  --path . \
  --name short-ad-maker
```

インストール後は新しいターンで使えます。

## 使い方

```text
$short-ad-maker
この商品画像から、20秒の縦型広告ショートを作って。
ターゲットは仕事帰りの20〜30代。自然なVlog風で、MP4まで完成させて。
```

商品名だけでも始められます。確認が必要なのは、効能の根拠、実在人物や声の許諾、課金、公開など結果や権利に関わる項目です。

## 必要な環境

Codexと、次の能力のいずれかを利用できる環境が必要です。

- 画像または動画を生成できるツール、あるいは手元の動画素材
- 音声を生成できるツール、あるいは手元のナレーション
- MP4を編集できるツール
- 音声認識による字幕タイミング取得

このスキルは特定の生成サービスへ固定せず、利用可能なツールから組み合わせを選びます。外部サービスの利用料や商用利用条件は各サービスに従います。

Skill Installerが導入するのは制作手順と検証ツールです。動画生成サービス、音声生成サービス、各サービスの契約やログイン状態は含みません。環境に応じた3つの動作モードは [runtime-modes.md](references/runtime-modes.md) を参照してください。

## 説明資料

[広告ショート制作ガイド](assets/guide.html) は単一HTMLです。白基調の資料としてブラウザでそのまま開けます。

## インストール確認

リポジトリ公開後、次で別フォルダへ導入テストできます。

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo fuuuuuuma/short-ad-maker \
  --path . \
  --name short-ad-maker \
  --dest /tmp/short-ad-maker-install-test
```

## ライセンス

MIT License。生成物に使用する画像、音声、フォント、ブランド素材の権利はそれぞれの利用条件に従ってください。
