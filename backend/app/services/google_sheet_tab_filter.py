SKIPPED_TAB_KEYWORDS = (
    "configuration",
    "config",
    "summary",
    "dashboard",
    "template",
    "readme",
)


def is_skipped_tab(sheet_name: str) -> bool:
    normalized_name = str(sheet_name or "").strip().casefold()

    if not normalized_name:
        return True

    return any(keyword in normalized_name for keyword in SKIPPED_TAB_KEYWORDS)


def get_syncable_tabs(tabs: list[str]) -> list[str]:
    return [
        tab
        for tab in tabs
        if tab and not is_skipped_tab(tab)
    ]
