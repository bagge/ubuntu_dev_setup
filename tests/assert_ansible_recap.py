#!/usr/bin/env python3
import argparse
import re
import sys
from pathlib import Path


RECAP_RE = re.compile(
    r"changed=(?P<changed>\d+).*failed=(?P<failed>\d+)",
    re.MULTILINE,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Assert Ansible recap counts")
    parser.add_argument("log", type=Path)
    parser.add_argument("--changed", type=int, required=True)
    parser.add_argument("--failed", type=int, required=True)
    args = parser.parse_args()

    text = args.log.read_text(encoding="utf-8", errors="replace")
    matches = list(RECAP_RE.finditer(text))
    if not matches:
        print(f"No Ansible recap found in {args.log}", file=sys.stderr)
        return 1

    recap = matches[-1]
    changed = int(recap.group("changed"))
    failed = int(recap.group("failed"))
    if changed != args.changed or failed != args.failed:
        print(
            f"Unexpected Ansible recap: changed={changed}, failed={failed}; "
            f"expected changed={args.changed}, failed={args.failed}",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
