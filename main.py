#!/usr/bin/env python3
"""Log temperature readings from a Dracal RTD200 on macOS or Linux.

Requires Dracal's `dracal-usb-get` utility installed and a connected sensor.
No third-party Python packages are required.
"""

import argparse
import csv
import platform
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path


def get_dracal_tool_path():
    """Find dracal-usb-get on PATH or in common installation locations."""
    found = shutil.which("dracal-usb-get")
    if found:
        return found

    system = platform.system()
    if system == "Darwin":
        candidates = [
            "/Applications/DracalView.app/Contents/MacOS/dracal-usb-get",
            "/opt/homebrew/bin/dracal-usb-get",
            "/usr/local/bin/dracal-usb-get",
        ]
    elif system == "Linux":
        candidates = [
            "/usr/local/bin/dracal-usb-get",
            "/usr/bin/dracal-usb-get",
        ]
    else:
        raise RuntimeError(f"Unsupported operating system: {system}")

    for candidate in candidates:
        if Path(candidate).is_file():
            return candidate

    raise FileNotFoundError(
        "Cannot find dracal-usb-get. Install the Dracal command-line utilities "
        "and ensure dracal-usb-get is on your PATH, or supply --tool-path."
    )


def log_temperature(
    log_file="temperature_log.csv",
    interval=10.0,
    tool_path=None,
    serial_number=None,
):
    """Append timestamped Dracal RTD200 readings to CSV until interrupted."""
    if interval <= 0:
        raise ValueError("interval must be greater than zero")

    if tool_path is None:
        tool_path = get_dracal_tool_path()

    log_path = Path(log_file).expanduser()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not log_path.exists() or log_path.stat().st_size == 0

    command = [str(tool_path)]
    if serial_number:
        command += ["-s", str(serial_number)]
    command += ["-i", "0"]

    print(f"Platform: {platform.system()}")
    print(f"Dracal utility: {tool_path}")
    print(f"Logging to {log_path.resolve()} every {interval} second(s).")
    print("Press Ctrl+C to stop.")

    try:
        with log_path.open("a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            if write_header:
                writer.writerow(["timestamp", "temperature_C"])
                file.flush()

            while True:
                start = time.monotonic()
                try:
                    result = subprocess.run(
                        command,
                        capture_output=True,
                        text=True,
                        check=True,
                        timeout=10,
                    )
                    temperature = float(result.stdout.strip())
                    timestamp = datetime.now().astimezone().isoformat(
                        timespec="seconds"
                    )
                    writer.writerow([timestamp, temperature])
                    file.flush()
                    print(f"{timestamp}  {temperature:.2f} °C", flush=True)
                except (subprocess.SubprocessError, ValueError, OSError) as error:
                    print(f"Could not read temperature: {error}", flush=True)

                time.sleep(max(0, interval - (time.monotonic() - start)))
    except KeyboardInterrupt:
        print("\nLogging stopped.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interval", type=float, default=10.0,
                        help="Seconds between measurements (default: 10)")
    parser.add_argument("--log-file", default="temperature_log.csv",
                        help="Output CSV path (default: temperature_log.csv)")
    parser.add_argument("--tool-path", default=None,
                        help="Explicit path to dracal-usb-get")
    parser.add_argument("--serial-number", default=None,
                        help="Dracal sensor serial number (optional)")
    args = parser.parse_args()
    log_temperature(args.log_file, args.interval, args.tool_path, args.serial_number)


if __name__ == "__main__":
    main()
