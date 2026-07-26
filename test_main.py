import functools
import http.client
import http.server
import typing as typ
from pathlib import Path
from queue import Queue
from threading import Thread

import pytest
from camoufox.sync_api import Camoufox

from main import RequestHandler

TESTDATA = Path("./testdata")


@pytest.fixture(scope="class")
def proxy_server():
    q = Queue(maxsize=1)

    def run_thread(q: Queue):
        with Camoufox() as browser:
            handler = functools.partial(RequestHandler, browser=browser)
            httpd = http.server.HTTPServer(("127.0.0.1", 1080), handler)
            q.put(httpd)
            httpd.serve_forever()

    thread = Thread(target=run_thread, args=(q,))
    thread.start()
    httpd = typ.cast(http.server.HTTPServer, q.get())
    yield httpd
    httpd.shutdown()
    thread.join()


@pytest.fixture(scope="class")
def data_server():
    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler, directory=TESTDATA
    )
    httpd = http.server.HTTPServer(("127.0.0.1", 8000), handler)
    thread = Thread(target=httpd.serve_forever)
    thread.start()
    yield httpd
    httpd.shutdown()
    thread.join()


def client_connection(
    proxy_server: http.server.HTTPServer,
    data_server: http.server.HTTPServer,
    method: str,
    path: str,
):
    proxy_addr, proxy_port = proxy_server.server_address
    conn = http.client.HTTPConnection(typ.cast(str, proxy_addr), proxy_port)
    data_addr, data_port = data_server.server_address
    conn.request(method, f"http://{typ.cast(str, data_addr)}:{data_port}/{path}")
    return conn


class TestSingleSession:
    def test_read_index_html(
        self, proxy_server: http.server.HTTPServer, data_server: http.server.HTTPServer
    ):
        conn = client_connection(proxy_server, data_server, "GET", "/index.html")

        resp = conn.getresponse()
        assert resp.status == http.client.OK
        assert resp.getheader("content-type") == "text/html"

        text = str(resp.read())
        assert "Hello, World!" in text
        assert "Page Heading" in text
        assert "Lorem ipsum dolor sit amet" in text

    def test_read_bridge_jpg(
        self, proxy_server: http.server.HTTPServer, data_server: http.server.HTTPServer
    ):
        conn = client_connection(proxy_server, data_server, "GET", "/bridge.jpg")

        resp = conn.getresponse()
        assert resp.status == http.client.OK
        assert resp.getheader("content-type") == "image/jpeg"

        with open(TESTDATA / "bridge.jpg", "rb") as f:
            assert resp.read() == f.read()

    def test_read_generated_json(
        self, proxy_server: http.server.HTTPServer, data_server: http.server.HTTPServer
    ):
        conn = client_connection(proxy_server, data_server, "GET", "/generated.json")

        resp = conn.getresponse()
        assert resp.status == http.client.OK
        assert resp.getheader("content-type") == "application/json"

        with open(TESTDATA / "generated.json", "r") as f:
            assert lines_equal(f, (l.decode("utf-8") for l in resp))


def lines_equal(a: typ.Iterable[str], b: typ.Iterable[str]):
    def strip(i: typ.Iterable[str]):
        return (l.strip() for l in i)

    return list(strip(a)) == list(strip(b))
