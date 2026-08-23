"""Tests for browser cookie extraction."""

import sys
from http.cookiejar import Cookie
from types import SimpleNamespace
from unittest.mock import patch

from tp_mcp.auth.browser import SUPPORTED_BROWSERS, extract_tp_cookie


def _cookie(value: str, *, expires: int) -> Cookie:
    return Cookie(
        version=0,
        name="Production_tpAuth",
        value=value,
        port=None,
        port_specified=False,
        domain=".trainingpeaks.com",
        domain_specified=True,
        domain_initial_dot=True,
        path="/",
        path_specified=True,
        secure=True,
        expires=expires,
        discard=False,
        comment=None,
        comment_url=None,
        rest={},
    )


def _browser_module(cookie_sets: dict[str, list[Cookie]]) -> SimpleNamespace:
    functions = {}
    for browser in SUPPORTED_BROWSERS:
        cookies = cookie_sets.get(browser, [])
        functions[browser] = lambda domain_name, cookies=cookies: cookies
    return SimpleNamespace(**functions)


def test_expired_cookie_does_not_hide_later_valid_cookie():
    module = _browser_module({
        "chrome": [
            _cookie("expired-secret", expires=1),
            _cookie("valid-secret", expires=4_102_444_800),
        ]
    })

    with patch.dict(sys.modules, {"browser_cookie3": module}):
        result = extract_tp_cookie("chrome")

    assert result.success is True
    assert result.cookie == "valid-secret"
    assert "expired-secret" not in result.message


def test_auto_continues_after_expired_cookie_in_first_browser():
    module = _browser_module({
        "chrome": [_cookie("expired-secret", expires=1)],
        "firefox": [_cookie("valid-secret", expires=4_102_444_800)],
    })

    with patch.dict(sys.modules, {"browser_cookie3": module}):
        result = extract_tp_cookie()

    assert result.success is True
    assert result.browser == "firefox"
    assert result.cookie == "valid-secret"


def test_expired_cookie_reports_expiry_without_leaking_value():
    module = _browser_module({
        "chrome": [_cookie("expired-secret", expires=1_704_067_200)]
    })

    with patch.dict(sys.modules, {"browser_cookie3": module}):
        result = extract_tp_cookie("chrome")

    assert result.success is False
    assert result.cookie is None
    assert "expired" in result.message.lower()
    assert "2024-01-01" in result.message
    assert "expired-secret" not in result.message
