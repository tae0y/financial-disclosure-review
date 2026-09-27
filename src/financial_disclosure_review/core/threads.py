"""Running sync Playwright work off the calling thread."""

from concurrent.futures import ThreadPoolExecutor


def run_in_thread(fn, *args):
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(fn, *args).result()
