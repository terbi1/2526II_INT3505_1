"""
Pagination benchmark — runs against your local Flask app.

Usage:
    python benchmark.py
    python benchmark.py --depths 1,10,50,200
    python benchmark.py --reps 10 --limit 20
    python benchmark.py --output results.csv
    python benchmark.py --base-url http://localhost:5000
"""

import argparse
import csv
import time
import statistics
from datetime import datetime

try:
    import requests
except ImportError:
    print("Missing dependency: pip install requests")
    raise SystemExit(1)

COLORS = {
    "header":     "\033[1;37m",
    "page-based": "\033[94m",
    "offset":     "\033[93m",
    "cursor":     "\033[92m",
    "ok":         "\033[32m",
    "warn":       "\033[33m",
    "error":      "\033[31m",
    "reset":      "\033[0m",
    "dim":        "\033[2m",
}

def c(color, text):
    return f"{COLORS.get(color, '')}{text}{COLORS['reset']}"

def make_strategies(base_url):
    return {
        "page-based": lambda d, l: f"{base_url}/api/v1/books?page={d}&limit={l}",
        "offset":     lambda d, l: f"{base_url}/api/v2/books?offset={(d - 1) * l}&limit={l}",
        "cursor":     lambda d, l: f"{base_url}/api/v3/books?cursor={(d - 1) * l}&limit={l}",
    }

def send_request(url):
    try:
        t0 = time.perf_counter()
        resp = requests.get(url, timeout=10)
        ms = (time.perf_counter() - t0) * 1000
        records = 0
        try:
            data = resp.json().get("data", [])
            records = len(data) if isinstance(data, list) else 0
        except Exception:
            pass
        return round(ms, 2), resp.status_code, records
    except requests.exceptions.ConnectionError:
        return None, "CONN_ERR", 0
    except requests.exceptions.Timeout:
        return None, "TIMEOUT", 0

def benchmark(strategies, depths, reps, limit):
    results = []

    print(f"\n{c('header', 'Pagination benchmark')}")
    print(c("dim", f"depths={depths}  reps={reps}  limit={limit}\n"))

    header = f"{'Strategy':<14} {'Depth':>6} {'Avg ms':>8} {'P95 ms':>8} {'Min ms':>8} {'Max ms':>8} {'StdDev':>8} {'Errors':>7}"
    print(c("header", header))
    print(c("dim", "-" * len(header)))

    for strategy, url_fn in strategies.items():
        for depth in depths:
            url = url_fn(depth, limit)
            latencies = []
            errors = 0

            for rep in range(reps):
                progress = f"  {strategy} depth={depth} rep {rep + 1}/{reps}..."
                print(f"\r{c('dim', progress)}", end="", flush=True)
                ms, status, records = send_request(url)
                status_str = str(status)
                if ms is None or status_str.startswith("4") or status_str.startswith("5"):
                    errors += 1
                else:
                    latencies.append(ms)
                time.sleep(0.05)

            print("\r" + " " * 60 + "\r", end="")

            if not latencies:
                avg = p95 = mn = mx = sd = None
            else:
                avg = round(statistics.mean(latencies), 1)
                p95 = round(sorted(latencies)[int(len(latencies) * 0.95) - 1], 1)
                mn  = round(min(latencies), 1)
                mx  = round(max(latencies), 1)
                sd  = round(statistics.stdev(latencies) if len(latencies) > 1 else 0.0, 1)

            results.append({
                "strategy":   strategy,
                "depth":      depth,
                "limit":      limit,
                "reps":       reps,
                "avg_ms":     avg,
                "p95_ms":     p95,
                "min_ms":     mn,
                "max_ms":     mx,
                "stddev_ms":  sd,
                "errors":     errors,
                "url_sample": url,
                "timestamp":  datetime.now().isoformat(),
            })

            def fmt(v):
                return f"{v:>8.1f}" if v is not None else f"{'N/A':>8}"

            err_display = c("error", f"{errors:>7}") if errors > 0 else f"{errors:>7}"
            row_color = "warn" if errors > 0 else strategy
            name_col = f"{strategy:<14}"
            line = f"{c(row_color, name_col)} {depth:>6} {fmt(avg)} {fmt(p95)} {fmt(mn)} {fmt(mx)} {fmt(sd)} {err_display}"
            print(line)

        print()

    return results

def save_csv(results, path):
    fields = ["strategy", "depth", "limit", "reps", "avg_ms", "p95_ms",
              "min_ms", "max_ms", "stddev_ms", "errors", "url_sample", "timestamp"]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)
    print(c("ok", f"\nResults saved to: {path}"))

def print_summary(results):
    print(c("header", "\nSummary — avg latency by strategy (across all depths)"))
    print(c("dim", "-" * 40))

    by_strategy = {}
    for r in results:
        if r["avg_ms"] is not None:
            by_strategy.setdefault(r["strategy"], []).append(r["avg_ms"])

    for strategy, vals in by_strategy.items():
        overall = round(statistics.mean(vals), 1)
        label = f"{strategy:<14}"
        print(f"  {c(strategy, label)}  {overall} ms overall avg")

    print(c("header", "\nLatency at deepest depth tested"))
    print(c("dim", "-" * 40))

    max_depth = max(r["depth"] for r in results)
    deep = [r for r in results if r["depth"] == max_depth and r["avg_ms"] is not None]
    deep.sort(key=lambda r: r["avg_ms"])

    for r in deep:
        label = f"{r['strategy']:<14}"
        print(f"  {c(r['strategy'], label)}  {r['avg_ms']} ms  (depth {max_depth})")

def check_server(base_url):
    try:
        requests.get(f"{base_url}/api/v1/books?page=1&limit=1", timeout=3)
        return True
    except Exception:
        return False

def main():
    parser = argparse.ArgumentParser(description="Benchmark Flask pagination strategies")
    parser.add_argument("--depths",   default="1,5,10,25,50,100", help="Comma-separated page depths")
    parser.add_argument("--reps",     default=5, type=int,         help="Requests per depth")
    parser.add_argument("--limit",    default=20, type=int,        help="Items per page")
    parser.add_argument("--output",   default="pagination_results.csv", help="Output CSV file")
    parser.add_argument("--base-url", default="http://localhost:5000",  help="Flask server base URL")
    args = parser.parse_args()

    base_url   = args.base_url.rstrip("/")
    depths     = [int(x.strip()) for x in args.depths.split(",") if x.strip()]
    strategies = make_strategies(base_url)

    print(c("dim", f"Checking server at {base_url}..."), end=" ", flush=True)
    if not check_server(base_url):
        print(c("error", "unreachable"))
        print(c("error", f"\nCould not connect to {base_url}"))
        print("Make sure your Flask app is running:  python app.py")
        raise SystemExit(1)
    print(c("ok", "ok"))

    results = benchmark(strategies, depths, args.reps, args.limit)
    print_summary(results)
    save_csv(results, args.output)

if __name__ == "__main__":
    main()