import json
from pathlib import Path

from .pipeline import run_pipeline

ROOT = Path(__file__).resolve().parents[1]


def main():
    config = json.loads((ROOT / "config" / "config.json").read_text(encoding="utf-8"))
    result = run_pipeline(config, ROOT)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
