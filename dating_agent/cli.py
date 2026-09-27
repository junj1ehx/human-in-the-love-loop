from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import (
    CLOSE_REASONS,
    EVENT_TYPES,
    GOAL_CLARITY,
    RISKS,
    STAGES,
    Store,
    TrackerError,
    add_event,
    add_funnel_snapshot,
    aggregate_metrics,
    get_case,
    new_case,
    review_case,
    set_status,
    transition_case,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dating-agent",
        description="本地、去标识、人工推进的 QsMatch 流程跟踪器。",
    )
    parser.add_argument("--data-dir", default="private", help="私有数据目录，默认 private")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="初始化私有数据目录")

    new = sub.add_parser("new-case", help="匹配后创建代号个案")
    new.add_argument("--alias", required=True)

    sub.add_parser("list", help="列出代号、阶段和状态")

    advance = sub.add_parser("advance", help="手工改变阶段")
    advance.add_argument("--case", required=True)
    advance.add_argument("--to", required=True, choices=STAGES)
    advance.add_argument("--mutual-yes", action="store_true")
    advance.add_argument("--public-plan", action="store_true")
    advance.add_argument("--explicit-mutual", action="store_true")

    log = sub.add_parser("log", help="记录去标识事件摘要")
    log.add_argument("--case", required=True)
    log.add_argument("--type", required=True, choices=EVENT_TYPES)
    log.add_argument("--summary", required=True)
    log.add_argument("--reciprocity", type=int, choices=range(1, 6))
    log.add_argument("--comfort", type=int, choices=range(1, 6))
    log.add_argument("--boundary-respect", type=int, choices=range(1, 6))
    log.add_argument("--reliability", type=int, choices=range(1, 6))
    log.add_argument("--goal-clarity", choices=GOAL_CLARITY)
    log.add_argument("--risk", choices=RISKS, default="none")
    log.add_argument("--next-action")

    review = sub.add_parser("review", help="查看当前阶段建议")
    review.add_argument("--case", required=True)

    pause = sub.add_parser("pause", help="暂停个案")
    pause.add_argument("--case", required=True)

    resume = sub.add_parser("resume", help="恢复个案")
    resume.add_argument("--case", required=True)

    close = sub.add_parser("close", help="关闭个案")
    close.add_argument("--case", required=True)
    close.add_argument("--reason", required=True, choices=CLOSE_REASONS)

    funnel = sub.add_parser("funnel-log", help="记录按日聚合的转化漏斗")
    funnel.add_argument("--date", required=True, help="YYYY-MM-DD")
    funnel.add_argument("--profiles-reviewed", type=int, default=0)
    funnel.add_argument("--likes-sent", type=int, default=0)
    funnel.add_argument("--notes-sent", type=int, default=0)
    funnel.add_argument("--matches", type=int, default=0)
    funnel.add_argument("--first-replies", type=int, default=0)
    funnel.add_argument("--substantive-chats", type=int, default=0)
    funnel.add_argument("--invitations-sent", type=int, default=0)
    funnel.add_argument("--first-dates-completed", type=int, default=0)
    funnel.add_argument("--mutual-second-date-yes", type=int, default=0)
    funnel.add_argument("--exclusive-started", type=int, default=0)
    funnel.add_argument("--minutes-spent", type=int, default=0)

    sub.add_parser("metrics", help="查看匿名聚合计数")
    return parser


def print_json(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def run(args: argparse.Namespace) -> int:
    store = Store(Path(args.data_dir))
    if args.command == "init":
        store.initialize()
        print(f"已初始化：{store.path}")
        return 0
    if args.command == "new-case":
        case = new_case(store, args.alias)
        print(f"已创建 {case['id']}，阶段 {case['stage']}。")
        return 0
    if args.command == "list":
        data = store.load()
        rows = [
            {"id": case["id"], "stage": case["stage"], "status": case["status"]}
            for case in data["cases"].values()
        ]
        print_json(rows)
        return 0
    if args.command == "advance":
        case = transition_case(
            store,
            args.case,
            args.to,
            mutual_yes=args.mutual_yes,
            public_plan=args.public_plan,
            explicit_mutual=args.explicit_mutual,
        )
        print(f"{case['id']} 已转到 {case['stage']}。")
        return 0
    if args.command == "log":
        event = add_event(
            store,
            args.case,
            event_type=args.type,
            summary=args.summary,
            reciprocity=args.reciprocity,
            comfort=args.comfort,
            boundary_respect=args.boundary_respect,
            reliability=args.reliability,
            goal_clarity=args.goal_clarity,
            risk=args.risk,
            next_action=args.next_action,
        )
        print(f"已记录 {event['type']}，未保存原始聊天。")
        return 0
    if args.command == "review":
        case = get_case(store.load(), args.case)
        print(f"{case['id']} | {case['stage']} | {case['status']}")
        print_json(case["signals"])
        for index, item in enumerate(review_case(case), start=1):
            print(f"{index}. {item}")
        return 0
    if args.command == "pause":
        case = set_status(store, args.case, "paused")
        print(f"{case['id']} 已暂停。暂停不是欲擒故纵。")
        return 0
    if args.command == "resume":
        case = set_status(store, args.case, "active")
        print(f"{case['id']} 已恢复为 active。")
        return 0
    if args.command == "close":
        case = set_status(store, args.case, "closed", reason=args.reason)
        print(f"{case['id']} 已关闭：{case['closed_reason']}。")
        return 0
    if args.command == "funnel-log":
        snapshot = add_funnel_snapshot(
            store,
            args.date,
            profiles_reviewed=args.profiles_reviewed,
            likes_sent=args.likes_sent,
            notes_sent=args.notes_sent,
            matches=args.matches,
            first_replies=args.first_replies,
            substantive_chats=args.substantive_chats,
            invitations_sent=args.invitations_sent,
            first_dates_completed=args.first_dates_completed,
            mutual_second_date_yes=args.mutual_second_date_yes,
            exclusive_started=args.exclusive_started,
            minutes_spent=args.minutes_spent,
        )
        print(f"已记录 {snapshot['date']} 聚合漏斗，未保存个人资料。")
        return 0
    if args.command == "metrics":
        print_json(aggregate_metrics(store.load()))
        return 0
    raise TrackerError("未知命令。")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return run(args)
    except TrackerError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
