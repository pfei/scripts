#!/usr/bin/env python3
"""
battery_monitor.py — Battery monitoring for Debian / MATE Desktop
Triggers notifications for low, critical, and high (overcharged) battery states.
"""

import os
import subprocess
import time
import logging
import glob

# ── Configuration ──────────────────────────────────────────────────────────────
THRESHOLD_HIGH = 90  # % : warning to unplug charger
THRESHOLD_CRITICAL = 10  # % : urgent notification
THRESHOLD_LOW = 25  # % : first warning
CHECK_INTERVAL = 60  # seconds between normal checks
SNOOZE_INTERVAL = 300  # seconds between notifications for low/high states
# ──────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
log = logging.getLogger(__name__)


def find_battery() -> str | None:
    """Automatically detects the battery path (BAT0, BAT1, …)."""
    candidates = glob.glob("/sys/class/power_supply/BAT*")
    for path in candidates:
        type_file = os.path.join(path, "type")
        try:
            with open(type_file) as f:
                if f.read().strip() == "Battery":
                    log.info("Battery detected: %s", path)
                    return path
        except FileNotFoundError:
            continue
    return None


def read_file(path: str) -> str | None:
    """Reads a sysfs file and returns its content, or None if missing."""
    try:
        with open(path) as f:
            return f.read().strip()
    except FileNotFoundError:
        log.warning("File not found: %s", path)
        return None


def get_dbus_env() -> dict:
    """
    Retrieves DISPLAY and DBUS_SESSION_BUS_ADDRESS so notify-send
    works even when run from a user systemd service.
    """
    env = os.environ.copy()
    if "DISPLAY" not in env:
        env["DISPLAY"] = ":0"
    if "DBUS_SESSION_BUS_ADDRESS" not in env:
        try:
            uid = subprocess.check_output(["id", "-u"], text=True).strip()
            bus_path = f"/run/user/{uid}/bus"
            if os.path.exists(bus_path):
                env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path={bus_path}"
        except Exception:
            pass
    return env


def send_notification(
    urgency: str, title: str, message: str, icon: str = "battery-caution"
) -> None:
    """Sends a persistent notification via notify-send."""
    env = get_dbus_env()
    # "0" forces the notification to remain visible until clicked on MATE
    timeout = "0"
    cmd = [
        "notify-send",
        "-u",
        urgency,
        "-t",
        timeout,
        "-i",
        icon,
        title,
        message,
    ]
    try:
        subprocess.run(cmd, env=env, check=True)
        log.info("Notification sent [%s]: %s", urgency, title)
    except subprocess.CalledProcessError as e:
        log.error("notify-send error: %s", e)
    except FileNotFoundError:
        log.error("notify-send not found — please install libnotify-bin.")


def check_battery(battery_path: str) -> float:
    """
    Checks the battery state and sends a notification if needed.
    Returns the recommended delay before the next check.
    """
    capacity_str = read_file(os.path.join(battery_path, "capacity"))
    status_str = read_file(os.path.join(battery_path, "status"))

    if capacity_str is None or status_str is None:
        return CHECK_INTERVAL

    capacity = int(capacity_str)
    status = status_str  # "Discharging", "Charging", "Full", "Unknown"

    log.info("Battery: %d%% [%s]", capacity, status)

    # --- Case 1: Battery is charging and gets too high ---
    if status == "Charging" and capacity >= THRESHOLD_HIGH:
        send_notification(
            "normal",
            "🔋 Battery High",
            f"Level: {capacity}%. Unplug the charger to protect battery health.",
            icon="battery-full-charging",
        )
        return SNOOZE_INTERVAL

    # If charging but hasn't reached 90%, or if full/unknown, sleep normally
    if status != "Discharging":
        return CHECK_INTERVAL

    # --- Case 2: Battery is discharging and getting low ---
    if capacity <= THRESHOLD_CRITICAL:
        send_notification(
            "critical",
            "⚠ Critical Battery!",
            f"Level: {capacity}%. Plug in the charger immediately.",
            icon="battery-caution",
        )
        return SNOOZE_INTERVAL

    if capacity <= THRESHOLD_LOW:
        send_notification(
            "normal",
            "🔋 Low Battery",
            f"Level: {capacity}%. Consider plugging in the charger.",
            icon="battery-caution",
        )
        return SNOOZE_INTERVAL

    return CHECK_INTERVAL


def main() -> None:
    log.info(
        "Starting battery monitor (thresholds: High %d%% / Low %d%% / Critical %d%%)",
        THRESHOLD_HIGH,
        THRESHOLD_LOW,
        THRESHOLD_CRITICAL,
    )

    battery_path = find_battery()
    if battery_path is None:
        log.error("No battery detected in /sys/class/power_supply/.")
        raise SystemExit(1)

    while True:
        delay = check_battery(battery_path)
        time.sleep(delay)


if __name__ == "__main__":
    main()
