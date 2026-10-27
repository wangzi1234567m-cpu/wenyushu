"""Idempotent maintenance importer; never overwrites a published version."""

from datetime import timedelta
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.modules.content.domain.flow import QuestionFlow
from app.modules.content.infrastructure.models import (
    daily_schedules_table,
    question_versions_table,
    questions_table,
    topics_table,
)

QUESTIONS = [
    (
        "love-choice",
        "如果能让喜欢的人也爱上你，你会使用这种能力吗？",
        "爱情与选择",
        "relationships",
    ),
    ("solitude", "独处是一种自由，还是一种失去？", "独处与自由", "autonomy"),
    ("justice", "当规则与公平冲突时，你更看重什么？", "公平与判断", "justice"),
    ("friendship", "朋友最终走散，是成长的必然代价吗？", "关系与成长", "relationships"),
    ("own-life", "如果没有人评价你，你还会这样生活吗？", "自我与生活", "autonomy"),
    ("choice", "选择越多，我们就越自由吗？", "自由与责任", "autonomy"),
    ("understand", "被理解与被陪伴，哪个更重要？", "理解与陪伴", "relationships"),
]


def stable_id(value):
    return uuid5(NAMESPACE_URL, "wenyushu:daily:" + value)


def make_flow(theme, fallback=False):
    def preference():
        return {
            "id": "preference",
            "prompt": "你希望从怎样的阅读继续探索？",
            "optional": True,
            "options": [
                {
                    "id": "story",
                    "label": "想读一个故事",
                    "genre": "novel",
                    "style": ["故事"],
                    "topics": [theme],
                },
                {
                    "id": "ideas",
                    "label": "想看不同观点",
                    "genre": "ideas",
                    "style": ["思想讨论"],
                    "topics": ["justice"],
                },
                {"id": "skip", "label": "都可以，跳过偏好", "topics": []},
            ],
        }

    def reason(key, prompt):
        return {
            "id": key,
            "prompt": prompt,
            "optional": False,
            "options": [
                {
                    "id": "connection",
                    "label": "更关注人与人的关系",
                    "topics": ["relationships"],
                    "focus": "关系、理解与选择",
                    "next_step_id": "preference",
                },
                {
                    "id": "self",
                    "label": "更关注自己的自由与生活",
                    "topics": ["autonomy"],
                    "focus": "自我、独处与自由",
                    "next_step_id": "preference",
                },
                {
                    "id": "fairness",
                    "label": "更关注背后的原则和公平",
                    "topics": ["justice"],
                    "focus": "原则与公平",
                    "next_step_id": "preference",
                },
            ],
        }

    data = {
        "schema_version": 1,
        "first_step_id": "stance",
        "fallback": fallback,
        "steps": {
            "stance": {
                "id": "stance",
                "prompt": "你的第一反应更接近哪一种？",
                "optional": False,
                "options": [
                    {
                        "id": "yes",
                        "label": "我更认同前一种想法",
                        "next_step_id": "reason_yes",
                        "topics": [],
                    },
                    {
                        "id": "no",
                        "label": "我更认同另一种可能",
                        "next_step_id": "reason_no",
                        "topics": [],
                    },
                    {
                        "id": "unsure",
                        "label": "我还没想好，想继续看看",
                        "next_step_id": "reason_no",
                        "topics": [],
                    },
                ],
            },
            "reason_yes": reason("reason_yes", "你认同它，主要是因为更在意什么？"),
            "reason_no": reason("reason_no", "让你犹豫或想到另一种可能的，是哪一方面？"),
            "preference": preference(),
        },
    }
    return QuestionFlow.model_validate(data).model_dump()


def seed_content(factory, start):
    with factory.begin() as s:
        for index, (slug, title, topic_title, theme) in enumerate(QUESTIONS):
            topic_id, question_id, version_id = (
                stable_id(slug + suffix) for suffix in (":topic", ":question", ":v1")
            )
            s.execute(
                insert(topics_table)
                .values(
                    id=topic_id, slug=slug, title=topic_title, status="published", audience="adult"
                )
                .on_conflict_do_nothing()
            )
            s.execute(
                insert(questions_table)
                .values(id=question_id, topic_id=topic_id, slug=slug)
                .on_conflict_do_nothing()
            )
            flow = make_flow(theme, index == 0)
            intro = "这个问题没有标准答案。选一个接近当下想法的方向，也可以补充你的看法。"
            existing = (
                s.execute(
                    select(question_versions_table).where(
                        question_versions_table.c.id == version_id
                    )
                )
                .mappings()
                .first()
            )
            if existing and (
                existing["title"] != title
                or existing["intro"] != intro
                or existing["flow_json"] != flow
            ):
                raise ValueError("Published seed version differs; create a new version instead")
            s.execute(
                insert(question_versions_table)
                .values(
                    id=version_id,
                    question_id=question_id,
                    version=1,
                    title=title,
                    intro=intro,
                    flow_json=flow,
                    status="published",
                    audience="adult",
                )
                .on_conflict_do_nothing()
            )
            s.execute(
                insert(daily_schedules_table)
                .values(
                    local_date=start + timedelta(days=index),
                    question_version_id=version_id,
                    audience="adult",
                    status="published",
                )
                .on_conflict_do_nothing()
            )
