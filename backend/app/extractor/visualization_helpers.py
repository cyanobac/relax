"""Visualization helper functions for stress chart extraction."""

import cv2


def create_visualization(img, circles, df):
    """Create annotated visualization."""
    vis = img.copy()

    for (x, y, r) in circles:
        cv2.circle(vis, (x, y), r, (0, 255, 0), 2)
        cv2.circle(vis, (x, y), 2, (0, 0, 255), 3)

    if len(circles) > 0:
        first_x, first_y, _ = circles[0]
        last_x, last_y, _ = circles[-1]

        cv2.putText(
            vis,
            "START",
            (first_x - 30, first_y - 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (0, 255, 255),
            1,
        )
        cv2.putText(
            vis,
            df.iloc[0]["timestamp"].strftime("%H:%M"),
            (first_x - 30, first_y - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.3,
            (0, 255, 255),
            1,
        )

        cv2.putText(
            vis,
            "END",
            (last_x - 25, last_y - 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (0, 255, 255),
            1,
        )
        cv2.putText(
            vis,
            df.iloc[-1]["timestamp"].strftime("%H:%M"),
            (last_x - 25, last_y - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.3,
            (0, 255, 255),
            1,
        )

    return vis
