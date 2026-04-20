"""CLI: python -m housing_policy_advisor.rag.ingest [options]"""
import argparse
import logging
import sys
from pathlib import Path


def _parse_source(value: str):
    """Parse 'category=path' argument."""
    if "=" not in value:
        raise argparse.ArgumentTypeError(f"Expected 'category=path', got: {value!r}")
    category, path = value.split("=", 1)
    return category.strip(), Path(path.strip())


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Ingest PDF corpus into the housing policy Chroma vector store.",
        prog="python -m housing_policy_advisor.rag.ingest",
    )
    parser.add_argument(
        "--source-dir",
        metavar="CATEGORY=PATH",
        action="append",
        dest="source_dirs",
        type=_parse_source,
        help="Category and directory pair, e.g. --source-dir academic=corpus/academic",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset the Chroma collection before ingesting",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Process at most N PDFs (for quick iteration)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Process PDFs but skip writing to Chroma",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG logging",
    )

    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    from housing_policy_advisor.rag.ingest.builder import IngestBuilder
    from housing_policy_advisor import config

    # Build sources dict — fall back to DEFAULT_PDF_SOURCES if none provided
    if args.source_dirs:
        sources = {cat: path for cat, path in args.source_dirs}
    else:
        sources = config.DEFAULT_PDF_SOURCES
        if not sources:
            print("No --source-dir provided and DEFAULT_PDF_SOURCES not configured.", file=sys.stderr)
            sys.exit(1)

    builder = IngestBuilder(reset=args.reset)
    total = builder.ingest_directories(sources, limit=args.limit, dry_run=args.dry_run)

    if args.dry_run:
        print(f"Dry run complete. Would have indexed {total} chunks.")
    else:
        print(f"Ingestion complete. {total} chunks indexed into '{config.CHROMA_COLLECTION_NAME}'.")


if __name__ == "__main__":
    main()
