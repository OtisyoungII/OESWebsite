import logging
import os
from .client import OutboundWorker


def main():
    logging.basicConfig(level=logging.WARNING, format='%(levelname)s %(message)s')
    # Never print configuration or raw exceptions (which can contain request data).
    try:
        OutboundWorker(dict(os.environ)).run()
    except KeyboardInterrupt:
        pass
    except Exception:
        logging.error('Worker stopped: invalid configuration or runtime failure')
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()
