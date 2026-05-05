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
        "--input-dir",
        action="append",
        dest="input_dirs",
        type=Path,
        help="Directory of PDFs to ingest (auto-category from folder name). "
        "Example: --input-dir data/corpus_additions/",
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
        "--policy-class",
        choices=("density_bonus", "adu", "affordable_dwelling_unit"),
        default=None,
        help="Optional classifier metadata tag for all ingested chunks",
    )
    parser.add_argument(
        "--doc-type",
        default=None,
        help='Optional classifier document type, e.g. "example_policy", "guidebook", or "definition"',
    )
    parser.add_argument(
        "--locality",
        default=None,
        help='Optional classifier locality tag, e.g. "fairfax" or "dc"',
    )
    parser.add_argument(
        "--ingest-version",
        default=None,
        help="Optional classifier ingest version tag; defaults to classifier_v1 when --policy-class is used",
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

    # Build sources dict — fall back to DEFAULT_PDF_SOURCES if none provided.
    # --input-dir is a convenience alias for one or more plain directories.
    sources = {}
    if args.source_dirs:
        sources.update({cat: path for cat, path in args.source_dirs})
    if args.input_dirs:
        for p in args.input_dirs:
            category = p.name.strip() or "input"
            sources[category] = p

    if sources:
        pass
    else:
        sources = config.DEFAULT_PDF_SOURCES
        if not sources:
            print("No --source-dir provided and DEFAULT_PDF_SOURCES not configured.", file=sys.stderr)
            sys.exit(1)

    builder = IngestBuilder(reset=args.reset)
    before = builder.db.get_stats()["total_chunks"]
    extra_metadata = {
        key: value
        for key, value in {
            "policy_class": args.policy_class,
            "doc_type": args.doc_type,
            "locality": args.locality,
            "ingest_version": args.ingest_version,
        }.items()
        if value is not None
    }
    total = builder.ingest_directories(
        sources,
        limit=args.limit,
        dry_run=args.dry_run,
        extra_metadata=extra_metadata,
    )

    if args.dry_run:
        print(f"Dry run complete. Would have indexed {total} chunks.")
        print(f"Total chunk count (unchanged): {before}")
    else:
        after = builder.db.get_stats()["total_chunks"]
        print(f"Ingestion complete. {total} chunks indexed into '{config.CHROMA_COLLECTION_NAME}'.")
        print(f"Total chunks before: {before}")
        print(f"Total chunks after:  {after}")


if __name__ == "__main__":
    main()
