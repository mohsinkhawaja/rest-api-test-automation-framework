from contextlib import closing
from socket import AF_INET, SOCK_STREAM, socket
from threading import Thread
from time import monotonic, sleep

import pytest
import requests
import uvicorn

from qa_api.app import create_app


@pytest.fixture
def client():
    """Start a clean service on an OS-assigned loopback port for each test."""
    with closing(socket(AF_INET, SOCK_STREAM)) as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        server = uvicorn.Server(
            uvicorn.Config(
                create_app(),
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

            def call(method, path, **kwargs):
                with requests.Session() as session:
                    session.trust_env = False
                    return session.request(method, origin + path, timeout=3, **kwargs)

            yield call
        finally:
            server.should_exit = True
            worker.join(timeout=5)
            if worker.is_alive():
                pytest.fail("Uvicorn did not shut down within five seconds")
