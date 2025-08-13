from datetime import datetime, date, time, timedelta, timezone
import re
from typing import Optional, Dict, Any

class NLPScheduleParser:
    """Rule-based lightweight Japanese schedule parser.
    Extracts target date, start time (if any), duration (estimated minutes), title, energy tag.
    """

    NOISE_PATTERNS = [
        "今日は", "明日", "明後日", "午前", "午後",
        r"\d{1,2}時\d{1,2}分", r"\d{1,2}時", r"\d{1,2}時間", r"\d{1,3}分",
        "書きたい", "したい"
    ]

    ENERGY_RULES = [
        (re.compile(r"集中|深く|ディープ|集中して"), "deep"),
        (re.compile(r"朝|午前"), "morning"),
        (re.compile(r"午後|昼"), "afternoon"),
    ]

    @classmethod
    def parse(cls, text: str, base_date: Optional[date] = None) -> Dict[str, Any]:
        text = (text or "").strip()
        if not text:
            return {"intents": [], "draft": None}

        today = base_date or date.today()
        target_date = today
        if "明日" in text:
            target_date = today + timedelta(days=1)
        elif "明後日" in text:
            target_date = today + timedelta(days=2)

        hour = 9
        minute = 0
        # full pattern hh時mm分
        tm = re.search(r"(午前|午後)?(\d{1,2})時(\d{1,2})分?", text)
        standalone_time_used = False
        if tm:
            h = int(tm.group(2))
            if tm.group(1) == "午後" and h < 12 and h != 12:
                h += 12
            hour = h
            minute = int(tm.group(3))
            standalone_time_used = True
        else:
            m = re.search(r"(午前|午後)?(\d{1,2})時", text)
            if m:
                h = int(m.group(2))
                if m.group(1) == "午後" and h < 12 and h != 12:
                    h += 12
                hour = h

        # duration inference
        duration = 60
        dm = None
        time_consumed_span_end = tm.end() if tm else 0
        dm_candidates = list(re.finditer(r"(\d{1,3})分", text))
        if dm_candidates:
            if standalone_time_used:
                for cand in dm_candidates:
                    if cand.start() >= time_consumed_span_end:
                        dm = cand
                        break
            else:
                dm = dm_candidates[0]
        hm = re.search(r"(\d{1,2})時間", text)
        if hm:
            duration = int(hm.group(1)) * 60
        elif dm:
            duration = min(480, int(dm.group(1)))

        start_dt = datetime.combine(target_date, time(hour=hour, minute=minute, tzinfo=timezone.utc))

        title = text
        for p in cls.NOISE_PATTERNS:
            title = re.sub(p, "", title)
        title = title.replace("  ", " ").strip(" 。、 ")
        title = re.sub(r"^(に|を|へ|で)+", "", title)
        if not title:
            title = "タスク"
        title = re.sub(r"(を|の|へ|に)$", "", title)

        # energy tag inference
        energy_tag = None
        for pattern, tag in cls.ENERGY_RULES:
            if pattern.search(text):
                # special handling: morning/afternoon tags only if hour consistent
                if tag == "morning" and hour < 11:
                    energy_tag = tag
                elif tag == "afternoon" and 11 <= hour <= 18:
                    energy_tag = tag
                elif tag == "deep":
                    energy_tag = tag
                if energy_tag:
                    break

        draft = {
            "title": title,
            "date": target_date.isoformat(),
            "startAt": start_dt.isoformat(),
            "estimatedMinutes": duration,
            "energyTag": energy_tag
        }
        return {"intents": [{"type": "create_task", "confidence": 0.9}], "draft": draft}


def parse_schedule_text(text: str) -> Dict[str, Any]:
    """Public helper used by API layer."""
    return NLPScheduleParser.parse(text)
