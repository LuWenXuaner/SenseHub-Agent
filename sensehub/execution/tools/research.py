"""信息检索类工具：向大脑返回可写入回答的数据（非打开浏览器副作用）."""

from __future__ import annotations

import json
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from html import unescape
from typing import Any

_DEFAULT_TIMEOUT = 20
_MAX_FETCH_BYTES = 256_000
_MAX_TEXT_CHARS = 12_000
_TAG_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.I | re.S)
_BR_RE = re.compile(r"<br\s*/?>", re.I)
_BLOCK_END_RE = re.compile(r"</(p|div|li|tr|h[1-6])>", re.I)
_STRIP_TAG_RE = re.compile(r"<[^>]+>")


def _http_get(url: str, *, accept: str = "*/*") -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "SenseHub-Agent/1.0 (research tool)",
            "Accept": accept,
        },
    )
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=_DEFAULT_TIMEOUT, context=ctx) as resp:
        data = resp.read(_MAX_FETCH_BYTES + 1)
    if len(data) > _MAX_FETCH_BYTES:
        raise ValueError("响应过大，已拒绝")
    return data


def _html_to_text(raw: str) -> str:
    text = _TAG_RE.sub(" ", raw)
    text = _BR_RE.sub("\n", text)
    text = _BLOCK_END_RE.sub("\n", text)
    text = _STRIP_TAG_RE.sub(" ", text)
    text = unescape(text)
    lines = [ln.strip() for ln in text.splitlines()]
    compact = "\n".join(ln for ln in lines if ln)
    return compact[:_MAX_TEXT_CHARS]


def fetch_url(params: dict[str, Any]) -> dict[str, Any]:
    """HTTP GET 抓取网页并提取可读文本（returns_data=true）."""
    url = str(params.get("url", "")).strip()
    if not url:
        raise ValueError("url 不能为空")
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        body = _http_get(url, accept="text/html,application/json,text/plain,*/*")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code}: {url}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"无法访问: {exc.reason}") from exc

    charset = "utf-8"
    try:
        text_probe = body[:2048].decode("utf-8", errors="ignore")
        m = re.search(r'charset=["\']?([\w-]+)', text_probe, re.I)
        if m:
            charset = m.group(1)
    except Exception:
        pass

    decoded = body.decode(charset, errors="replace")
    content_type = "text"
    if decoded.lstrip().startswith(("{", "[")):
        try:
            parsed = json.loads(decoded)
            text = json.dumps(parsed, ensure_ascii=False, indent=2)[:_MAX_TEXT_CHARS]
            content_type = "json"
        except json.JSONDecodeError:
            text = _html_to_text(decoded)
    else:
        text = _html_to_text(decoded)

    return {
        "url": url,
        "content_type": content_type,
        "text": text,
        "chars": len(text),
    }


def _wmo_summary(code: int | None) -> str:
    """WMO 天气码 → 简短中文描述（Open-Meteo）."""
    if code is None:
        return ""
    table = {
        0: "晴",
        1: "大部晴朗",
        2: "局部多云",
        3: "多云",
        45: "雾",
        48: "雾凇",
        51: "小毛毛雨",
        53: "毛毛雨",
        55: "大毛毛雨",
        61: "小雨",
        63: "中雨",
        65: "大雨",
        71: "小雪",
        73: "中雪",
        75: "大雪",
        80: "阵雨",
        81: "中阵雨",
        82: "强阵雨",
        95: "雷暴",
    }
    return table.get(int(code), "多变")


def _geocode_open_meteo(name: str) -> dict[str, Any] | None:
    q = urllib.parse.quote(name.strip())
    url = (
        f"https://geocoding-api.open-meteo.com/v1/search?name={q}"
        f"&count=5&language=zh&format=json"
    )
    try:
        body = _http_get(url, accept="application/json")
        payload = json.loads(body.decode("utf-8"))
    except Exception:
        return None
    results = payload.get("results") or []
    if not results:
        return None
    # 中文查询优先选中国境内结果
    if re.search(r"[\u4e00-\u9fff]", name):
        for row in results:
            if str(row.get("country_code", "")).upper() == "CN":
                return row
    return results[0]


def _get_weather_open_meteo(geo: dict[str, Any], days: int) -> dict[str, Any]:
    lat = geo.get("latitude")
    lon = geo.get("longitude")
    if lat is None or lon is None:
        raise RuntimeError("地理编码缺少坐标")
    tz = urllib.parse.quote(str(geo.get("timezone") or "auto"))
    url = (
        "https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        "&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,weathercode"
        f"&timezone={tz}&forecast_days={days}"
    )
    body = _http_get(url, accept="application/json")
    payload = json.loads(body.decode("utf-8"))
    daily = payload.get("daily") or {}
    dates = daily.get("time") or []
    max_t = daily.get("temperature_2m_max") or []
    min_t = daily.get("temperature_2m_min") or []
    rain = daily.get("precipitation_probability_max") or []
    codes = daily.get("weathercode") or []
    label = str(geo.get("name") or "").strip()
    admin = str(geo.get("admin1") or "").strip()
    display = f"{label}（{admin}）" if admin and admin not in label else label
    forecasts = []
    for i, date in enumerate(dates[:days]):
        forecasts.append(
            {
                "date": date,
                "max_temp_c": str(int(round(max_t[i]))) if i < len(max_t) and max_t[i] is not None else "",
                "min_temp_c": str(int(round(min_t[i]))) if i < len(min_t) and min_t[i] is not None else "",
                "summary": _wmo_summary(codes[i] if i < len(codes) else None),
                "rain_chance": str(int(rain[i])) if i < len(rain) and rain[i] is not None else "",
                "wind_kmph": "",
            }
        )
    return {
        "location": display,
        "days": days,
        "forecasts": forecasts,
        "source": "open-meteo",
    }


def get_weather(params: dict[str, Any]) -> dict[str, Any]:
    """查询城市天气预报（Open-Meteo 地理编码 + 预报，中文城市更准确）."""
    location = str(params.get("location") or params.get("city") or "").strip()
    if not location:
        raise ValueError("location 不能为空")
    days = max(1, min(int(params.get("days", 2)), 3))

    geo = _geocode_open_meteo(location)
    if geo:
        try:
            return _get_weather_open_meteo(geo, days)
        except Exception:
            pass

    lang = str(params.get("lang", "zh"))
    encoded = urllib.parse.quote(location)
    url = f"https://wttr.in/{encoded}?format=j1&lang={lang}"

    try:
        body = _http_get(url, accept="application/json")
    except Exception as exc:
        raise RuntimeError(f"天气服务不可用: {exc}") from exc

    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError("天气数据解析失败") from exc

    area = (payload.get("nearest_area") or [{}])[0]
    area_name = ((area.get("areaName") or [{}])[0]).get("value") or location
    forecasts = []
    for day in (payload.get("weather") or [])[:days]:
        hourly = day.get("hourly") or []
        mid = hourly[len(hourly) // 2] if hourly else {}
        desc = ((mid.get("lang_zh") or mid.get("weatherDesc") or [{}])[0]).get("value", "")
        forecasts.append(
            {
                "date": day.get("date"),
                "max_temp_c": (day.get("maxtempC")),
                "min_temp_c": (day.get("mintempC")),
                "summary": desc,
                "rain_chance": mid.get("chanceofrain"),
                "wind_kmph": mid.get("windspeedKmph"),
            }
        )

    return {
        "location": area_name,
        "days": days,
        "forecasts": forecasts,
        "source": "wttr.in",
    }
