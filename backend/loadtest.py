"""Repeatable end-to-end WebSocket load test for ChatApp.

The measured latency is the time from sending a message to receiving that exact
message in the server broadcast.  Account creation, login, connection setup and
optional warm-up traffic are deliberately outside the measurement window.
"""

import argparse
import asyncio
import json
import math
import random
import statistics
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import websockets


@dataclass
class ClientResult:
    sent: int = 0
    acked: int = 0
    failures: int = 0
    latencies_ms: list[float] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def http_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"HTTP {error.code} on {url}: {body}") from error


def signup_and_login(base_url: str, username: str, password: str) -> str:
    try:
        http_json(f"{base_url}/auth/signup", {"username": username, "password": password})
    except RuntimeError as error:
        if "HTTP 409" not in str(error):
            raise
    return http_json(
        f"{base_url}/auth/login", {"username": username, "password": password}
    )["access_token"]


async def receive_matching_message(websocket: Any, text: str, timeout: float) -> None:
    """Drain broadcasts until the response for this particular send arrives."""
    deadline = asyncio.get_running_loop().time() + timeout
    while True:
        remaining = deadline - asyncio.get_running_loop().time()
        if remaining <= 0:
            raise TimeoutError(f"timed out waiting for broadcast after {timeout:.1f}s")
        incoming = json.loads(await asyncio.wait_for(websocket.recv(), remaining))
        if incoming.get("type") == "message" and incoming.get("text") == text:
            return
        if incoming.get("type") == "error":
            raise RuntimeError(incoming.get("error", "server returned an error"))


async def send_one(websocket: Any, text: str, timeout: float) -> float:
    started = time.perf_counter()
    await websocket.send(json.dumps({"type": "message", "text": text}))
    await receive_matching_message(websocket, text, timeout)
    return (time.perf_counter() - started) * 1000


async def run_client(
    client_id: int,
    run_id: str,
    base_http: str,
    base_ws: str,
    messages_per_client: int,
    warmup_messages: int,
    per_user_rate: float,
    timeout: float,
    ready_queue: asyncio.Queue,
    start_event: asyncio.Event,
) -> ClientResult:
    username = f"load{run_id}{client_id:05d}"
    result = ClientResult()
    try:
        token = await asyncio.to_thread(signup_and_login, base_http, username, "loadtest123")
        async with websockets.connect(
            f"{base_ws}/ws?token={token}", max_size=2**20, open_timeout=timeout
        ) as websocket:
            await asyncio.wait_for(websocket.recv(), timeout)
            for index in range(warmup_messages):
                text = f"lt:{run_id}:{client_id}:warmup:{index}:{uuid.uuid4().hex}"
                await send_one(websocket, text, timeout)

            await ready_queue.put(None)
            await start_event.wait()
            interval = 1 / per_user_rate if per_user_rate > 0 else 0
            next_send = time.perf_counter()
            for index in range(messages_per_client):
                if interval:
                    await asyncio.sleep(max(0, next_send - time.perf_counter()))
                    next_send += interval
                text = f"lt:{run_id}:{client_id}:{index}:{uuid.uuid4().hex}"
                result.sent += 1
                try:
                    result.latencies_ms.append(await send_one(websocket, text, timeout))
                    result.acked += 1
                except Exception as error:
                    result.failures += 1
                    result.errors.append(str(error))
    except Exception as error:
        result.failures += messages_per_client - result.sent
        result.errors.append(str(error))
        await ready_queue.put(None)
    return result


def percentile(values: list[float], percentile_value: float) -> float | None:
    """Return a linearly interpolated percentile (the common R-7 definition)."""
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile_value
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def build_report(
    results: list[ClientResult], users: int, messages: int, duration: float, run_id: str
) -> dict[str, Any]:
    latencies = [latency for result in results for latency in result.latencies_ms]
    sent = sum(result.sent for result in results)
    acked = sum(result.acked for result in results)
    failures = sum(result.failures for result in results)
    return {
        "run_id": run_id,
        "users": users,
        "messages_per_user": messages,
        "sent": sent,
        "acked": acked,
        "failures": failures,
        "error_rate": failures / max(sent + failures, 1),
        "duration_s": duration,
        "throughput_messages_s": acked / max(duration, 1e-9),
        "latency_ms": {
            "count": len(latencies),
            "min": min(latencies) if latencies else None,
            "mean": statistics.fmean(latencies) if latencies else None,
            "p50": percentile(latencies, 0.50),
            "p95": percentile(latencies, 0.95),
            "p99": percentile(latencies, 0.99),
            "max": max(latencies) if latencies else None,
        },
        "errors": [error for result in results for error in result.errors][:20],
    }


def print_report(report: dict[str, Any]) -> None:
    print("\n=== LOAD TEST RESULTS ===")
    print(
        f"users={report['users']} messages_per_user={report['messages_per_user']} "
        f"sent={report['sent']} acked={report['acked']} failures={report['failures']}"
    )
    print(
        f"duration_s={report['duration_s']:.3f} "
        f"throughput_messages_s={report['throughput_messages_s']:.2f} "
        f"error_rate={report['error_rate']:.2%}"
    )
    latency = report["latency_ms"]
    if latency["count"]:
        print(
            "broadcast_latency_ms "
            + " ".join(
                f"{key}={latency[key]:.2f}"
                for key in ("min", "mean", "p50", "p95", "p99", "max")
            )
        )
    else:
        print("broadcast_latency_ms unavailable (no acknowledgements received)")
    for error in report["errors"][:5]:
        print(f"error: {error}")


async def main() -> int:
    parser = argparse.ArgumentParser(description="Repeatable ChatApp WebSocket load test")
    parser.add_argument("--http-base", default="http://127.0.0.1:8000")
    parser.add_argument("--ws-base", default="ws://127.0.0.1:8000")
    parser.add_argument("--users", type=int, default=10)
    parser.add_argument("--messages", type=int, default=10, help="Measured messages per user")
    parser.add_argument("--warmup", type=int, default=1, help="Unmeasured messages per user")
    parser.add_argument("--rate", type=float, default=0, help="Messages/sec/user; 0 sends ASAP")
    parser.add_argument("--timeout", type=float, default=10, help="Per-message timeout in seconds")
    parser.add_argument("--output", type=Path, help="Write machine-readable JSON results")
    parser.add_argument("--max-error-rate", type=float, default=0.01)
    args = parser.parse_args()
    if args.users < 1 or args.messages < 1 or args.warmup < 0 or args.rate < 0:
        parser.error("users/messages must be positive; warmup/rate cannot be negative")

    run_id = f"{random.randrange(16**6):06x}"
    ready_queue: asyncio.Queue = asyncio.Queue()
    start_event = asyncio.Event()
    tasks = [
        asyncio.create_task(
            run_client(
                index, run_id, args.http_base.rstrip("/"), args.ws_base.rstrip("/"),
                args.messages, args.warmup, args.rate, args.timeout, ready_queue, start_event
            )
        )
        for index in range(args.users)
    ]
    for _ in range(args.users):
        await ready_queue.get()
    started = time.perf_counter()
    start_event.set()
    results = await asyncio.gather(*tasks)
    duration = time.perf_counter() - started
    report = build_report(results, args.users, args.messages, duration, run_id)
    print_report(report)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0 if report["error_rate"] <= args.max_error_rate else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
