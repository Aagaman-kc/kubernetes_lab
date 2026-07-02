import threading
import requests

URL = "http://backend"


def generate_load():
    while True:
        try:
            requests.get(URL, timeout=2)
        except Exception:
            pass


# Start 20 worker threads
for _ in range(20):
    t = threading.Thread(target=generate_load)
    t.daemon = True
    t.start()

# Keep the main process alive
while True:
    pass