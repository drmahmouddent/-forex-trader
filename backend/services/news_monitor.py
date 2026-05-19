"""
News Monitor Service
Real-time forex news monitoring with high-impact event detection
Prevents trading during volatile news events
"""

import requests
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from dataclasses import dataclass, field
from enum import Enum
import logging
import json
from pathlib import Path
import threading
import time

from config.settings import config

logger = logging.getLogger(__name__)


class ImpactLevel(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3


@dataclass
class NewsEvent:
    """Represents a forex news event"""
    title: str
    currency: str
    impact: ImpactLevel
    time: datetime
    forecast: str = ""
    previous: str = ""
    actual: str = ""
    source: str = ""

    @property
    def is_high_impact(self) -> bool:
        return self.impact == ImpactLevel.HIGH

    @property
    def is_medium_impact(self) -> bool:
        return self.impact == ImpactLevel.MEDIUM

    def minutes_until(self) -> float:
        """Minutes until this event occurs"""
        delta = self.time - datetime.utcnow()
        return delta.total_seconds() / 60

    def is_active(self, buffer_minutes: int = 30) -> bool:
        """Check if we're within the buffer window of this event"""
        minutes = self.minutes_until()
        return -buffer_minutes <= minutes <= buffer_minutes


class NewsMonitor:
    """Monitors forex news and manages trading blackouts"""

    def __init__(self):
        self.events: List[NewsEvent] = []
        self.last_update: Optional[datetime] = None
        self.update_interval = 300  # 5 minutes
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._blackout_active = False
        self._blackout_reason = ""
        self._cache_file = Path("data/news_cache.json")

    def start(self):
        """Start the news monitoring thread"""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("News monitor started")

    def stop(self):
        """Stop the news monitoring thread"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)
        logger.info("News monitor stopped")

    def _monitor_loop(self):
        """Main monitoring loop"""
        while self._running:
            try:
                self.update_events()
                self._check_blackout()
                time.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"News monitor error: {e}")
                time.sleep(60)

    def update_events(self):
        """Fetch latest news events from all sources"""
        events = []

        # Source 1: ForexFactory-style calendar
        events.extend(self._fetch_forex_factory())

        # Source 2: Investing.com calendar
        events.extend(self._fetch_investing_com())

        # Source 3: Finnhub economic calendar
        events.extend(self._fetch_finnhub())

        # Filter for relevant currencies
        watched = set(config.news.currencies_to_watch)
        events = [e for e in events if e.currency in watched]

        # Sort by time
        events.sort(key=lambda e: e.time)

        self.events = events
        self.last_update = datetime.utcnow()

        # Cache events
        self._save_cache()

        logger.info(f"Updated news events: {len(events)} events found")

    def _fetch_forex_factory(self) -> List[NewsEvent]:
        """Fetch from ForexFactory-style API"""
        events = []
        try:
            # Using a free forex calendar API
            url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                for item in data:
                    impact_map = {
                        "High": ImpactLevel.HIGH,
                        "Medium": ImpactLevel.MEDIUM,
                        "Low": ImpactLevel.LOW
                    }

                    event_time = datetime.strptime(
                        item.get("date", ""), "%Y-%m-%dT%H:%M:%S%z"
                    ).replace(tzinfo=None)

                    events.append(NewsEvent(
                        title=item.get("title", ""),
                        currency=item.get("currency", ""),
                        impact=impact_map.get(item.get("impact", "Low"), ImpactLevel.LOW),
                        time=event_time,
                        forecast=item.get("forecast", ""),
                        previous=item.get("previous", ""),
                        source="forex_factory"
                    ))

        except Exception as e:
            logger.warning(f"ForexFactory fetch failed: {e}")

        return events

    def _fetch_investing_com(self) -> List[NewsEvent]:
        """Fetch from Investing.com economic calendar"""
        events = []
        try:
            # Using investing.com economic calendar API
            url = "https://economic-calendar.tradingview.com/events"
            headers = {"User-Agent": "Mozilla/5.0"}
            params = {
                "from": datetime.utcnow().isoformat(),
                "to": (datetime.utcnow() + timedelta(days=7)).isoformat(),
                "countries": "US,EU"
            }

            response = requests.get(url, headers=headers, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                for item in data.get("result", []):
                    impact_map = {1: ImpactLevel.LOW, 2: ImpactLevel.MEDIUM, 3: ImpactLevel.HIGH}

                    event_time = datetime.fromisoformat(
                        item.get("date", "").replace("Z", "+00:00")
                    ).replace(tzinfo=None)

                    events.append(NewsEvent(
                        title=item.get("title", ""),
                        currency=item.get("country", ""),
                        impact=impact_map.get(item.get("importance", 1), ImpactLevel.LOW),
                        time=event_time,
                        forecast=str(item.get("forecast", "")),
                        previous=str(item.get("previous", "")),
                        source="investing_com"
                    ))

        except Exception as e:
            logger.warning(f"Investing.com fetch failed: {e}")

        return events

    def _fetch_finnhub(self) -> List[NewsEvent]:
        """Fetch from Finnhub economic calendar"""
        events = []
        try:
            # Finnhub provides free economic calendar
            url = "https://finnhub.io/api/v1/calendar/economic"
            params = {"token": "free"}  # Free tier

            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                for item in data.get("economicCalendar", []):
                    event_time = datetime.fromtimestamp(item.get("time", 0))

                    events.append(NewsEvent(
                        title=item.get("event", ""),
                        currency=item.get("country", "US"),
                        impact=ImpactLevel.HIGH if item.get("impact", 0) >= 3 else ImpactLevel.MEDIUM,
                        time=event_time,
                        forecast=str(item.get("forecast", "")),
                        previous=str(item.get("previous", "")),
                        source="finnhub"
                    ))

        except Exception as e:
            logger.warning(f"Finnhub fetch failed: {e}")

        return events

    def _check_blackout(self):
        """Check if we should be in trading blackout"""
        if not config.news.enabled:
            self._blackout_active = False
            return

        now = datetime.utcnow()

        for event in self.events:
            if not event.is_high_impact and not event.is_medium_impact:
                continue

            buffer = config.news.high_impact_buffer_minutes if event.is_high_impact else config.news.medium_impact_buffer_minutes

            time_diff = (event.time - now).total_seconds() / 60

            if -buffer <= time_diff <= buffer:
                self._blackout_active = True
                self._blackout_reason = (
                    f"{event.impact.name} impact: {event.title} "
                    f"({event.currency}) at {event.time.strftime('%H:%M UTC')}"
                )
                logger.warning(f"TRADING BLACKOUT: {self._blackout_reason}")
                return

        self._blackout_active = False
        self._blackout_reason = ""

    def is_blackout_active(self) -> bool:
        """Check if trading blackout is currently active"""
        return self._blackout_active

    def get_blackout_reason(self) -> str:
        """Get reason for current blackout"""
        return self._blackout_reason

    def get_upcoming_events(self, hours: int = 24) -> List[Dict]:
        """Get upcoming events within specified hours"""
        cutoff = datetime.utcnow() + timedelta(hours=hours)
        upcoming = [
            {
                "title": e.title,
                "currency": e.currency,
                "impact": e.impact.name,
                "time": e.time.isoformat(),
                "forecast": e.forecast,
                "previous": e.previous,
                "minutes_until": round(e.minutes_until(), 1)
            }
            for e in self.events
            if e.time <= cutoff and e.time >= datetime.utcnow() - timedelta(hours=1)
        ]
        return upcoming

    def get_next_high_impact(self) -> Optional[Dict]:
        """Get the next high-impact event"""
        now = datetime.utcnow()
        for event in self.events:
            if event.is_high_impact and event.time > now:
                return {
                    "title": event.title,
                    "currency": event.currency,
                    "time": event.time.isoformat(),
                    "minutes_until": round(event.minutes_until(), 1)
                }
        return None

    def _save_cache(self):
        """Save events to cache file"""
        try:
            self._cache_file.parent.mkdir(exist_ok=True)
            data = {
                "last_update": self.last_update.isoformat() if self.last_update else None,
                "events": [
                    {
                        "title": e.title,
                        "currency": e.currency,
                        "impact": e.impact.name,
                        "time": e.time.isoformat(),
                        "forecast": e.forecast,
                        "previous": e.previous,
                        "source": e.source
                    }
                    for e in self.events
                ]
            }
            self._cache_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.warning(f"Failed to save news cache: {e}")

    def load_cache(self):
        """Load events from cache"""
        try:
            if self._cache_file.exists():
                data = json.loads(self._cache_file.read_text())
                self.last_update = datetime.fromisoformat(data["last_update"]) if data.get("last_update") else None
                self.events = [
                    NewsEvent(
                        title=e["title"],
                        currency=e["currency"],
                        impact=ImpactLevel[e["impact"]],
                        time=datetime.fromisoformat(e["time"]),
                        forecast=e.get("forecast", ""),
                        previous=e.get("previous", ""),
                        source=e.get("source", "")
                    )
                    for e in data.get("events", [])
                ]
                logger.info(f"Loaded {len(self.events)} events from cache")
        except Exception as e:
            logger.warning(f"Failed to load news cache: {e}")


# Global news monitor instance
news_monitor = NewsMonitor()
