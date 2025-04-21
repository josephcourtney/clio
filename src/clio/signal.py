import signal
import threading


def wait_for_signal(signum: int) -> str:
    received = threading.Event()
    signal_name: list[str] = []

    def handler(signum_: int, _frame: object) -> None:
        signal_name.append(signal.Signals(signum_).name)
        received.set()

    _ = signal.signal(signum, handler)
    _ = received.wait()
    return signal_name[0]
