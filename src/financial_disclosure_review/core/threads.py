"""Running sync Playwright work off the calling thread."""

from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context


def run_in_thread(fn, *args):
    """fn runs in the caller's context, so its model calls count against the caller's run meter."""
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(copy_context().run, fn, *args).result()
