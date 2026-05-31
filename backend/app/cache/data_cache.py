from datetime import datetime, timedelta
from threading import Lock

cached_data = None
last_fetch_time = None
cached_data_by_key = {}
last_fetch_time_by_key = {}
fetch_locks_by_key = {}
fetch_locks_guard = Lock()

CACHE_DURATION = timedelta(minutes=5)


def get_fetch_lock(cache_key):
    with fetch_locks_guard:
        if cache_key not in fetch_locks_by_key:
            fetch_locks_by_key[cache_key] = Lock()

        return fetch_locks_by_key[cache_key]
