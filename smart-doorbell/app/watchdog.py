from email.policy import default
import sys
import os
import argparse
import time
from datetime import datetime


class Watchdog():
    def __init__(self, path="/tmp/pywd") -> None:
        self.path = path

    def write(self):
        with open(self.path, 'w') as f:
            current_time = datetime.now().timestamp()
            f.write(str(current_time))

    def read(self):
        if not os.path.exists:
            return 0.0
        else:
            with open(self.path, 'r') as f:
                saved_time = float(f.read())
            return saved_time
    
    def test(self, threshold=15):
        current_time = datetime.now().timestamp()
        saved_time = self.read()

        if current_time - saved_time > threshold:
            return 1
        else:
            return 0
            

if __name__=="__main__":
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-t", "--test", help="test if app is running",
                    action="store_true")
    group.add_argument("-a", "--app", help="simulate app",
                    action="store_true")
    parser.add_argument("-i", "--interval", type=int, help="watchdog loop interval", default=5)
    parser.add_argument("-n", "--threshold", type=int, help="watchdog check threshold", default=10)
    parser.add_argument("-p", "--path", type=str, help="write path", default="/tmp/pywd")

    args = parser.parse_args()

    wd = Watchdog(path=args.path)
    ## app
    if args.app:
        while True:
            try:
                wd.write()
                time.sleep(args.interval)
            except KeyboardInterrupt:
                break

    ## test
    elif args.test:
        sys.stdout.write(repr(wd.test(args.threshold)) + "\n")
    else:
        print("No mode specified! Exiting...")