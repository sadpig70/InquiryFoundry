"""ifa CLI — prediction rounds over adopted IF questions.

    python ifa.py select     [--n 6] --run RUN-ID
    python ifa.py run        --run RUN-ID --lwars LWAR1,LWAR2,LWAR4
    python ifa.py review-run --run RUN-ID --lwar-id LWAR3 --by "Claude Fable 5"
    python ifa.py ratify     --run RUN-ID --reviewer NAME [--delegated]
    python ifa.py close      --run RUN-ID
    python ifa.py report     --run RUN-ID
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ifa_core import cycle  # noqa: E402
from ifa_core.bus import publish_collect  # noqa: E402
from ifa_core.store import IfaStore, atomic_write_yaml, load_yaml  # noqa: E402


def _emit(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("select", "run", "review-run", "ratify", "close", "report", "vendors"):
        p = sub.add_parser(name)
        p.add_argument("--run", required=True)
        p.add_argument("--ifa-root", default=".ifa")
        p.add_argument("--if-root", default=".if")
        if name == "select":
            p.add_argument("--n", type=int, default=6)
            p.add_argument("--mode", default="fresh",
                           choices=("fresh", "second-opinion"))
        if name == "run":
            p.add_argument("--lwars", required=True)
        if name == "review-run":
            p.add_argument("--lwar-id", required=True)
            p.add_argument("--by", required=True)
        if name == "ratify":
            p.add_argument("--reviewer", required=True)
            p.add_argument("--delegated", action="store_true")
    args = ap.parse_args()
    store = IfaStore(args.ifa_root, args.if_root)

    if args.cmd == "select":
        batch = cycle.select_batch(store, args.n, getattr(args, "mode", "fresh"))
        run_dir = store.run_dir(args.run)
        atomic_write_yaml(run_dir / "batch.yaml", batch)
        _emit({"selected": [q["question_id"] for q in batch],
               "criteria": "quantitative reject_if, domains interleaved"})
    elif args.cmd == "run":
        lwars = [x.strip() for x in args.lwars.split(",") if x.strip()]
        _emit(cycle.run_predict_round(store, args.run, lwars))
    elif args.cmd == "review-run":
        packet = cycle.review_packet(store, args.run)
        run_dir = store.run_dir(args.run)
        outboxes, statuses = publish_collect(
            run_dir, "review", [(args.lwar_id, packet)])
        doc = outboxes.get(args.lwar_id)
        if not doc:
            _emit({"status": "review_failed", "statuses": statuses})
            return 1
        _emit({"status": "recommended", "statuses": statuses,
               "decisions": len(cycle.fold_review(store, args.run, doc, args.by)["decisions"])})
    elif args.cmd == "ratify":
        _emit(cycle.ratify(store, args.run, args.reviewer, args.delegated))
    elif args.cmd == "close":
        _emit(cycle.close_run(store, args.run))
    elif args.cmd == "vendors":
        _emit(cycle.vendor_scores(store))
    elif args.cmd == "report":
        rows = cycle.priorities(store, None if args.run == "ALL" else args.run)
        lines = ["# 실험 우선순위 — 등록된 예측의 벤더 간 불일치", "",
                 "| question_id | 등록 예측 | 방향 | 불일치 |", "|---|---|---|---|"]
        for r in rows:
            lines.append("| %s | %d | %s | **%s** |" % (
                r["question_id"], r["n_registered"],
                " / ".join(r["directions"]), r["disagreement"]))
        lines.append("")
        lines.append("split 이 위에 온다 — 잘 근거된 모델들이 갈리는 질문이 실험의 정보 이득이 가장 크다.")
        out = store.reports_dir() / f"priorities-{args.run}.md"
        out.write_text("\n".join(lines), encoding="utf-8")
        _emit({"report": str(out), "rows": rows})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
