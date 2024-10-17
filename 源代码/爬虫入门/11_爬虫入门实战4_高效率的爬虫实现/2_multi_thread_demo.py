import threading
import time

def worker(num):
    print(f"Thread {num} started")
    time.sleep(2)
    print(f"Thread {num} finished")

threads = []
for i in range(5):
    t = threading.Thread(target=worker, args=(i,))
    threads.append(t)
    t.start()

for t in threads:
    t.join()

print("All threads completed")