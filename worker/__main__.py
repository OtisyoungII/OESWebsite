import logging
import os
import sys
import threading
from .client import OutboundWorker


def main():
    logging.basicConfig(level=logging.WARNING, format='%(levelname)s %(message)s')
    # Never print configuration or raw exceptions (which can contain request data).
    try:
        worker = OutboundWorker(dict(os.environ))

        def control():
            # Optional cross-platform launcher control channel. Manual console startup
            # remains unchanged; only the exact local STOP command has meaning.
            try:
                for line in sys.stdin:
                    if line.rstrip('\r\n') == 'STOP':
                        worker.stop.set()
                        return
            except (OSError, ValueError):
                return

        threading.Thread(target=control, daemon=True, name='oes-worker-control').start()
        worker.run()
    except KeyboardInterrupt:
        pass
    except Exception:
        logging.error('Worker stopped: invalid configuration or runtime failure')
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()
