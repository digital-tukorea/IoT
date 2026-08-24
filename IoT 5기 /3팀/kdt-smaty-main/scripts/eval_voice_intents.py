#!/usr/bin/env python3
"""음성 intent 파라프레이즈 평가를 실행하고 실패율 리포트를 남긴다.

실제 OpenAI API를 호출하므로 CI에서 상시 실행하지 않는다. 필요할 때만 손으로
돌리는 opt-in 스크립트다.

    export SMART_DESK_OPENAI__API_KEY=sk-...
    python scripts/eval_voice_intents.py --limit 20
    python scripts/eval_voice_intents.py --tool set_activity_mode --report report.json

종료 코드는 ``--max-failure-rate``를 넘겼을 때만 1이다. 임계값을 주지 않으면
결과를 보고만 하고 항상 0으로 끝난다.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for entry in (REPO_ROOT, REPO_ROOT / "src"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from tests.eval.baseline import (  # noqa: E402
    BASELINE_PATH,
    BaselineError,
    build_baseline,
    compare,
    load_baseline,
    per_tool_delta,
    write_baseline,
)
from tests.eval.runner import RunnerOptions, create_client, run_cases  # noqa: E402
from tests.eval.schema import DATASET_DIR, CaseResult, ParaphraseCase, load_all  # noqa: E402


API_KEY_NAMES = ("SMART_DESK_OPENAI__API_KEY", "OPENAI_API_KEY")


def read_env_file(path: Path) -> dict[str, str]:
    """``.env``에서 ``KEY=value`` 줄만 읽는다. 앱 설정을 불러오지는 않는다."""

    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def resolve_api_key() -> str | None:
    """환경변수를 먼저 보고, 없으면 저장소 ``.env``를 본다."""

    for name in API_KEY_NAMES:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    from_file = read_env_file(REPO_ROOT / ".env")
    for name in API_KEY_NAMES:
        value = from_file.get(name, "").strip()
        if value:
            return value
    return None


def select_cases(cases: list[ParaphraseCase], args: argparse.Namespace) -> list[ParaphraseCase]:
    selected = cases
    if args.dataset:
        wanted = set(args.dataset)
        selected = [case for case in selected if case.dataset in wanted]
    if args.tool:
        wanted = set(args.tool)
        selected = [case for case in selected if case.expected_tool in wanted]
    if args.shuffle:
        selected = list(selected)
        random.Random(args.seed).shuffle(selected)
    if args.limit is not None:
        selected = selected[: args.limit]
    return selected


def summarize(results: list[CaseResult]) -> dict[str, object]:
    per_tool: dict[str, Counter[str]] = defaultdict(Counter)
    for result in results:
        bucket = per_tool[result.case.expected_tool]
        bucket["total"] += 1
        bucket["passed" if result.passed else "failed"] += 1

    total = len(results)
    failed = sum(1 for result in results if not result.passed)
    return {
        "total": total,
        "passed": total - failed,
        "failed": failed,
        "failure_rate": (failed / total) if total else 0.0,
        "reasons": dict(Counter(result.reason for result in results)),
        "per_tool": {
            tool: {
                "total": counts["total"],
                "passed": counts["passed"],
                "failed": counts["failed"],
                "failure_rate": counts["failed"] / counts["total"],
            }
            for tool, counts in sorted(per_tool.items())
        },
    }


def print_report(results: list[CaseResult], summary: dict[str, object]) -> None:
    failures = [result for result in results if not result.passed]
    if failures:
        print("\n실패한 발화")
        print("-" * 78)
        for result in failures:
            case = result.case
            print(f"  [{case.case_id}] {case.utterance}")
            print(f"      기대: {case.expected_tool}{case.expected_args_match or ''}")
            print(f"      실제: {', '.join(result.observed_tools) or '호출 없음'}")
            print(f"      사유: {result.reason} — {result.detail}")
            if result.response:
                spoken = " ".join(result.response.split())
                print(f"      응답: {spoken[:160]}{'…' if len(spoken) > 160 else ''}")

    print("\ntool별 실패율")
    print("-" * 78)
    print(f"  {'tool':26} {'전체':>5} {'통과':>5} {'실패':>5}  실패율")
    per_tool: dict[str, dict[str, float]] = summary["per_tool"]  # type: ignore[assignment]
    for tool, counts in sorted(per_tool.items(), key=lambda kv: -kv[1]["failure_rate"]):
        rate = counts["failure_rate"]
        bar = "#" * round(rate * 20)
        print(
            f"  {tool:26} {counts['total']:5.0f} {counts['passed']:5.0f} "
            f"{counts['failed']:5.0f}  {rate:6.1%} {bar}"
        )

    print("-" * 78)
    print(
        f"  전체 {summary['total']}건 중 {summary['failed']}건 실패 "
        f"(실패율 {summary['failure_rate']:.1%})"
    )
    reasons = ", ".join(f"{k}={v}" for k, v in sorted(summary["reasons"].items()))  # type: ignore[union-attr]
    print(f"  사유 분포: {reasons}")


def git_commit() -> str:
    """기준선이 어느 코드에서 측정됐는지 남긴다. 저장소가 아니어도 실패하지 않는다."""

    try:
        completed = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
    except Exception:
        return ""
    return completed.stdout.strip() if completed.returncode == 0 else ""


def print_comparison(comparison: Any, delta: dict[str, dict[str, float]]) -> None:
    """기준선 대비 무엇이 뒤집혔는지 보여준다."""

    print("\n기준선 대비 변화")
    print("-" * 78)
    if comparison.regressions:
        print(f"  회귀 {len(comparison.regressions)}건 — 기준선에서는 통과하던 발화")
        for flip in comparison.regressions:
            print(f"    ✗ {flip.utterance}")
            print(f"        {flip.expected_tool}: {flip.before} → {flip.after}")
    else:
        print("  회귀 없음")

    if comparison.fixes:
        print(f"  개선 {len(comparison.fixes)}건")
        for flip in comparison.fixes:
            print(f"    ✓ {flip.utterance}  ({flip.expected_tool}: {flip.before} → 통과)")
    if comparison.added:
        print(f"  기준선에 없는 새 발화 {len(comparison.added)}건")
        for flip in comparison.added:
            print(f"    + {flip.utterance}  ({flip.expected_tool}: {flip.after})")
    if comparison.missing:
        print(f"  기준선에만 있고 이번에 없는 발화 {len(comparison.missing)}건")
        for utterance in comparison.missing:
            print(f"    - {utterance}")
    if comparison.still_failing:
        print(f"  계속 실패 {len(comparison.still_failing)}건 (기준선에서도 실패)")

    moved = [
        (tool, counts)
        for tool, counts in delta.items()
        if counts["baseline_total"] and counts["failed"] != counts["baseline_failed"]
    ]
    if moved:
        print("\n  tool별 실패 수 변화 (기준선 → 이번)")
        for tool, counts in moved:
            arrow = "악화" if counts["failed"] > counts["baseline_failed"] else "개선"
            print(
                f"    {tool:26} {counts['baseline_failed']:.0f} → {counts['failed']:.0f}"
                f" / {counts['total']:.0f}건  ({arrow})"
            )

    print("-" * 78)
    print(
        f"  같은 발화 {comparison.compared}건 기준 실패율"
        f" {comparison.baseline_failure_rate:.1%} → {comparison.current_failure_rate:.1%}"
        f" ({comparison.rate_delta:+.1%})"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset", action="append", help="평가셋 파일 이름(확장자 제외). 반복 지정 가능")
    parser.add_argument("--tool", action="append", help="이 tool을 기대하는 발화만 실행. 반복 지정 가능")
    parser.add_argument("--limit", type=int, help="실행할 최대 발화 수")
    parser.add_argument("--shuffle", action="store_true", help="표본을 섞어서 고른다")
    parser.add_argument("--seed", type=int, default=0, help="--shuffle 시드")
    parser.add_argument("--concurrency", type=int, default=4, help="동시 실행 수 (기본 4)")
    parser.add_argument("--model", help="운영 기본 모델 대신 사용할 모델")
    parser.add_argument("--reasoning-effort", help="운영 기본값 대신 사용할 reasoning effort")
    parser.add_argument("--no-web-search", action="store_true", help="hosted web search tool을 빼고 실행")
    parser.add_argument("--timeout", type=float, default=90.0, help="발화 하나의 제한 시간(초)")
    parser.add_argument("--report", type=Path, help="JSON 리포트를 저장할 경로")
    parser.add_argument("--max-failure-rate", type=float, help="이 실패율을 넘으면 종료 코드 1")
    parser.add_argument("--list", action="store_true", help="API 호출 없이 선택된 발화만 출력")
    parser.add_argument(
        "--baseline", type=Path, default=BASELINE_PATH,
        help=f"비교할 기준선 파일 (기본 {BASELINE_PATH.name})",
    )
    parser.add_argument("--no-baseline", action="store_true", help="기준선 비교를 건너뛴다")
    parser.add_argument(
        "--update-baseline", action="store_true",
        help="이번 결과를 새 기준선으로 저장한다. 전체 실행에서만 쓴다",
    )
    parser.add_argument(
        "--fail-on-regression", action="store_true",
        help="기준선에서 통과하던 발화가 깨지면 종료 코드 1",
    )
    parser.add_argument("--baseline-note", default="", help="기준선에 남길 한 줄 메모")
    return parser


async def main_async(args: argparse.Namespace) -> int:
    cases = select_cases(load_all(DATASET_DIR), args)
    if not cases:
        print("조건에 맞는 발화가 없습니다.", file=sys.stderr)
        return 2

    if args.list:
        for case in cases:
            print(f"[{case.case_id}] {case.expected_tool:24} {case.utterance}")
        print(f"\n총 {len(cases)}건")
        return 0

    api_key = resolve_api_key()
    if not api_key:
        print(
            "OpenAI API key가 없습니다. SMART_DESK_OPENAI__API_KEY 또는 "
            "OPENAI_API_KEY를 설정하세요.",
            file=sys.stderr,
        )
        return 2

    options = RunnerOptions(
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        include_web_search=not args.no_web_search,
        timeout_seconds=args.timeout,
    )
    client = create_client(api_key)
    done = 0

    def progress(result: CaseResult) -> None:
        nonlocal done
        done += 1
        mark = "." if result.passed else "F"
        end = "\n" if done % 50 == 0 or done == len(cases) else ""
        print(f"{mark}{end}", end="", flush=True)

    print(f"{len(cases)}개 발화를 동시 실행 {args.concurrency}로 평가합니다.")
    started = datetime.now(UTC)
    try:
        results = await run_cases(
            cases, client=client, options=options, concurrency=args.concurrency, on_result=progress
        )
    finally:
        await client.close()
    elapsed = (datetime.now(UTC) - started).total_seconds()

    summary = summarize(results)
    print_report(results, summary)
    print(f"  소요 시간: {elapsed:.1f}초")

    if args.report:
        payload = {
            "generated_at": started.isoformat(),
            "elapsed_seconds": round(elapsed, 1),
            "model": options.model or "운영 기본값",
            "include_web_search": options.include_web_search,
            "summary": summary,
            "cases": [
                {
                    "case_id": result.case.case_id,
                    "utterance": result.case.utterance,
                    "expected_tool": result.case.expected_tool,
                    "expected_args_match": result.case.expected_args_match,
                    "passed": result.passed,
                    "reason": result.reason,
                    "detail": result.detail,
                    "response": result.response,
                    "observed": [
                        {"tool": call.name, "arguments": call.arguments} for call in result.calls
                    ],
                }
                for result in results
            ],
        }
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"  리포트 저장: {args.report}")

    # 조건을 걸어 일부만 돌렸으면, 기준선에만 있는 발화는 사라진 게 아니라 안 돈 것이다.
    partial = bool(args.dataset or args.tool or args.limit)
    regressed = False
    if not args.no_baseline:
        try:
            baseline = load_baseline(args.baseline)
        except BaselineError as error:
            print(f"\n기준선 비교를 건너뜁니다: {error}")
        else:
            comparison = compare(baseline, results, partial=partial)
            print_comparison(comparison, per_tool_delta(baseline, results))
            regressed = comparison.has_regression

    if args.update_baseline:
        if partial:
            print("\n일부만 실행했으므로 기준선을 갱신하지 않습니다. 전체 실행에서만 갱신하세요.")
        else:
            write_baseline(
                build_baseline(
                    results,
                    generated_at=started.isoformat(),
                    model=options.model or "운영 기본값",
                    commit=git_commit(),
                    note=args.baseline_note,
                ),
                args.baseline,
            )
            print(f"  기준선 갱신: {args.baseline}")

    rate: float = summary["failure_rate"]  # type: ignore[assignment]
    if args.max_failure_rate is not None and rate > args.max_failure_rate:
        print(f"\n실패율 {rate:.1%}가 임계값 {args.max_failure_rate:.1%}를 넘었습니다.")
        return 1
    if args.fail_on_regression and regressed:
        print("\n기준선에서 통과하던 발화가 깨졌습니다.")
        return 1
    return 0


def main() -> int:
    args = build_parser().parse_args()
    try:
        return asyncio.run(main_async(args))
    except KeyboardInterrupt:
        print("\n중단했습니다.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
