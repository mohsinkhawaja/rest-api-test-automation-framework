from contextlib import closing, contextmanager
from socket import AF_INET, SOCK_STREAM, socket
from threading import Thread
from time import monotonic, sleep

import pytest
import requests
import uvicorn

from qa_api.app import create_app


@contextmanager
def _serve(app):
    """Start a clean service on an OS-assigned loopback port."""
    with closing(socket(AF_INET, SOCK_STREAM)) as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        server = uvicorn.Server(
            uvicorn.Config(
                app,
                log_level="warning",
                access_log=False,
                timeout_graceful_shutdown=2,
            )
        )
        worker = Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        worker.start()
        origin = f"http://127.0.0.1:{port}"
        try:
            deadline = monotonic() + 5
            while not server.started and worker.is_alive() and monotonic() < deadline:
                sleep(0.01)
            if not server.started:
                pytest.fail("Uvicorn did not start within five seconds")

            yield origin
        finally:
            server.should_exit = True
            worker.join(timeout=5)
            if worker.is_alive():
                pytest.fail("Uvicorn did not shut down within five seconds")


@pytest.fixture
def serve():
    return _serve


@pytest.fixture
def send():
    def call(method, url, **kwargs):
        with requests.Session() as session:
            session.trust_env = False
            return session.request(method, url, timeout=3, **kwargs)

    return call


@pytest.fixture
def client(send):
    with _serve(create_app()) as origin:
        yield lambda method, path, **kwargs: send(method, origin + path, **kwargs)
