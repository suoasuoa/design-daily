#!/usr/bin/env python3
"""Run the local desktop social collection and publish the refreshed site."""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from insight_common import ROOT, load_env, today


PUBLISH_PATHS = [
    "index.html",
    "data/raw/",
    "data/reports/",
    "data/products.json",
    "data/dedupe_index.json",
    "data/seen_fingerprints.json",
    "data/category_review.json",
    "data/company_multimodal_review.json",
    "data/rejected_category.json",
    "data/published.json",
    "data/trends.json",
    "data/weekly_report.json",
    "insight/",
]


def run(cmd, check=True):
    print("+", " ".join(cmd))
    return subprocess.run(cmd, cwd=ROOT, check=check)


def changed_files():
    result = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, text=True, stdout=subprocess.PIPE, check=True)
    files = []
    for line in result.stdout.splitlines():
        if not line:
            continue
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if path and Path(ROOT / path).is_file():
            files.append(path)
    return sorted(set(files))


def gh_json(method, endpoint, payload=None):
    cmd = ["gh", "api", "-X", method, endpoint]
    temp_path = None
    if payload is not None:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as f:
            json.dump(payload, f, ensure_ascii=False)
            temp_path = f.name
        cmd.extend(["--input", temp_path])
    try:
        result = subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    finally:
        if temp_path:
            Path(temp_path).unlink(missing_ok=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
    return json.loads(result.stdout or "{}")


def publish_with_github_api(repo, message, files):
    if not files:
        print("publish=skipped reason=no_changes")
        return ""
    ref = gh_json("GET", f"repos/{repo}/git/ref/heads/main")
    base_sha = ref["object"]["sha"]
    base_tree = gh_json("GET", f"repos/{repo}/git/commits/{base_sha}")["tree"]["sha"]
    tree = []
    for path in files:
        full_path = ROOT / path
        if not full_path.exists() or not full_path.is_file():
            continue
        content = full_path.read_text(encoding="utf-8")
        blob_sha = gh_json("POST", f"repos/{repo}/git/blobs", {"content": content, "encoding": "utf-8"})["sha"]
        tree.append({"path": path, "mode": "100644", "type": "blob", "sha": blob_sha})
    if not tree:
        print("publish=skipped reason=no_file_blobs")
        return ""
    new_tree = gh_json("POST", f"repos/{repo}/git/trees", {"base_tree": base_tree, "tree": tree})["sha"]
    commit = gh_json("POST", f"repos/{repo}/git/commits", {"message": message, "tree": new_tree, "parents": [base_sha]})
    gh_json("PATCH", f"repos/{repo}/git/refs/heads/main", {"sha": commit["sha"], "force": False})
    print(f"publish=github_api sha={commit['sha']} files={len(tree)}")
    return commit["sha"]


def selected_publish_file(path):
    return any(path == selected.rstrip("/") or path.startswith(selected) for selected in PUBLISH_PATHS)


def publish_api_only(repo, message):
    files = [path for path in changed_files() if selected_publish_file(path)]
    if not files:
        print("publish=skipped reason=no_changes")
        return
    commit_sha = publish_with_github_api(repo, message, files)
    if not commit_sha:
        return
    run(["git", "fetch", "origin", "main"])
    run(["git", "update-ref", "refs/heads/main", commit_sha])
    run(["git", "read-tree", commit_sha])
    print(f"publish=local_index_synced sha={commit_sha}")


def publish(repo, message):
    run(["git", "add", *PUBLISH_PATHS])
    files = changed_files()
    if not files:
        print("publish=skipped reason=no_changes")
        return
    run(["git", "config", "user.name", "design-insight-bot"])
    run(["git", "config", "user.email", "bot@design-digest.com"])
    run(["git", "commit", "-m", message])
    pushed = run(["git", "push", "origin", "main"], check=False)
    if pushed.returncode == 0:
        print("publish=git_push")
        return
    print("git_push=failed; falling back to GitHub API")
    publish_with_github_api(repo, message, files)


def main():
    load_env()
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-total", type=int, default=80)
    parser.add_argument("--min-social", type=int, default=10)
    parser.add_argument("--per-category", type=int, default=3)
    parser.add_argument("--score-limit", type=int, default=160)
    parser.add_argument("--trend-limit", type=int, default=100)
    parser.add_argument("--weekly-limit", type=int, default=100)
    parser.add_argument("--repo", default="suoasuoa/design-daily")
    parser.add_argument("--skip-publish", action="store_true")
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    py = sys.executable
    collect_cmd = [
        py,
        "scripts/collect_desktop_social.py",
        "--platform",
        "douyin",
        "--target-total",
        str(args.target_total),
        "--min-social",
        str(args.min_social),
        "--per-category",
        str(args.per_category),
    ]
    if args.headless:
        collect_cmd.append("--headless")
    run(collect_cmd)
    run([py, "scripts/dedupe.py"])
    run([py, "scripts/review_categories.py", "--batch-size", "20"])
    run([py, "scripts/enrich_images.py", "--limit", "100"])
    run([py, "scripts/score.py", "--limit", str(args.score_limit)])
    run([py, "scripts/trend_agent.py", "--limit", str(args.trend_limit)])
    run([py, "scripts/build_site.py"])
    run([py, "scripts/weekly_report.py", "--limit", str(args.weekly_limit)])
    run([py, "scripts/build_site.py"])
    if not args.skip_publish:
        publish(args.repo, f"Update desktop social pool {today()}")
    print("nightly_social_update=done")


if __name__ == "__main__":
    main()
