import subprocess,sys,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def web():
    subprocess.run([sys.executable,"-m","uvicorn","app:app","--host","127.0.0.1","--port","8000"],cwd=ROOT)
def scheduler():
    subprocess.run([sys.executable,"-m","src.scheduler"],cwd=ROOT)
if __name__=="__main__":
    threading.Thread(target=web,daemon=True).start()
    scheduler()
