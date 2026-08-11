import argparse
import asyncio
import json
import random
import statistics
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any
import websockets

@dataclass
class ClientResult:
    sent: int = 0
    acked: int = 0
    failures: int = 0
    latencies_ms: list[float] = None

    def __post_init__(self):
        if self.latencies_ms is None:
            self.latencies_ms = []

def http_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"HTTP {e.code} on {url}: {body}") from e

def signup_and_login(base_url: str, username: str, password: str) -> str:
    signup_url = f"{base_url}/auth/signup"
    login_url = f"{base_url}/auth/login"

    try:
        http_json(signup_url, {"username": username, "password": password})
    except RuntimeError as err:
        if "HTTP 409" not in str(err):
            raise

    login = http_json(login_url, {"username": username, "password": password})
    return login["access_token"]

async def run_client(
    client_id: int,
    base_http: str,
    base_ws: str,
    messages_per_client: int,
    start_event: asyncio.Event,
) -> ClientResult:
    username = f"loaduser{client_id:04d}"
    password = "loadtest123"
    result = ClientResult()

    try:
        token = signup_and_login(base_http, username, password)
    except Exception:
        result.failures += messages_per_client
        return result

    ws_url = f"{base_ws}/ws?token={token}"

    try:
        async with websockets.connect(ws_url, max_size=2**20) as ws:
            await ws.recv()
            await start_event.wait()

            for i in range(messages_per_client):
                payload = {
                    "type": "message",
                    "text": f"load test {client_id}-{i}-{random.randint(1000, 9999)}",
                }
                t0 = time.perf_counter()
                await ws.send(json.dumps(payload))
                result.sent += 1

                while True:
                    incoming = json.loads(await ws.recv())
                    if incoming.get("type") == "message" and incoming.get("client_id") == username:
                        t1 = time.perf_counter()
                        result.acked += 1
                        result.latencies_ms.append((t1 - t0) * 1000)
                        break
                    if incoming.get("type") == "error":
                        result.failures += 1
                        break
    except Exception:
        result.failures += max(messages_per_client - result.acked, 0)

    return result

def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = int((len(ordered) - 1) * p)
    return ordered[idx]

async def main() -> None:
    parser = argparse.ArgumentParser(description="Simple websocket load test for ChatApp")
    parser.add_argument("--http-base", default="http://127.0.0.1:8000", help="HTTP API base URL")
    parser.add_argument("--ws-base", default="ws://127.0.0.1:8000", help="WebSocket base URL")
    parser.add_argument("--users", type=int, default=10, help="Number of concurrent websocket clients")
    parser.add_argument("--messages", type=int, default=10, help="Messages per client")
    args = parser.parse_args()

    start_event = asyncio.Event()
    tasks = [
        asyncio.create_task(
            run_client(
                client_id=i,
                base_http=args.http_base,
                base_ws=args.ws_base,
                messages_per_client=args.messages,
                start_event=start_event,
            )
        )
        for i in range(args.users)
    ]

    t_start = time.perf_counter()
    start_event.set()
    results = await asyncio.gather(*tasks)
    t_end = time.perf_counter()

    all_latencies = [lat for r in results for lat in r.latencies_ms]
    total_sent = sum(r.sent for r in results)
    total_acked = sum(r.acked for r in results)
    total_failures = sum(r.failures for r in results)
    duration_s = max(t_end - t_start, 1e-9)

    print("\n=== LOAD TEST RESULTS ===")
    print(f"users={args.users} messages_per_client={args.messages}")
    print(f"sent={total_sent} acked={total_acked} failures={total_failures}")
    print(f"duration_s={duration_s:.3f} throughput_msg_s={total_acked / duration_s:.2f}")

    if all_latencies:
        print(
            "latency_ms "
            f"min={min(all_latencies):.2f} "
            f"p50={statistics.median(all_latencies):.2f} "
            f"p95={percentile(all_latencies, 0.95):.2f} "
            f"p99={percentile(all_latencies, 0.99):.2f} "
            f"max={max(all_latencies):.2f}"
        )
    else:
        print("latency_ms unavailable (no acknowledgements received)")


if __name__ == "__main__":
    asyncio.run(main())