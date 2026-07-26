import functools
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer

from camoufox.sync_api import Browser, BrowserContext, Camoufox


class RequestHandler(BaseHTTPRequestHandler):
    browser: Browser | BrowserContext

    def __init__(self, *args, browser: Browser | BrowserContext, **kwargs) -> None:
        self.browser = browser
        super().__init__(*args, **kwargs)

    def do_GET(self) -> None:
        with self.browser.new_page() as page:
            response = page.goto(self.path)
            if response is None:
                self.send_response(HTTPStatus.GONE)
                self.end_headers()
            else:
                self.send_response(response.status)

                content_type = (
                    response.header_value("content-type") or "application/octet-stream"
                )
                self.send_header("Content-Type", content_type)

                self.end_headers()

                if content_type == "text/html":
                    self.wfile.write(page.content().encode("utf-8"))
                else:
                    self.wfile.write(response.body())


def main() -> None:
    with Camoufox() as browser:
        handler = functools.partial(RequestHandler, browser=browser)
        httpd = HTTPServer(("127.0.0.1", 1080), handler)
        httpd.serve_forever()


if __name__ == "__main__":
    main()
