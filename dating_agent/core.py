from __future__ import annotations

import json
import os
import re
import tempfile
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any


STAGES = (
    "matched",
    "conversing",
    "date_planned",
    "dating",
    "exclusive",
    "relationship",
)
STATUSES = ("active", "paused", "closed")
EVENT_TYPES = (
    "message_exchange",
    "invitation",
    "date_scheduled",
    "date_completed",
    "boundary",
    "red_flag",
    "check_in",
    "pause",
    "close",
)
RISKS = ("none", "uncertain", "high")
GOAL_CLARITY = ("unknown", "partial", "clear")
CLOSE_REASONS = (
    "incompatible",
    "no_reciprocity",
    "user_choice",
    "mutual_end",
    "safety",
    "relationship",
    "other",
)
FUNNEL_FIELDS = (
    "profiles_reviewed",
    "likes_sent",
    "notes_sent",
    "matches",
    "first_replies",
    "substantive_chats",
    "invitations_sent",
    "first_dates_completed",
    "mutual_second_date_yes",
    "exclusive_started",
    "minutes_spent",
)

ALIAS_RE = re.compile(r"^[A-Za-z0-9_-]{1,32}$")
SENSITIVE_PATTERNS = (
    ("疑似中国大陆手机号", re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")),
    ("疑似邮箱", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("疑似网址", re.compile(r"https?://|www\." , re.IGNORECASE)),
    ("疑似长编号", re.compile(r"(?<!\d)\d{8,}(?!\d)")),
)


class TrackerError(ValueError):
    """Raised for invalid or unsafe tracker operations."""


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def validate_alias(alias: str) -> str:
    if not ALIAS_RE.fullmatch(alias):
        raise TrackerError("代号只能含字母、数字、下划线和连字符，长度 1–32。")
    return alias


def validate_text(text: str | None, *, field: str, max_length: int) -> str | None:
    if text is None:
        return None
    value = text.strip()
    if not value:
        raise TrackerError(f"{field} 不能为空。")
    if len(value) > max_length:
        raise TrackerError(f"{field} 最多 {max_length} 个字符。")
    for label, pattern in SENSITIVE_PATTERNS:
        if pattern.search(value):
            raise TrackerError(f"{field} 含{label}；请改成去标识摘要。")
    return value


def validate_rating(value: int | None, name: str) -> int | None:
    if value is not None and value not in range(1, 6):
        raise TrackerError(f"{name} 必须是 1–5。")
    return value


def validate_nonnegative_count(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise TrackerError(f"{name} 必须是非负整数。")
    return value


def safe_rate(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 4)


@dataclass
class Store:
    data_dir: Path

    @property
    def path(self) -> Path:
        return self.data_dir / "cases.json"

    def initialize(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.save({"version": 1, "cases": {}, "funnel": []})

    def load(self) -> dict[str, Any]:
        self.initialize()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise TrackerError(f"无法读取数据文件：{exc}") from exc
        if data.get("version") != 1 or not isinstance(data.get("cases"), dict):
            raise TrackerError("数据文件格式无效。")
        if "funnel" not in data:
            data["funnel"] = []
        if not isinstance(data["funnel"], list):
            raise TrackerError("漏斗数据格式无效。")
        return data

    def save(self, data: dict[str, Any]) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        handle, temp_name = tempfile.mkstemp(
            prefix="cases-", suffix=".tmp", dir=self.data_dir
        )
        try:
            with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
                json.dump(data, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
            os.replace(temp_name, self.path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)


def new_case(store: Store, alias: str) -> dict[str, Any]:
    alias = validate_alias(alias)
    data = store.load()
    if alias in data["cases"]:
        raise TrackerError(f"代号 {alias} 已存在。")
    timestamp = now_iso()
    case = {
        "id": alias,
        "alias": alias,
        "platform": "qsmatch",
        "stage": "matched",
        "status": "active",
        "created_at": timestamp,
        "updated_at": timestamp,
        "signals": {
            "reciprocity": None,
            "comfort": None,
            "boundary_respect": None,
            "reliability": None,
            "goal_clarity": "unknown",
            "risk": "none",
        },
        "events": [],
    }
    data["cases"][alias] = case
    store.save(data)
    return case


def get_case(data: dict[str, Any], case_id: str) -> dict[str, Any]:
    validate_alias(case_id)
    try:
        return data["cases"][case_id]
    except KeyError as exc:
        raise TrackerError(f"找不到个案 {case_id}。") from exc


def add_event(
    store: Store,
    case_id: str,
    *,
    event_type: str,
    summary: str,
    reciprocity: int | None = None,
    comfort: int | None = None,
    boundary_respect: int | None = None,
    reliability: int | None = None,
    goal_clarity: str | None = None,
    risk: str = "none",
    next_action: str | None = None,
) -> dict[str, Any]:
    if event_type not in EVENT_TYPES:
        raise TrackerError(f"未知事件类型：{event_type}")
    if risk not in RISKS:
        raise TrackerError(f"未知风险级别：{risk}")
    if goal_clarity is not None and goal_clarity not in GOAL_CLARITY:
        raise TrackerError(f"未知目标清晰度：{goal_clarity}")

    summary = validate_text(summary, field="摘要", max_length=500) or ""
    next_action = validate_text(next_action, field="下一步", max_length=250)
    ratings = {
        "reciprocity": validate_rating(reciprocity, "相互性"),
        "comfort": validate_rating(comfort, "舒适度"),
        "boundary_respect": validate_rating(boundary_respect, "边界尊重"),
        "reliability": validate_rating(reliability, "可靠性"),
    }

    data = store.load()
    case = get_case(data, case_id)
    if case["status"] == "closed":
        raise TrackerError("已关闭个案不能继续记录事件。")

    event: dict[str, Any] = {
        "occurred_at": now_iso(),
        "type": event_type,
        "summary": summary,
        **ratings,
        "goal_clarity": goal_clarity,
        "risk": risk,
        "next_action": next_action,
    }
    case["events"].append(event)
    for name, value in ratings.items():
        if value is not None:
            case["signals"][name] = value
    if goal_clarity is not None:
        case["signals"]["goal_clarity"] = goal_clarity
    risk_rank = {"none": 0, "uncertain": 1, "high": 2}
    if risk_rank[risk] > risk_rank[case["signals"]["risk"]]:
        case["signals"]["risk"] = risk
    case["updated_at"] = now_iso()
    store.save(data)
    return event


def transition_case(
    store: Store,
    case_id: str,
    target: str,
    *,
    mutual_yes: bool = False,
    public_plan: bool = False,
    explicit_mutual: bool = False,
) -> dict[str, Any]:
    if target not in STAGES:
        raise TrackerError(f"未知阶段：{target}")
    data = store.load()
    case = get_case(data, case_id)
    if case["status"] == "closed":
        raise TrackerError("已关闭个案不能推进。")
    current = case["stage"]
    allowed = {
        "matched": {"conversing"},
        "conversing": {"date_planned"},
        "date_planned": {"conversing", "dating"},
        "dating": {"exclusive"},
        "exclusive": {"relationship"},
        "relationship": set(),
    }
    if target not in allowed[current]:
        raise TrackerError(f"不允许从 {current} 转到 {target}。")
    if target == "date_planned" and not (mutual_yes and public_plan):
        raise TrackerError("进入 date_planned 需要 --mutual-yes 和 --public-plan。")
    if target == "dating" and not any(
        event["type"] == "date_completed" for event in case["events"]
    ):
        raise TrackerError("进入 dating 前必须记录 date_completed 事件。")
    if target in {"exclusive", "relationship"} and not explicit_mutual:
        raise TrackerError(f"进入 {target} 需要 --explicit-mutual。")

    case["stage"] = target
    case["status"] = "active"
    case["updated_at"] = now_iso()
    store.save(data)
    return case


def set_status(
    store: Store,
    case_id: str,
    status: str,
    *,
    reason: str | None = None,
) -> dict[str, Any]:
    if status not in STATUSES:
        raise TrackerError(f"未知状态：{status}")
    if reason is not None and reason not in CLOSE_REASONS:
        raise TrackerError(f"未知关闭原因：{reason}")
    data = store.load()
    case = get_case(data, case_id)
    if case["status"] == "closed":
        raise TrackerError("已关闭个案不能恢复、暂停或重复关闭。")
    if status != "closed" and reason is not None:
        raise TrackerError("只有关闭个案时才能提供关闭原因。")
    if status == "closed" and reason is None:
        raise TrackerError("关闭个案必须提供原因。")

    case["status"] = status
    case["updated_at"] = now_iso()
    if status == "closed":
        case["closed_reason"] = reason
    store.save(data)
    return case


def review_case(case: dict[str, Any]) -> list[str]:
    if case["status"] == "closed":
        return ["个案已关闭；不建议继续接触或推进。"]

    signals = case["signals"]
    if signals["risk"] == "high":
        return ["高风险：停止推进，优先离开、保存必要证据并使用平台/警方渠道。"]

    advice: list[str] = []
    if signals["risk"] == "uncertain":
        advice.append("风险尚不确定：不要转账、投资、下载陌生 App 或转移到不可控渠道。")
    if signals["boundary_respect"] is not None and signals["boundary_respect"] <= 2:
        advice.append("边界尊重偏低：暂停推进；若已重复发生，建议结束。")

    message_events = [e for e in case["events"] if e["type"] == "message_exchange"]
    if (
        len(message_events) >= 3
        and signals["reciprocity"] is not None
        and signals["reciprocity"] <= 2
    ):
        advice.append("连续互动的相互性偏低：停止单方加力，不追发。")

    stage = case["stage"]
    if stage == "matched" and not message_events:
        advice.append("由本人写一条 2–3 行、基于具体资料点且易回复的开场。")
    elif stage == "conversing":
        if len(message_events) < 2:
            advice.append("继续轻量双向了解，不急着深入或邀约。")
        elif (signals["reciprocity"] or 0) >= 3 and (signals["comfort"] or 0) >= 3:
            advice.append("已有一定相互性：若共同话题自然出现，可由本人提出公开、短时、低压力邀约。")
        else:
            advice.append("证据不足：观察真实扩展和主动性，不按固定轮次推进。")
    elif stage == "date_planned":
        advice.append("前一天确认；公开场所、各自交通、可信联系人知情，允许随时结束。")
    elif stage == "dating":
        advice.append("增加场景样本，逐步澄清城市、婚育、事业、家庭和边界；不要自动推断排他。")
    elif stage == "exclusive":
        advice.append("明确排他的具体定义、App 处理、性健康和退出沟通，不靠猜测。")
    elif stage == "relationship":
        advice.append("停止候选漏斗；未经伴侣同意，不建立秘密分析档案。")

    if not advice:
        advice.append("没有足够结构化证据；先记录自己的感受与可观察行为。")
    return advice


def add_funnel_snapshot(
    store: Store,
    period: str,
    **counts: int,
) -> dict[str, Any]:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", period):
        raise TrackerError("日期必须是 YYYY-MM-DD。")
    try:
        date.fromisoformat(period)
    except ValueError as exc:
        raise TrackerError("日期必须是 YYYY-MM-DD。") from exc

    unknown = set(counts) - set(FUNNEL_FIELDS)
    if unknown:
        raise TrackerError(f"未知漏斗字段：{', '.join(sorted(unknown))}")
    values = {
        field: validate_nonnegative_count(counts.get(field, 0), field)
        for field in FUNNEL_FIELDS
    }
    if not any(values.values()):
        raise TrackerError("漏斗快照至少需要一个非零计数。")

    data = store.load()
    if any(item.get("date") == period for item in data["funnel"]):
        raise TrackerError(f"{period} 的漏斗快照已存在。")
    snapshot = {"date": period, **values}
    data["funnel"].append(snapshot)
    data["funnel"].sort(key=lambda item: item["date"])
    store.save(data)
    return snapshot


def funnel_metrics(data: dict[str, Any]) -> dict[str, Any]:
    totals = {
        field: sum(item.get(field, 0) for item in data.get("funnel", []))
        for field in FUNNEL_FIELDS
    }
    outbound = totals["likes_sent"] + totals["notes_sent"]
    hours = totals["minutes_spent"] / 60
    rates = {
        "outreach_rate": safe_rate(outbound, totals["profiles_reviewed"]),
        "match_rate": safe_rate(totals["matches"], outbound),
        "first_reply_rate": safe_rate(totals["first_replies"], totals["matches"]),
        "substantive_chat_rate": safe_rate(
            totals["substantive_chats"], totals["first_replies"]
        ),
        "invitation_rate": safe_rate(
            totals["invitations_sent"], totals["substantive_chats"]
        ),
        "first_date_rate": safe_rate(
            totals["first_dates_completed"], totals["invitations_sent"]
        ),
        "mutual_second_date_rate": safe_rate(
            totals["mutual_second_date_yes"], totals["first_dates_completed"]
        ),
        "exclusive_rate": safe_rate(
            totals["exclusive_started"], totals["mutual_second_date_yes"]
        ),
        "mutual_second_dates_per_10_hours": (
            round(totals["mutual_second_date_yes"] / hours * 10, 4)
            if hours
            else None
        ),
    }
    return {
        "snapshot_count": len(data.get("funnel", [])),
        "totals": totals,
        "rates": rates,
    }


def aggregate_metrics(data: dict[str, Any]) -> dict[str, Any]:
    cases = list(data["cases"].values())
    stage_counts = Counter(case["stage"] for case in cases)
    status_counts = Counter(case["status"] for case in cases)
    event_counts = Counter(
        event["type"] for case in cases for event in case.get("events", [])
    )
    return {
        "case_count": len(cases),
        "stages": {stage: stage_counts.get(stage, 0) for stage in STAGES},
        "statuses": {status: status_counts.get(status, 0) for status in STATUSES},
        "events": {kind: event_counts.get(kind, 0) for kind in EVENT_TYPES},
        "funnel": funnel_metrics(data),
    }
