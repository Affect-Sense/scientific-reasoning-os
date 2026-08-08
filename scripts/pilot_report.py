"""Pilot funnel and activity report (Milestones 6–7 evidence generator).

Usage:
  python -m scripts.pilot_report            # console summary
  python -m scripts.pilot_report --json     # machine-readable snapshot

Reads customers, research_questions, events, agent_runs. Read-only.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone

from src.services.firestore_repository import FirestoreRepository
from src.settings import settings


def build_report() -> dict:
    repo = FirestoreRepository(settings.gcp_project_id, settings.firestore_database)
    db = repo.db

    customers = {d.id: d.to_dict() for d in db.collection("customers").stream()}
    questions = {d.id: d.to_dict() for d in db.collection("research_questions").stream()}
    runs = [d.to_dict() | {"_id": d.id} for d in db.collection("agent_runs").stream()]
    events = [d.to_dict() for d in db.collection("events").stream()]

    by_project_q: dict[str, list] = defaultdict(list)
    for qid, q in questions.items():
        by_project_q[q.get("project_id", "?")].append((qid, q))

    ev_by_project: dict[str, list] = defaultdict(list)
    for e in events:
        ev_by_project[e.get("project_id", "?")].append(e)

    total_cost = sum(r.get("estimated_cost_usd") or 0 for r in runs)
    total_tokens = sum((r.get("token_usage") or {}).get("total_tokens", 0) for r in runs)

    pilots = []
    for cus_id, c in sorted(customers.items(), key=lambda kv: str(kv[1].get("created_at", ""))):
        project_id = c.get("project_id", f"proj_{cus_id}")
        qs = by_project_q.get(project_id, [])
        evs = ev_by_project.get(project_id, [])
        etypes = [e.get("event_type") for e in evs]
        n_versions = 0
        n_validated = 0
        statuses = []
        for qid, q in qs:
            versions = list(
                db.collection("research_questions").document(qid).collection("versions").stream()
            )
            n_versions += len(versions)
            statuses.append(q.get("status"))
            if q.get("status") == "validated":
                n_validated += 1
        cus_runs = [r for r in runs if r.get("project_id") == project_id]
        pilots.append(
            {
                "customer_id": cus_id,
                "email": c.get("email", ""),
                "onboarded_at": str(c.get("created_at", "")),
                "amount_total": c.get("amount_total"),
                "funnel": {
                    "payment_confirmed": "payment_confirmed" in etypes,
                    "questions_submitted": len(qs),
                    "versions_authored": n_versions,
                    "revisions": max(0, n_versions - len(qs)),
                    "critiques_received": sum(
                        1 for t in etypes if t == "question_critique_created"
                    ),
                    "validated_questions": n_validated,
                },
                "question_statuses": statuses,
                "agent_runs": len(cus_runs),
                "cost_usd": round(sum(r.get("estimated_cost_usd") or 0 for r in cus_runs), 6),
                "last_activity": max((str(e.get("occurred_at", "")) for e in evs), default=""),
            }
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "totals": {
            "customers": len(customers),
            "research_questions": len(questions),
            "agent_runs": len(runs),
            "events": len(events),
            "total_tokens": total_tokens,
            "total_estimated_cost_usd": round(total_cost, 4),
        },
        "pilots": pilots,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = build_report()
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
        return 0

    t = report["totals"]
    print(f"\n=== SROS PILOT REPORT — {report['generated_at']} ===")
    print(
        f"Customers: {t['customers']} | RQs: {t['research_questions']} | "
        f"Agent runs: {t['agent_runs']} | Events: {t['events']} | "
        f"Cost: ${t['total_estimated_cost_usd']}"
    )
    for p in report["pilots"]:
        f = p["funnel"]
        print(f"\n— {p['customer_id']}  <{p['email']}>  onboarded {p['onboarded_at'][:16]}")
        print(
            f"   paid:{f['payment_confirmed']}  RQs:{f['questions_submitted']}  "
            f"versions:{f['versions_authored']}  revisions:{f['revisions']}  "
            f"critiques:{f['critiques_received']}  validated:{f['validated_questions']}"
        )
        print(f"   statuses:{p['question_statuses']}  runs:{p['agent_runs']}  cost:${p['cost_usd']}")
        print(f"   last activity: {p['last_activity'][:19]}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
