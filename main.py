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
            page.goto(self.path)
            content = page.content()

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(content.encode("utf-8"))


def main() -> None:
    with Camoufox() as browser:
        handler = functools.partial(RequestHandler, browser=browser)
        httpd = HTTPServer(("127.0.0.1", 1080), handler)
        httpd.serve_forever()


if __name__ == "__main__":
    main()
