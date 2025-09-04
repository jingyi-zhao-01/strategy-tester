import sys
from argparse import ArgumentParser
from lib.log.log import Log
from cli.lambda_handler import (
    ingest_options_handler,
    ingest_option_snapshots_handler,
)


def main() -> int:
    parser = ArgumentParser(prog="strategy-tester", description="Strategy Tester CLI")
    subparsers = parser.add_subparsers(dest="command_group")

    # ingestion group
    ingest_parser = subparsers.add_parser("ingestion", help="Ingestion related commands")
    ingest_sub = ingest_parser.add_subparsers(dest="ingest_command")

    ingest_sub.add_parser("options", help="Ingest options universe")
    ingest_sub.add_parser("snapshots", help="Ingest option snapshots")

    # alias top-level group 'ingest' to match phrasing
    ingest_parser2 = subparsers.add_parser("ingest", help="Alias of 'ingestion'")
    ingest_sub2 = ingest_parser2.add_subparsers(dest="ingest_command")
    ingest_sub2.add_parser("options", help="Ingest options universe")

    # support literal: strategy-tester ingest_options_snapshots handler
    ios_parser = subparsers.add_parser(
        "ingest_options_snapshots",
        help="Invoke option snapshots ingestion handler",
    )
    ios_parser.add_argument("handler", nargs="?", default="handler")

    args, _extra = parser.parse_known_args()

    try:
        if args.command_group in ("ingestion", "ingest"):
            if args.ingest_command == "options":
                Log.info("Running ingestion: options")
                _ = ingest_options_handler(None, None)
                return 0
            if args.ingest_command == "snapshots":
                Log.info("Running ingestion: option snapshots")
                _ = ingest_option_snapshots_handler(None, None)
                return 0

        if getattr(args, "command_group", None) == "ingest_options_snapshots":
            Log.info("Running ingest_option_snapshots handler")
            _ = ingest_option_snapshots_handler(None, None)
            return 0

        # fallback for argv-based alias
        if getattr(args, "command_group", None) is None and "ingest_options_snapshots" in sys.argv:
            Log.info("Running alias: ingest option snapshots handler")
            _ = ingest_option_snapshots_handler(None, None)
            return 0

        parser.print_help()
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
