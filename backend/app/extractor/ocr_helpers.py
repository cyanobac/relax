"""OCR helper functions for stress chart time extraction."""

from datetime import date, datetime, timedelta
from pathlib import Path
import platform
import re
import shutil

import cv2
import pytesseract


# Time axis label region
TIME_AXIS_Y_MIN = 780
TIME_AXIS_Y_MAX = 825


def configure_tesseract(cmd=None):
    """Point pytesseract at the Tesseract binary.

    In the Docker image Tesseract is on PATH, so this is a no-op there. On
    Windows dev machines it lives under Program Files and isn't on PATH, so we
    look there. Pass an explicit `cmd` to override.
    """
    if cmd:
        pytesseract.pytesseract.tesseract_cmd = cmd
        return
    if platform.system() == "Windows":
        default = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        if Path(default).exists():
            pytesseract.pytesseract.tesseract_cmd = default
    else:
        found = shutil.which("tesseract")
        if found:
            pytesseract.pytesseract.tesseract_cmd = found


def extract_time_from_region(img, x_start, x_end, y_start, y_end, debug=True):
    """Extract time text from a specific region using OCR."""
    region = img[y_start:y_end, x_start:x_end]

    if len(region.shape) == 3:
        region_gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    else:
        region_gray = region

    region_inv = cv2.bitwise_not(region_gray)
    _, region_binary = cv2.threshold(region_inv, 127, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    scale_factor = 4
    region_upscaled = cv2.resize(
        region_binary,
        (region_binary.shape[1] * scale_factor, region_binary.shape[0] * scale_factor),
        interpolation=cv2.INTER_CUBIC,
    )

    region_clean = cv2.medianBlur(region_upscaled, 13)

    if debug:
        cv2.imwrite(f"debug_ocr_{x_start}_{x_end}.png", region_clean)

    config = "--psm 7 -c tessedit_char_whitelist=0123456789:apm "
    text = pytesseract.image_to_string(region_clean, config=config).strip()

    return text


def parse_time_string(time_str, reference_date):
    """
    Parse time string like '2:27 pm', '5:08 am', '6 am', or '6am' into a datetime object.
    Handles common OCR errors like 'O' for '0', '|' for '1', etc.
    """
    if isinstance(reference_date, date) and not isinstance(reference_date, datetime):
        reference_date = datetime.combine(reference_date, datetime.min.time())

    time_str = time_str.lower().strip()
    time_str = re.sub(r"\s+", " ", time_str)

    time_str = time_str.replace("o", "0").replace("O", "0")
    time_str = time_str.replace("l", "1").replace("I", "1")
    time_str = time_str.replace("|", "1")
    time_str = time_str.replace("pm", " pm").replace("am", " am")

    patterns = [
        r"(\d{1,2})[:\.](\d{2})\s*(am|pm)",
        r"(\d{1,2})[:\.](\d{2})(am|pm)",
        r"(\d{1,2})[:\.](\d{1,3})\s*p",
        r"(\d{1,2})[:\.](\d{1,3})\s*a",
        r"(\d{1,2})\s+(am|pm)",
        r"(\d{1,2})(am|pm)",
        r"(\d{1,2})[:\.](\d{2})",
    ]

    for i, pattern in enumerate(patterns):
        match = re.search(pattern, time_str)
        if match:
            hour = int(match.group(1))

            if len(match.groups()) >= 3:
                minute = int(match.group(2))
                ampm = match.group(3)
            else:
                group2 = match.group(2)

                if group2[0].isdigit():
                    minute_str = group2
                    if len(minute_str) > 2:
                        minute_str = minute_str[:2]
                    minute = int(minute_str)

                    if i == 2 or "p" in time_str:
                        ampm = "pm"
                    elif i == 3 or "a" in time_str:
                        ampm = "am"
                    else:
                        ampm = "pm" if hour >= 12 else "am"
                else:
                    minute = 0
                    ampm = group2

            if ampm == "pm" and hour != 12:
                hour += 12
            elif ampm == "am" and hour == 12:
                hour = 0

            return reference_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

    raise ValueError(f"Could not parse time string: '{time_str}'")


def round_down_to_15min(dt):
    """Round datetime down to nearest 15-minute interval."""
    total_minutes = dt.hour * 60 + dt.minute
    rounded_minutes = (total_minutes // 15) * 15

    return dt.replace(
        hour=rounded_minutes // 60,
        minute=rounded_minutes % 60,
        second=0,
        microsecond=0,
    )


def extract_times_from_chart(img, reference_date, debug=True):
    """
    Extract start and end times from the chart's time axis.
    
    Handles Oura's edge cases:
    1. Late-night start (≥11 PM): x-axis shows previous day, data starts at midnight
    2. Early-morning end (<8 AM): chart may span into the day AFTER the given date
    
    Returns:
        (first_time, last_time) as datetime objects
    """
    left_text = extract_time_from_region(
        img, 20, 160, TIME_AXIS_Y_MIN, TIME_AXIS_Y_MAX, debug=debug
    )
    print(f"  Left label OCR: '{left_text}'")

    right_text = extract_time_from_region(
        img, 450, 640, TIME_AXIS_Y_MIN, TIME_AXIS_Y_MAX, debug=debug
    )
    print(f"  Right label OCR: '{right_text}'")

    first_time = parse_time_string(left_text, reference_date)
    
    # EDGE CASE 1: Late-night start (11 PM or later)
    # Oura shows x-axis starting from previous day
    if first_time.hour >= 23:
        print(f"  ⚠️  Detected late-night start time ({first_time.hour}:xx) - adjusting reference date back by 1 day")
        adjusted_reference = reference_date - timedelta(days=1)
        first_time = parse_time_string(left_text, adjusted_reference)
        last_time = parse_time_string(right_text, adjusted_reference)
        print(f"  ✓ Adjusted: first_time now on {first_time.date()}, last_time on {last_time.date()}")
    else:
        last_time = parse_time_string(right_text, reference_date)

    # Handle midnight crossing
    if last_time < first_time:
        last_time = last_time + timedelta(days=1)
    
    # EDGE CASE 2: Early-morning end (<8 AM) with late-night start
    # Chart may span TWO midnights (e.g., 11 PM on day 1 to 6 AM on day 3)
    # Check if the span seems too short (< 12 hours) despite crossing midnight
    if first_time.hour >= 23 and last_time.hour < 8:
        span_hours = (last_time - first_time).total_seconds() / 3600
        if span_hours < 12:
            print(f"  ⚠️  Detected early-morning end time ({last_time.hour}:xx) with short span ({span_hours:.1f}h)")
            print(f"     Chart likely spans TWO midnights - adding another day to end time")
            last_time = last_time + timedelta(days=1)
            print(f"  ✓ Adjusted: last_time now on {last_time.date()}")

    first_time = round_down_to_15min(first_time)
    last_time = round_down_to_15min(last_time)

    return first_time, last_time
