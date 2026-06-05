"""Image and time-series helper functions for stress chart extraction."""

from datetime import timedelta

import cv2
import numpy as np


# Zone definitions
ZONES = {
    "stressed": (260, 374),
    "engaged": (375, 486),
    "relaxed": (487, 596),
    "restored": (597, 724),
}

# Mask parameters
MASK_THRESHOLD = 50
DILATE_KERNEL_SIZE = 5
DILATE_ITERATIONS = 2

# Crop bounds
Y_MIN = 260
Y_MAX = 724


def load_precise_mask(mask_path, target_shape):
    """Load and process the mask_scaled.png file."""
    mask_img = cv2.imread(mask_path)
    if mask_img is None:
        raise FileNotFoundError(f"Could not load mask: {mask_path}")

    mask_img = cv2.resize(mask_img, (target_shape[1], target_shape[0]))
    mask_gray = cv2.cvtColor(mask_img, cv2.COLOR_BGR2GRAY)
    _, mask_binary = cv2.threshold(mask_gray, MASK_THRESHOLD, 255, cv2.THRESH_BINARY)

    mask_text = cv2.bitwise_not(mask_binary)
    kernel = np.ones((DILATE_KERNEL_SIZE, DILATE_KERNEL_SIZE), np.uint8)
    mask_text_dilated = cv2.dilate(mask_text, kernel, iterations=DILATE_ITERATIONS)
    final_mask = cv2.bitwise_not(mask_text_dilated)

    return final_mask


def preprocess_array(screenshot, mask_path):
    """Apply mask, crop, and preprocess an already-decoded BGR image array.

    Shares its logic with load_and_preprocess so the CLI (path-based) and the
    web API (bytes/array-based) produce identical results.
    """
    mask = load_precise_mask(mask_path, screenshot.shape)
    masked_screenshot = cv2.bitwise_and(screenshot, screenshot, mask=mask)
    cropped = masked_screenshot[Y_MIN:Y_MAX, :]
    gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)

    return screenshot, masked_screenshot, mask, blur


def load_and_preprocess(image_path, mask_path):
    """Load image from disk, apply mask, crop, preprocess."""
    screenshot = cv2.imread(image_path)
    if screenshot is None:
        raise FileNotFoundError(f"Could not load image: {image_path}")

    return preprocess_array(screenshot, mask_path)


def detect_dots(blur):
    """Detect circular dots using HoughCircles."""
    circles = cv2.HoughCircles(
        blur,
        cv2.HOUGH_GRADIENT,
        dp=1.0,
        minDist=8,
        param1=40,
        param2=10,
        minRadius=3,
        maxRadius=8,
    )

    if circles is None:
        raise RuntimeError("No dots detected")

    circles = np.round(circles[0, :]).astype("int")
    circles = sorted(circles, key=lambda c: c[0])
    return circles


def calculate_timestamp_from_x(x_pos, first_dot_x, last_dot_x, first_dot_time, last_dot_time):
    """Calculate timestamp based on x-position using linear interpolation."""
    total_seconds = (last_dot_time - first_dot_time).total_seconds()
    x_range = last_dot_x - first_dot_x
    x_offset = x_pos - first_dot_x
    time_offset_seconds = (x_offset / x_range) * total_seconds

    timestamp = first_dot_time + timedelta(seconds=time_offset_seconds)

    total_minutes = timestamp.hour * 60 + timestamp.minute
    rounded_minutes = round(total_minutes / 15) * 15

    if rounded_minutes >= 24 * 60:
        rounded_minutes -= 24 * 60
        timestamp = timestamp + timedelta(days=1)

    timestamp = timestamp.replace(
        hour=rounded_minutes // 60,
        minute=rounded_minutes % 60,
        second=0,
        microsecond=0,
    )

    return timestamp


def zone_for_y(y):
    """Return zone name for a given y-coordinate."""
    for zone, (ymin, ymax) in ZONES.items():
        if ymin <= y <= ymax:
            return zone
    return "unknown"


def detect_gaps(df, expected_interval_minutes=15):
    """Detect gaps in the time series data."""
    gaps = []
    for i in range(len(df) - 1):
        current_time = df.iloc[i]["timestamp"]
        next_time = df.iloc[i + 1]["timestamp"]
        time_diff = (next_time - current_time).total_seconds() / 60

        if time_diff > expected_interval_minutes * 1.5:
            gaps.append(
                {
                    "after": current_time,
                    "before": next_time,
                    "gap_minutes": time_diff,
                    "expected_minutes": expected_interval_minutes,
                    "missing_points": int(time_diff / expected_interval_minutes) - 1,
                }
            )

    return gaps
