"""Existing provider contract over the authenticated in-memory job handoff."""
import queue
import threading
from .providers import ChatEvent


class OutboundWorkerProvider:
    def __init__(self, config):
        self.relay = config['_OES_WORKER_RELAY']
        if not self.relay.configured():
            raise ValueError('Worker disabled')
        self.cancelled = threading.Event()
        self.request_id = None
        self.attempt = 1

    def set_trace(self, request_id, attempt):
        self.request_id, self.attempt = request_id, attempt

    def stream(self, messages):
        return self.relay.stream(messages, self.cancelled, self.request_id, self.attempt)

    def cancel(self):
        self.cancelled.set()
        with self.relay.cv:
            self.relay.cv.notify_all()


def disconnect_aware(stream, provider):
    """Keep WSGI writes moving even while policy buffers a model response.

    Existing 'start' frames contain no model content and are ignored by the UI.
    A failed write closes this generator and cancels the provider's own job.
    One bounded pump exists only for an admitted outbound-provider request.
    """
    events = queue.Queue(maxsize=8)
    stop = threading.Event()
    sentinel = object()

    def put(value):
        while not stop.is_set():
            try:
                events.put(value, timeout=0.25)
                return
            except queue.Full:
                pass

    def pump():
        try:
            for event in stream:
                if stop.is_set():
                    break
                put(event)
        finally:
            stream.close()
            put(sentinel)

    thread = threading.Thread(target=pump, daemon=True, name='oes-inference')
    thread.start()
    try:
        while True:
            try:
                event = events.get(timeout=2)
            except queue.Empty:
                yield ChatEvent('start', {})
                continue
            if event is sentinel:
                return
            yield event
    finally:
        stop.set()
        provider.cancel()
        thread.join(timeout=1)
