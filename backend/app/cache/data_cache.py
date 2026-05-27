from datetime import datetime, timedelta

cached_data = None
last_fetch_time = None
cached_data_by_key = {}
last_fetch_time_by_key = {}

CACHE_DURATION = timedelta(minutes=5)
