import os
import signal
import threading
import time

from clio.signal import wait_for_signal


def test_wait_for_signal():
    def trigger():
        time.sleep(0.1)
        os.kill(os.getpid(), signal.SIGUSR1)

    t = threading.Thread(target=trigger)
    t.start()

    result = wait_for_signal(signal.SIGUSR1)
    assert result == "SIGUSR1"
    t.join()
