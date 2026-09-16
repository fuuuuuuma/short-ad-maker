#!/usr/bin/env python3
"""Create a non-destructive workspace for one vertical short-ad production."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


GOALS = {"awareness", "consideration", "purchase", "booking", "signup"}
PLATFORMS = {"reels", "tiktok", "youtube-shorts", "multi"}
CASTING = {"female", "male", "faceless", "auto"}


def slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9ぁ-んァ-ヶ一-龠]+", "-", value.strip().lower())
    return value.strip("-")[:48] or "short-ad"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--product", required=True)
    parser.add_argument("--goal", default="purchase", choices=sorted(GOALS))
    parser.add_argument("--audience", default="商品に関心のある視聴者")
    parser.add_argument("--duration", type=int, default=20)
    parser.add_argument("--platform", default="multi", choices=sorted(PLATFORMS))
    parser.add_argument("--casting", default="auto", choices=sorted(CASTING))
    parser.add_argument("--voice", default="auto")
    parser.add_argument("--product-source", default="")
    parser.add_argument("--cta", default="詳細を見る")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def default_output(slug: str) -> Path:
    shared = Path("/Users/Shared/short-ad-maker")
    if shared.parent.exists():
        return shared / slug
    return Path.cwd().resolve() / "outputs" / "short-ad-maker" / slug


def main() -> int:
    args = parse_args()
    if not 6 <= args.duration <= 60:
        raise SystemExit("--duration must be between 6 and 60 seconds")

    slug = slugify(args.product)
    root = (args.output or default_output(slug)).expanduser().resolve()
    if root.exists() and any(root.iterdir()):
        raise SystemExit(f"Refusing to overwrite non-empty directory: {root}")

    for relative in (
        "assets/source",
        "assets/generated",
        "planning",
        "work/audio",
        "work/video",
        "work/captions",
        "exports",
        "reports",
    ):
        (root / relative).mkdir(parents=True, exist_ok=True)

    project = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "product": args.product,
        "product_source": args.product_source,
        "goal": args.goal,
        "audience": args.audience,
        "duration_seconds": args.duration,
        "platform": args.platform,
        "casting": args.casting,
        "voice": args.voice,
        "call_to_action": args.cta,
        "confirmed_claims": [],
        "output_path": str(root / "exports" / "short-ad-final.mp4"),
    }
    (root / "project.json").write_text(
        json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (root / "planning" / "creative-plan.md").write_text(
        "# Creative plan\n\n"
        "## One promise\n\n"
        "## 0–3s hook\n\n"
        "## Demonstration\n\n"
        "## Visible proof\n\n"
        "## CTA\n\n"
        "## Confirmed facts and sources\n",
        encoding="utf-8",
    )
    (root / "planning" / "narration.txt").write_text("", encoding="utf-8")
    (root / "work" / "captions" / "final.srt").write_text("", encoding="utf-8")
    receipt = {
        "final_mp4": project["output_path"],
        "caption_coverage": 0.0,
        "caption_timing_source": "pending",
        "narration_continuous": False,
        "voice_speed": 1.0,
        "hook_end_seconds": 3.0,
        "median_shot_seconds": 0.0,
        "rights_checked": False,
        "facts_checked": False,
        "visual_reviewed": False,
        "audio_components": {
            "narration": "work/audio/voice.wav",
            "bgm": "work/audio/bgm.wav",
            "sfx": "work/audio/sfx.wav"
        },
    }
    (root / "reports" / "delivery-receipt.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
