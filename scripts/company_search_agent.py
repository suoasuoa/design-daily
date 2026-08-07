#!/usr/bin/env python3
"""Run an independent company-GPT discovery and multimodal screening lane."""

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

from company_gpt import CompanyGPTClient
from company_multimodal_review import review_one
from deepseek_search_agent import (
    accepted_today,
    balanced_limit,
    enrich_pages,
    execute_searches,
    lead_from_candidate,
    merge_leads,
    plan_queries,
    seen_urls,
)
from insight_common import (
    DATA_DIR,
    RAW_DIR,
    canonical_url,
    ensure_dirs,
    load_env,
    load_json,
    now_iso,
    stable_hash,
    strip_html,
    today,
    write_json,
)


def provisional_product(row):
    title = strip_html(row.get("page_title") or row.get("title") or "").strip()
    summary = strip_html(row.get("description") or row.get("snippet") or "").strip()
    return {
        "id": stable_hash(f"company-candidate|{row.get('url')}|{title}"),
        "title": title[:180],
        "category": row.get("category_hint") or "",
        "summary": summary[:700],
        "tags": [
            row.get("category_hint") or "",
            row.get("source_group") or "curated_keyword",
            row.get("intent") or "adapt",
        ],
        "price_gate": "unknown",
        "source_primary": row.get("source") or "Company GPT Curated Search",
        "url": row.get("url") or "",
        "image": row.get("image") or "",
    }


def screen_one(row, client):
    product = provisional_product(row)
    decision = review_one(product, client)
    candidate = dict(row)
    candidate["agent_decision"] = {
        "category": decision.get("category") or decision.get("suggested_category") or "",
        "reason": decision.get("reason") or "",
        "keep": bool(decision.get("keep")),
        "model_keep": bool(decision.get("keep")),
        "confidence": int(decision.get("confidence") or 0),
        "relevance": int(decision.get("relevance") or 0),
        "innovation": int(decision.get("innovation") or 0),
        "utility": int(decision.get("utility") or 0),
        "clarity": int(decision.get("clarity") or 0),
        "quality_score": int(decision.get("quality_score") or 0),
        "image_status": decision.get("image_status") or "unreadable",
        "title_image_match": int(decision.get("title_image_match") or 0),
        "source": "company_gpt_multimodal",
    }
    return candidate


def screen_candidates(rows, workers=4):
    reviewed = []
    client = CompanyGPTClient(timeout=150)
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = [executor.submit(screen_one, row, client) for row in rows]
        for future in as_completed(futures):
            try:
                reviewed.append(future.result())
            except Exception as exc:
                print(f"company_search_screen_retry_later error={str(exc)[:220]}", flush=True)
            kept = sum(bool(row.get("agent_decision", {}).get("keep")) for row in reviewed)
            print(f"company_search_screen reviewed={len(reviewed)} kept={kept}", flush=True)
    return reviewed


def company_lead(row, round_index):
    lead = lead_from_candidate(row, round_index)
    lead["id"] = stable_hash(f"company-agent|{row.get('url')}|{lead.get('title')}")
    lead["source"] = lead.get("source") or "Company GPT Curated Search"
    lead["creator"] = "Company GPT Search Agent"
    lead["tags"] = [
        tag for tag in lead.get("tags", []) if tag != "deepseek_search_agent"
    ] + ["company_search_agent", "company_gpt_discovery"]
    lead["quality_tier"] = "company_gpt_verified"
    lead["agent_pre_review"]["source"] = "company_gpt_multimodal"
    return lead


def write_report(stats):
    path = DATA_DIR / "reports" / f"company-search-agent-{today()}.json"
    report = load_json(path, {"date": today(), "rounds": []})
    report.setdefault("rounds", []).append(stats)
    report["generated_at"] = now_iso()
    report["total_kept"] = sum(int(row.get("kept") or 0) for row in report["rounds"])
    write_json(path, report)


def run_agent(args):
    current_count, current_categories = accepted_today()
    jobs = plan_queries(args.query_count, args.target, args.round, planner="company")
    print(f"company_agent_plan queries={len(jobs)} current={current_count}/{args.target}", flush=True)
    results = execute_searches(jobs, args.per_query, args.search_workers)
    known = seen_urls()
    fresh = [row for row in results if canonical_url(row.get("url") or "") not in known]
    fresh = balanced_limit(fresh, args.max_pages)
    print(f"company_agent_search results={len(results)} fresh={len(fresh)}", flush=True)
    enriched = enrich_pages(fresh, args.page_workers)
    reviewed = screen_candidates(enriched, args.screen_workers)
    approved = [row for row in reviewed if row.get("agent_decision", {}).get("keep")]
    leads = [company_lead(row, args.round) for row in approved]
    leads = [lead for lead in leads if lead.get("url") and lead.get("title")]
    path = RAW_DIR / f"company-agent-{today()}.json"
    merged, existing, added = merge_leads(path, leads)
    write_json(path, merged)
    by_category = Counter(lead.get("category") for lead in leads)
    stats = {
        "round": args.round + 1,
        "generated_at": now_iso(),
        "accepted_before": current_count,
        "accepted_by_category_before": dict(current_categories),
        "queries": len(jobs),
        "search_results": len(results),
        "fresh_direct_urls": len(fresh),
        "screened": len(reviewed),
        "kept": len(approved),
        "added": added,
        "by_category": dict(by_category.most_common()),
    }
    write_report(stats)
    print(
        f"company_agent saved={path} existing={existing} screened={len(reviewed)} "
        f"kept={len(approved)} added={added} categories={dict(by_category)}",
        flush=True,
    )
    return stats


def main():
    load_env()
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=int, default=40)
    parser.add_argument("--round", type=int, default=0)
    parser.add_argument("--query-count", type=int, default=60)
    parser.add_argument("--per-query", type=int, default=10)
    parser.add_argument("--max-pages", type=int, default=240)
    parser.add_argument("--search-workers", type=int, default=10)
    parser.add_argument("--page-workers", type=int, default=12)
    parser.add_argument("--screen-workers", type=int, default=4)
    args = parser.parse_args()
    ensure_dirs()
    run_agent(args)


if __name__ == "__main__":
    main()
