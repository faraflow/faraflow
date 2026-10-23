# Copyright 2026 Alokin LLC
# SPDX-License-Identifier: FCL-1.0-ALv2
"""Shared HTTP config for DriveUp crawl nodes.

A single User-Agent is used for every outbound request that fetches the *target
site* (JINA reader, robots.txt, homepage metadata), so the crawl presents a
consistent, browser-compatible-but-identifiable identity. Many WAFs 403 the
default `python-httpx/x.y` UA; a real browser string clears those, and the
appended `DriveUpBot` token keeps us honest and contactable.
"""

CRAWL_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 "
    "DriveUpBot/1.0 (+https://selfstorageapps.com/bot)"
)
