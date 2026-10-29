import argparse
import json
from pathlib import Path

from .app import serve
from .data import demo_csv, parse_csv
from .metrics import evaluate
from .report import render_report


def main():
    parser = argparse.ArgumentParser(description="Local healthcare ML evaluation and reports.")
    commands = parser.add_subparsers(dest="command", required=True)
    web = commands.add_parser("serve", help="Start the local dashboard")
    web.add_argument("--port", type=int, default=8765)
    demo = commands.add_parser("demo", help="Write reproducible synthetic CSV data")
    demo.add_argument("--output", type=Path, default=Path("synthetic-readmission.csv"))
    report = commands.add_parser("evaluate", help="Evaluate a CSV and export HTML")
    report.add_argument("csv", type=Path)
    report.add_argument("--threshold", type=float, default=0.5)
    report.add_argument("--group")
    report.add_argument("--output", type=Path, default=Path("report.html"))
    report.add_argument("--json", type=Path, help="Also save aggregate metrics as JSON")
    args = parser.parse_args()
    try:
        if args.command == "serve":
            serve(args.port)
        elif args.command == "demo":
            args.output.write_text(demo_csv(), encoding="utf-8")
            print(f"Wrote synthetic data: {args.output}")
        else:
            result = evaluate(parse_csv(args.csv.read_text(encoding="utf-8-sig")), args.threshold, args.group)
            args.output.write_text(render_report(result), encoding="utf-8")
            if args.json:
                args.json.write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
            print(f"Evaluated {result['overall']['n']:,} patients → {args.output}")
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
