from __future__ import annotations

import os
import sys

from ai_x_post import checker, generator, poster, rss


MAX_RETRIES = 3
DRY_RUN_ENV = "AI_X_POST_DRY_RUN"


def main() -> None:
    dry_run = os.environ.get(DRY_RUN_ENV) == "1"

    print("[1/4] Fetching RSS...")
    entries = rss.recent(limit=30)
    if not entries:
        print("No entries fetched. Aborting.")
        sys.exit(1)
    print(f"  {len(entries)} entries")

    post_text: str | None = None
    chosen_entry = None
    chosen_template = None

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"[2/4] Generating post (attempt {attempt}/{MAX_RETRIES})...")
        draft, entry, template = generator.generate(entries)
        print(f"  template: {template}")
        print(f"  source  : {entry.source}")
        print(f"  draft   : {draft}")

        print("[3/4] Self-checking...")
        ok, reason = checker.check(draft)
        if ok:
            post_text = draft
            chosen_entry = entry
            chosen_template = template
            print("  OK")
            break
        print(f"  NG: {reason}")

    if post_text is None:
        print("All attempts failed self-check. Aborting.")
        sys.exit(1)

    print("[4/4] Posting to X...")
    if dry_run:
        print("  (dry run — skipping actual post)")
        print(f"  would post: {post_text}")
    else:
        tweet_id = poster.post(post_text)
        print(f"  posted: https://x.com/i/web/status/{tweet_id}")

    print("Done.")
    print(f"  entry   : [{chosen_entry.source}] {chosen_entry.title}")
    print(f"  template: {chosen_template}")


if __name__ == "__main__":
    main()
