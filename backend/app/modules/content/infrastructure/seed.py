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
        "假如你有超能力，可以让你爱的人也爱你，你要不要使用这项超能力？",
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

SEED_VERSION = 3
STANCES = [
    ("会，我希望拥有这份爱情", "不会，我希望对方自由选择"),
    ("独处更像一种自由", "独处更像一种失去"),
    ("我更看重规则", "我更看重公平"),
    ("是，关系可能随着成长改变", "不一定，我愿意主动维系"),
    ("会，我愿意保留现在的生活", "不会，我想重新选择"),
    ("是，更多选择带来更多可能", "不一定，选择也可能带来负担"),
    ("被理解更重要", "被陪伴更重要"),
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


def seed_content(factory, start, publish_current_version=False):
    with factory.begin() as s:
        for index, (slug, title, topic_title, theme) in enumerate(QUESTIONS):
            topic_id, question_id, version_id = (
                stable_id(slug + suffix) for suffix in (":topic", ":question", f":v{SEED_VERSION}")
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
            for option, label in zip(flow["steps"]["stance"]["options"][:2], STANCES[index]):
                option["label"] = label
            flow["steps"]["stance"]["options"][2]["label"] = "取决于具体情况，我还没想好"
            flow = discussion_flow(flow, index == 0, theme)
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
                    version=SEED_VERSION,
                    title=title,
                    intro=intro,
                    flow_json=flow,
                    status="published",
                    audience="adult",
                )
                .on_conflict_do_nothing()
            )
            schedule = insert(daily_schedules_table)
            schedule = schedule.values(
                local_date=start + timedelta(days=index),
                question_version_id=version_id,
                audience="adult",
                status="published",
            )
            if publish_current_version:
                schedule = schedule.on_conflict_do_update(
                    index_elements=["local_date", "audience"],
                    set_={"question_version_id": version_id, "status": "published"},
                )
            else:
                schedule = schedule.on_conflict_do_nothing()
            s.execute(schedule)


def discussion_flow(flow, love_question, theme):
    """Version 3: two deliberate choices before open discussion; old versions stay immutable."""
    flow["steps"].pop("preference")
    if love_question:
        sides = {
            "reason_yes": [
                "想争取一次双向相爱的机会",
                "感情能否持续，仍取决于彼此相处",
                "如果后来仍可离开，就不等于永久束缚",
                "比起错过，我更愿意尝试建立关系",
            ],
            "reason_no": [
                "对方应保留选择爱谁的自由",
                "我会一直怀疑这份爱的来由",
                "单方面掌控会削弱关系中的平等",
                "我珍惜双方自然靠近的过程",
            ],
        }
    else:
        sides = {
            key: [o["label"] for o in flow["steps"][key]["options"]]
            for key in ("reason_yes", "reason_no")
        }
    sides["reason_unsure"] = [
        sides["reason_yes"][0],
        sides["reason_no"][0],
        "我想先听听不同角度，再形成自己的看法",
    ]
    flow["steps"]["stance"]["options"][2]["next_step_id"] = "reason_unsure"
    for key, labels in sides.items():
        flow["steps"][key] = {
            "id": key,
            "prompt": "哪些理由更接近你的想法？可以多选，也可以自己补充。",
            "multiple": True,
            "options": [
                {"id": f"reason_{i + 1}", "label": label, "topics": [theme], "focus": label}
                for i, label in enumerate(labels)
            ]
            + [{"id": "other", "label": "其他，我想自己补充", "topics": [theme]}],
        }
        if love_question:
            flow["steps"][key]["source_url"] = (
                "https://debatetimer.cn/record/66a0f2c5a92f8e067c57d797"
            )
    return QuestionFlow.model_validate(flow).model_dump()
