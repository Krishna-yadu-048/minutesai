"""The shape of the minutes, and how to show them as markdown."""

from pydantic import BaseModel


class ActionItem(BaseModel):
    task: str
    owner: str | None = None  # None when nobody is named
    due: str | None = None


class Minutes(BaseModel):
    title: str
    date: str | None = None
    attendees: list[str] = []
    summary: str
    discussion_points: list[str] = []
    decisions: list[str] = []
    action_items: list[ActionItem] = []


def bullets(items: list[str]) -> str:
    if not items:
        return "_None recorded._"
    return "\n".join(f"- {item}" for item in items)


def to_markdown(minutes: Minutes) -> str:
    parts = [f"# {minutes.title}"]
    if minutes.date:
        parts.append(f"**Date:** {minutes.date}")
    if minutes.attendees:
        parts.append(f"**Attendees:** {', '.join(minutes.attendees)}")

    actions = []
    for item in minutes.action_items:
        line = f"{item.task} (owner: {item.owner or 'unassigned'}"
        line += f", due: {item.due})" if item.due else ")"
        actions.append(line)

    parts += [
        "## Summary",
        minutes.summary,
        "## Discussion points",
        bullets(minutes.discussion_points),
        "## Decisions",
        bullets(minutes.decisions),
        "## Action items",
        bullets(actions),
    ]
    return "\n\n".join(parts)
