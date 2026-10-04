#!/usr/bin/env python3
import argparse
import json

from generator.campaigns import CAMPAIGNS
from generator.pipeline import generate_brand_video


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Colour Diam conversion ads")
    parser.add_argument("--format", choices=["vertical", "horizontal", "square"], default="vertical")
    parser.add_argument("--campaign", choices=sorted(CAMPAIGNS), default="register")
    parser.add_argument("--all", action="store_true", help="Render every campaign x format")
    args = parser.parse_args()
    if args.all:
        results = []
        for campaign in CAMPAIGNS:
            for fmt in ["vertical", "horizontal"]:
                results.append(generate_brand_video(fmt, campaign))
        print(json.dumps(results, indent=2))
        return
    result = generate_brand_video(args.format, args.campaign)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
