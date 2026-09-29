import json, logging, time
from pathlib import Path
from .local_pipeline import run_local_pipeline
ROOT=Path(__file__).resolve().parents[1]
logging.basicConfig(level=logging.INFO,format="%(asctime)s | %(levelname)s | %(message)s")
def main():
    config=json.loads((ROOT/"config"/"config.json").read_text())
    interval=int(config.get("interval_minutes",60))*60
    while True:
        try:
            logging.info("Starting automatic Short job")
            logging.info("%s",run_local_pipeline(config,ROOT))
        except Exception:
            logging.exception("Short job failed; will retry next cycle")
        time.sleep(interval)
if __name__=="__main__": main()
