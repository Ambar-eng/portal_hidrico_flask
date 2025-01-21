import threading
import socket


class ThreadWithReturnValue(threading.Thread):
    def __init__(self, *args, **keywords):
        threading.Thread.__init__(self, *args, **keywords)
        self._return = None

    def run(self):
        if self._target is not None:
            self._return = self._target(*self._args, **self._kwargs)
            print(self._return)

    def join(self, *args, **kwargs):
        threading.Thread.join(self, *args, **kwargs)
        return self._return


def is_open(ip, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((ip, int(port)))
        s.shutdown(2)
        return True
    except Exception as ex:
        print(ex)
        return False
