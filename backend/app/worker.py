import logging
import signal
import threading

from app.bootstrap.container import build_services
from app.infrastructure.settings.config import Settings


def run():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    services, engine = build_services(Settings())
    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())
    try:
        services.health.ready()
        logging.info("P0 worker ready; no business handlers registered")
        while not stop.wait(30):
            services.health.ready()
    finally:
        engine.dispose()
        logging.info("worker stopped")


if __name__ == "__main__":
    run()
