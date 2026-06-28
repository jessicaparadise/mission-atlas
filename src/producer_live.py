"""
LIVE ADS-B telemetry producer for Mission ATLAS.
Authenticates to OpenSky via OAuth2, pulls real aircraft over a
bounding box, and streams them into Kinesis — same record shape
as the synthetic producer, so everything downstream just works.
"""

import json
import time
from datetime import datetime, timezone, timedelta

import boto3
import requests

STREAM_NAME = "atlas-telemetry-dev"
REGION = "us-east-1"

TOKEN_URL = ("https://auth.opensky-network.org/auth/realms/"
             "opensky-network/protocol/openid-connect/token")
STATES_URL = "https://opensky-network.org/api/states/all"
CREDS_FILE = "credentials.json"

BBOX = {
    "lamin": 32.5,
    "lamax": 35.0,
    "lomin": -120.0,
    "lomax": -116.0,
}

POLL_INTERVAL_SEC = 10

kinesis = boto3.client("kinesis", region_name=REGION)

class TokenManager:
    """Fetches and caches an OpenSky access token, refreshing before expiry."""

    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = None
        self.expires_at = None

    def get(self):
        if self.token and self.expires_at and datetime.now() < self.expires_at:
            return self.token
        return self._refresh()

    def _refresh(self):
        resp = requests.post(TOKEN_URL, data={
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        })
        resp.raise_for_status()
        data = resp.json()
        self.token = data["access_token"]
        ttl = data.get("expires_in", 1800)
        self.expires_at = datetime.now() + timedelta(seconds=ttl - 30)
        print("🔑 Got fresh OpenSky token.")
        return self.token

def parse_state(s):
    """Map an OpenSky state-vector array into our telemetry record."""
    if s[5] is None or s[6] is None:
        return None
    return {
        "icao24": s[0],
        "callsign": (s[1] or "").strip() or "UNKNOWN",
        "origin_country": s[2],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "lon": s[5],
        "lat": s[6],
        "altitude_ft": round(s[7] * 3.281, 1) if s[7] else None,  # meters→feet
        "on_ground": s[8],
        "velocity_kt": round(s[9] * 1.944, 1) if s[9] else None,  # m/s→knots
        "heading_deg": s[10],
    }


def main():
    with open(CREDS_FILE) as f:
        creds = json.load(f)
    tokens = TokenManager(creds["clientId"], creds["clientSecret"])

    print(f"🛫 Streaming LIVE aircraft over SoCal → {STREAM_NAME}")
    print("Press Ctrl+C to stop.\n")

    sent = 0
    try:
        while True:
            resp = requests.get(
                    STATES_URL,
                    headers={"Authorization": f"Bearer {tokens.get()}"},
                    params=BBOX,
                )

            if resp.status_code == 429:
                print("⏳ Rate limited — backing off 30s.")
                time.sleep(30)
                continue
            resp.raise_for_status()

            states = resp.json().get("states") or []

            records = []
            for s in states:
                rec = parse_state(s)
                if rec is None:
                    continue
                records.append({
                    "Data": json.dumps(rec).encode("utf-8"),
                    "PartitionKey": rec["icao24"],   # ordering per aircraft
                })

            if records:
                kinesis.put_records(StreamName=STREAM_NAME, Records=records)
                sent += len(records)
                sample = ", ".join(
                    f"{json.loads(r['Data'])['callsign']}" for r in records[:3]
                )
                print(f"✈️  {len(records)} aircraft → Kinesis "
                      f"(total {sent}) | e.g. {sample} "
                      f"@ {datetime.now().strftime('%H:%M:%S')}")
            else:
                print(f"   No aircraft in box right now "
                      f"@ {datetime.now().strftime('%H:%M:%S')}")

            time.sleep(POLL_INTERVAL_SEC)

    except KeyboardInterrupt:
        print(f"\n🛬 Stopped. Streamed {sent} live aircraft records total.")


if __name__ == "__main__":
    main()