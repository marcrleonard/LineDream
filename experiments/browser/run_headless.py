"""Serve site/ locally and run the benchmark in headless Chromium; prints the timings as JSON.

    python experiments/browser/run_headless.py [--chromium /path/to/chrome]
"""
import argparse
import functools
import http.server
import json
import pathlib
import threading

from playwright.sync_api import sync_playwright

SITE = pathlib.Path(__file__).resolve().parent / "site"


class Handler(http.server.SimpleHTTPRequestHandler):
	extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, ".wasm": "application/wasm", ".mjs": "text/javascript"}

	def log_message(self, *args):
		pass


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("--chromium", default=None, help="Chromium executable (default: Playwright's)")
	ap.add_argument("--screenshot", default=None)
	args = ap.parse_args()

	server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(SITE)))
	threading.Thread(target=server.serve_forever, daemon=True).start()
	url = f"http://127.0.0.1:{server.server_address[1]}/index.html"

	with sync_playwright() as p:
		browser = p.chromium.launch(executable_path=args.chromium, headless=True)
		page = browser.new_page(viewport={"width": 1200, "height": 1600})
		page.on("console", lambda m: print("[page]", m.text))
		page.goto(url)
		page.wait_for_function("window.benchDone === true", timeout=15 * 60 * 1000, polling=500)
		if args.screenshot:
			page.screenshot(path=args.screenshot, full_page=True)
		error = page.evaluate("window.benchError")
		results = page.evaluate("window.benchResults")
		browser.close()
	server.shutdown()
	if error:
		raise SystemExit(f"benchmark failed in the browser: {error}")
	print(json.dumps(results, indent=2))


if __name__ == "__main__":
	main()
