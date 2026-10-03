import queue
import threading
import traceback


class Worker:
    """Runs one task at a time on a background thread so the window stays responsive.

    Tkinter widgets may only be touched from the main thread, so the task's log
    messages and result are passed back through a queue that the main loop polls.
    """

    POLL_MS = 50

    def __init__(self, root, log):
        self.root = root
        self.log = log
        self.queue = queue.Queue()
        self.busy = False
        self._poll()

    def run(self, fn, *args, on_done=None, on_error=None, **kwargs):
        """Call fn(*args, log=..., **kwargs) in the background.

        Afterwards on_done(result), or on_error(exception) if it raised, is called on the main thread.
        """
        if self.busy:
            self.log("A task is still running. Wait for it to finish.")
            return
        self.busy = True

        def target():
            try:
                result = fn(*args, log=lambda message: self.queue.put(("log", message)), **kwargs)
            except Exception as e:
                # ValueError/OSError are expected problems with the input; the log message is enough
                if not isinstance(e, (ValueError, OSError)):
                    traceback.print_exc()
                self.queue.put(("error", (on_error, e)))
            else:
                self.queue.put(("done", (on_done, result)))

        threading.Thread(target=target, daemon=True).start()

    def _poll(self):
        try:
            while True:
                kind, payload = self.queue.get_nowait()
                if kind == "log":
                    self.log(payload)
                elif kind == "error":
                    self.busy = False
                    on_error, error = payload
                    self.log(f"Error: {error}")
                    if on_error:
                        on_error(error)
                elif kind == "done":
                    self.busy = False
                    on_done, result = payload
                    if on_done:
                        on_done(result)
        except queue.Empty:
            pass
        self.root.after(self.POLL_MS, self._poll)
