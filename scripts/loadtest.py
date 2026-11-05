#!/usr/bin/env python3
"""Production load test for iota-api.

Speaks HTTP/1.1 over a raw socket with keep-alive. A full HTTP client
library (httpx, requests) spends more CPU on the client side than the
server spends serving the request, which makes the measurement useless
when the load generator shares the box with the server.

Usage:
    python3 scripts/loadtest.py --url http://127.0.0.1:8000
    python3 scripts/loadtest.py --path /health/live --requests 5000 --connections 100
    python3 scripts/loadtest.py --path /stream/yt:ID --key "$API_KEY"

The report includes the server's CPU time per request, which is the
number that decides how many workers and replicas a deployment needs.
"""
from __future__ import annotations

import argparse
import asyncio
import glob
import json
import os
import statistics
import time
from typing import Iterable, List, Optional, Tuple
from urllib.parse import urlsplit

_CLOCK = os.sysconf("SC_CLK_TCK")


def _server_pids(pattern: str = "uvicorn") -> set[int]:
    pids: set[int] = set()
    for entry in glob.glob("/proc/[0-9]*"):
        try:
            with open(f"{entry}/cmdline", "rb") as fh:
                cmd = fh.read().decode(errors="ignore")
        except OSError:
            continue
        if pattern in cmd or "multiprocessing-fork" in cmd:
            pids.add(int(entry.rsplit("/", 1)[-1]))
    return pids


def _cpu_seconds(pids: Iterable[int]) -> float:
    total = 0.0
    for pid in pids:
        try:
            with open(f"/proc/{pid}/stat") as fh:
                fields = fh.read().rsplit(")", 1)[1].split()
            total += (int(fields[11]) + int(fields[12])) / _CLOCK
        except (OSError, IndexError, ValueError):
            continue
    return total


def _build_request(host: str, path: str, key: Optional[str]) -> bytes:
    headers = [
        f"GET {path} HTTP/1.1",
        f"Host: {host}",
        "Connection: keep-alive",
        "User-Agent: iota-loadtest",
        "Accept: */*",
    ]
    if key:
        headers.append(f"X-API-Key: {key}")
    return ("\r\n".join(headers) + "\r\n\r\n").encode()


async def _read_response(reader: asyncio.StreamReader) -> int:
    status_line = await reader.readuntil(b"\r\n")
    status = int(status_line.split(b" ")[1])
    length = 0
    chunked = False
    while True:
        line = await reader.readuntil(b"\r\n")
        if line == b"\r\n":
            break
        lower = line.lower()
        if lower.startswith(b"content-length:"):
            length = int(line.split(b":", 1)[1].strip())
        elif lower.startswith(b"transfer-encoding:") and b"chunked" in lower:
            chunked = True
    if chunked:
        while True:
            size = int((await reader.readuntil(b"\r\n")).strip(), 16)
            if size == 0:
                await reader.readuntil(b"\r\n")
                break
            await reader.readexactly(size + 2)
    elif length:
        await reader.readexactly(length)
    return status


async def _worker(
    host: str, port: int, path: str, key: Optional[str],
    count: int, bucket: List[Tuple[int, float]],
) -> None:
    reader, writer = await asyncio.open_connection(host, port)
    request = _build_request(f"{host}:{port}", path, key)
    try:
        for _ in range(count):
            started = time.perf_counter()
            writer.write(request)
            await writer.drain()
            status = await _read_response(reader)
            bucket.append((status, (time.perf_counter() - started) * 1000))
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass


async def run(
    url: str, path: str, key: Optional[str], requests: int, connections: int,
) -> dict:
    parts = urlsplit(url)
    host = parts.hostname or "127.0.0.1"
    port = parts.port or (443 if parts.scheme == "https" else 80)
    per = max(1, requests // connections)
    buckets: List[List[Tuple[int, float]]] = [[] for _ in range(connections)]

    pids = _server_pids()
    cpu_before = _cpu_seconds(pids)
    started = time.perf_counter()
    await asyncio.gather(*[
        _worker(host, port, path, key, per, buckets[i])
        for i in range(connections)
    ])
    elapsed = time.perf_counter() - started
    cpu_after = _cpu_seconds(pids)

    flat = [item for bucket in buckets for item in bucket]
    latencies = sorted(item[1] for item in flat)
    codes: dict = {}
    for status, _ in flat:
        codes[str(status)] = codes.get(str(status), 0) + 1
    count = len(flat)
    cpu_used = max(0.0, cpu_after - cpu_before)
    return {
        "url": f"{host}:{port}{path}",
        "requests": count,
        "connections": connections,
        "wall_seconds": round(elapsed, 3),
        "requests_per_second": round(count / elapsed, 1),
        "status_codes": codes,
        "latency_ms": {
            "p50": round(statistics.median(latencies), 2),
            "p95": round(latencies[int(count * 0.95) - 1], 2),
            "p99": round(latencies[int(count * 0.99) - 1], 2),
            "max": round(latencies[-1], 2),
        },
        "server_cpu_seconds": round(cpu_used, 3),
        "server_cpu_cores_used": round(cpu_used / elapsed, 2),
        "server_cpu_ms_per_request": round(cpu_used / count * 1000, 3),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--path", default="/health/live")
    parser.add_argument("--key", default=os.getenv("IOTA_API_KEY"))
    parser.add_argument("--requests", type=int, default=3000)
    parser.add_argument("--connections", type=int, default=50)
    args = parser.parse_args()
    report = asyncio.run(run(
        args.url, args.path, args.key, args.requests, args.connections,
    ))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
