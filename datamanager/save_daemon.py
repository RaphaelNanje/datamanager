from threading import Thread
from time import sleep
from typing import List, Callable


class SaveDaemon(Thread):
    def __init__(self, sleep_interval=15, *args,
                 **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.go = True
        self.sleep = sleep_interval
        self.name = 'DataManager.SaveDaemon'
        self.funcs: List[Callable] = []

    def run(self) -> None:
        while self.go:
            for func in self.funcs:
                try:
                    func()
                except Exception as e:
                    print(e)
            sleep(self.sleep)
