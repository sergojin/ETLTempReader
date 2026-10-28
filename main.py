import csv

import subprocess

import time

from datetime import datetime

from pathlib import Path

def log_temperature(

    log_file="temperature_log.csv",

    interval=10.0,

    tool_path="/Applications/DracalView.app/Contents/MacOS/dracal-usb-get",

    serial_number=None,

):

    """Log Dracal RTD200 temperature readings until interrupted."""

    if interval <= 0:

        raise ValueError("interval must be greater than zero")

    log_path = Path(log_file)

    write_header = not log_path.exists() or log_path.stat().st_size == 0

    command = [tool_path]

    if serial_number:

        command += ["-s", serial_number]

    command += ["-i", "0"]

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

                    print(f"{timestamp}  {temperature:.2f} °C")

                except (subprocess.SubprocessError, ValueError) as error:

                    print(f"Could not read temperature: {error}")

                # Account for the time spent taking the reading.

                time.sleep(max(0, interval - (time.monotonic() - start)))

    except KeyboardInterrupt:

        print("\nLogging stopped.")

if __name__ == "__main__":

    log_temperature(interval=10)