import json
import random
import time
import uuid
from datetime import datetime, timezone

import boto3

STREAM_NAME = "atlas-telemetry-dev"
REGION = "us-east-1"
NUM_AIRCRAFT = 5          
SEND_INTERVAL_SEC = 2    

kinesis = boto3.client("kinesis", region_name=REGION)


def make_fleet(n):
    """Create n fake aircraft with stable IDs and starting positions."""
    fleet = []
    for _ in range(n):
        fleet.append({
            "icao24": uuid.uuid4().hex[:6],
            "callsign": f"ATL{random.randint(100, 999)}",
            "lat": random.uniform(32.0, 42.0),    # roughly US airspace
            "lon": random.uniform(-120.0, -95.0),
            "altitude": random.uniform(30000, 40000),   # feet
            "velocity": random.uniform(400, 550),        # knots
            "heading": random.uniform(0, 360),           # degrees
        })
    return fleet


def step(aircraft):
    """Advance one aircraft's position a little, like it's actually flying."""
    aircraft["lat"] += random.uniform(-0.05, 0.05)
    aircraft["lon"] += random.uniform(-0.05, 0.05)
    aircraft["altitude"] += random.uniform(-200, 200)
    aircraft["velocity"] += random.uniform(-10, 10)
    aircraft["heading"] = (aircraft["heading"] + random.uniform(-5, 5)) % 360
    return aircraft


def to_record(aircraft):
    """Shape one aircraft into a telemetry record with a timestamp."""
    return {
        "icao24": aircraft["icao24"],
        "callsign": aircraft["callsign"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "lat": round(aircraft["lat"], 5),
        "lon": round(aircraft["lon"], 5),
        "altitude_ft": round(aircraft["altitude"], 1),
        "velocity_kt": round(aircraft["velocity"], 1),
        "heading_deg": round(aircraft["heading"], 1),
    }


def main():
    fleet = make_fleet(NUM_AIRCRAFT)
    print(f"🛫 Generating telemetry for {NUM_AIRCRAFT} aircraft → {STREAM_NAME}")
    print("Press Ctrl+C to stop.\n")

    sent = 0
    try:
        while True:
            records = []
            for aircraft in fleet:
                step(aircraft)
                data = to_record(aircraft)
                records.append({
                    "Data": json.dumps(data).encode("utf-8"),
                    "PartitionKey": aircraft["icao24"],
                })

            resp = kinesis.put_records(StreamName=STREAM_NAME, Records=records)

            sent += len(records)
            failed = resp.get("FailedRecordCount", 0)
            print(f"Sent {len(records)} records "
                  f"(total {sent}, failed {failed}) "
                  f"at {datetime.now().strftime('%H:%M:%S')}")

            time.sleep(SEND_INTERVAL_SEC)

    except KeyboardInterrupt:
        print(f"\n🛬 Stopped. Sent {sent} records total.")


if __name__ == "__main__":
    main()