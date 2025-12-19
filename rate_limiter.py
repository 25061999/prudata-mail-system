import time

LAST_SENT = 0

def allow_send(delay=5):
    global LAST_SENT
    now = time.time()
    if now - LAST_SENT < delay:
        time.sleep(delay - (now - LAST_SENT))
    LAST_SENT = time.time()
