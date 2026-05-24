from datetime import datetime, timedelta

cached_data = None
last_fetch_time = None

CACHE_DURATION = timedelta(minutes=5)