from datetime import datetime


class Logger:
    def __init__(self, callback=None):
        self.callback = callback

    def info(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] INFO  {msg}")
        if self.callback:
            self.callback("log", msg)

    def error(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ERROR {msg}")
        if self.callback:
            self.callback("error", msg)
