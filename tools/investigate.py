"""Criminal data management CLI.

Pass a FIR, a name, a phone, or an ID. The system recovers skipped fields,
attaches the identity to the most probable cluster, and lists every link.
"""
import argparse
import sys

from tools.cms import build_index, ingest, print_ingest, INDEX_PATH
import os


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Ingest criminal data. Do not pick a slot — the system attaches "
            "the record by features, then expands every hidden link."
        )
    )
    parser.add_argument("text", nargs="*", help="Raw FIR text, name, phone, or ID")
    parser.add_argument("--rebuild-index", action="store_true")
    parser.add_argument("--file", help="Read input from a file")
    args = parser.parse_args()

    if args.rebuild_index or not os.path.exists(INDEX_PATH):
        build_index()

    if args.file:
        with open(args.file, "r", encoding="utf-8") as handle:
            text = handle.read()
    elif args.text:
        text = " ".join(args.text)
    else:
        parser.print_help()
        sys.exit(1)

    print_ingest(ingest(text))


if __name__ == "__main__":
    main()
