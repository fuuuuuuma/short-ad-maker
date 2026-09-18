#!/usr/bin/env bash
set -e

REPO_URL="https://github.com/fuuuuuuma/short-ad-maker.git"
TEMP_DIR="$(mktemp -d)"

echo "==> Downloading short-ad-maker plugin from GitHub..."
git clone --depth 1 "$REPO_URL" "$TEMP_DIR"

echo "==> Installing plugin into Antigravity..."
if command -v agy >/dev/null 2>&1; then
  agy plugin install "$TEMP_DIR/plugins/short-ad-maker"
else
  mkdir -p "$HOME/.gemini/config/plugins"
  rm -rf "$HOME/.gemini/config/plugins/short-ad-maker"
  cp -R "$TEMP_DIR/plugins/short-ad-maker" "$HOME/.gemini/config/plugins/"
  echo "  [ok] Copied plugin to ~/.gemini/config/plugins/short-ad-maker"
fi

# Antigravity の標準スキル探索パス (~/.agents/skills/) にもシンボリックリンクを展開
mkdir -p "$HOME/.agents/skills"
for skill in cut short-ad-maker srt-fast; do
  ln -sfn "$HOME/.gemini/config/plugins/short-ad-maker/skills/$skill" "$HOME/.agents/skills/$skill"
done

rm -rf "$TEMP_DIR"
echo "==> Successfully installed short-ad-maker plugin into Antigravity!"
echo "    Available skills: /short-ad-maker, /cut, /srt-fast"
