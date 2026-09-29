import json
from pathlib import Path
from .local_pipeline import run_local_pipeline
ROOT=Path(__file__).resolve().parents[1]
def main():
    config=json.loads((ROOT/"config"/"config.json").read_text())
    print(json.dumps(run_local_pipeline(config,ROOT),indent=2))
if __name__=="__main__": main()
