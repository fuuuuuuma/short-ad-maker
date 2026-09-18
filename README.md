# Short Ad Maker

商品画像・URL・短い説明から企画・素材・ナレーション・全文字幕・BGM・効果音を組み、Reels / TikTok / YouTube Shorts向けの縦型MP4まで仕上げる動画制作プラグインです。

本プラグインには、広告ショート制作に加えて、Premiere Proの無音自動ジェットカット（`/cut`）や、Apple Silicon GPU / Whisper による高速SRT字幕生成（`/srt-fast`）など、動画編集を大幅に効率化するスキル群が同封されており、**Codex** および **Antigravity** の両環境で動作します。

## インストール

```bash
codex plugin marketplace add fuuuuuuma/short-ad-maker
codex plugin add short-ad-maker@short-ad-maker
```

インストール後は、新しいセッションまたは即時にスキルが利用可能になります。

## 同封スキル一覧

| スキル | 説明 | コマンド例 |
|---|---|---|
| **`short-ad-maker`** | 商品情報から縦型広告ショート（9:16 MP4）を企画・生成・編集・完パケ | `$short-ad-maker この商品画像から広告ショートを作って` |
| **`cut`** | Premiere Pro XML の無音・雑音区間を自動ジェットカット | `/cut /path/to/timeline.xml` |
| **`srt-fast`** | 単一パスGPU転写＋並列改行による高速日本語SRT字幕生成 | `/srt-fast /path/to/audio.wav` |

### 1. 広告ショート制作 (`short-ad-maker`)
```text
$short-ad-maker
この商品画像から、20秒の縦型広告ショートを作って。
ターゲットは仕事帰りの20〜30代。自然なVlog風で、MP4まで完成させて。
```
商品名だけでも始められます。効能根拠、人物・声の許諾、課金などの要所のみ確認し、構成・生成・編集・納品前検証まで進めます。

### 2. 無音カット (`cut`)
```text
/cut /path/to/your_timeline.xml
```
Premiere Pro から書き出した Final Cut Pro XML を解析し、無音部分をカットした編集済み XML を出力します。複数人ピンマイク収録時の `--tracks A1,A2` にも対応しています。

### 3. 高速字幕生成 (`srt-fast`)
```text
/srt-fast /path/to/audio_or_video
```
Apple Silicon GPU（mlx-whisper）による超高速文字起こしと、サブエージェント/LLMによる意味区切り並列改行、全体アライメント、25字超・文頭NGのQA自動修復ループにより、高品質なテロップ用SRTを瞬時に生成します。

## 必要な環境

- Codex / Antigravity
- Python 3.9 以降
- `ffmpeg`（無音カット・メディア処理用: `brew install ffmpeg`）
- `mlx-whisper` または `faster-whisper`（高速字幕生成用: `pip3 install --user mlx-whisper faster-whisper`）

## ライセンス

MIT License。生成物に使用する画像、音声、フォント、ブランド素材の権利はそれぞれの利用条件に従ってください。
