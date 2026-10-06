"""Profile the accepted CLI on Snap; retain function timing/count metadata only."""

import contextlib
import cProfile
import io
import json
import pstats
import time

from agent_observer.cli import main as cli_main


def main():
    results = []
    for provider in ("codex", "claude"):
        profile = cProfile.Profile()
        sink = io.StringIO()
        started = time.perf_counter()
        with contextlib.redirect_stdout(sink):
            code = profile.runcall(cli_main, ["snapshot", "--host-scope", "snap", "--provider", provider])
        if code != 0:
            raise SystemExit("accepted CLI profile failed")
        snapshot = json.loads(sink.getvalue())
        sink.close()
        stats = pstats.Stats(profile)
        top = []
        for (filename, line, function), (_primitive, total, selftime, cumulative, _callers) in sorted(
            stats.stats.items(), key=lambda pair: pair[1][3], reverse=True,
        )[:24]:
            top.append({
                "module": filename.rsplit("/", 1)[-1], "line": line, "function": function,
                "calls": total, "selfSeconds": round(selftime, 4),
                "cumulativeSeconds": round(cumulative, 4),
            })
        results.append({
            "provider": provider, "elapsedSeconds": round(time.perf_counter() - started, 4),
            "rows": len(snapshot["sessions"]),
            "profile": "existing CLI main under cProfile; not future service benchmark",
            "topFunctions": top,
        })
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
