from datetime import datetime
class Logger:
    def info(self,msg): print(f"[{datetime.now().strftime('%H:%M:%S')}] INFO  {msg}")
    def error(self,msg): print(f"[{datetime.now().strftime('%H:%M:%S')}] ERROR {msg}")
