import threading


class BasePlugin(threading.Thread):
    def get_exports(self):
        pass

    def stop(self):
        pass
