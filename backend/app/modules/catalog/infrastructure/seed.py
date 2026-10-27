"""Reviewed P1 samples. Sources checked 2026-10-27; no external calls at runtime."""

from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy.dialects.postgresql import insert

from app.modules.catalog.infrastructure.models import evidence_table, works_table

SAMPLES = [
    (
        "autonomy",
        "瓦尔登湖",
        "亨利·戴维·梭罗",
        "Walden",
        "https://www.gutenberg.org/ebooks/205",
        "围绕独处、自然与生活方式展开的散文作品。",
    ),
    (
        "relationships",
        "简·爱",
        "夏洛蒂·勃朗特",
        "Jane Eyre",
        "https://www.gutenberg.org/ebooks/1260",
        "以年轻女性的成长与爱情为线索的小说。",
    ),
    (
        "justice",
        "理想国",
        "柏拉图",
        "The Republic",
        "https://www.gutenberg.org/ebooks/1497",
        "围绕正义和城邦生活展开讨论的哲学作品。",
    ),
]


def seed_catalog(factory):
    checked = datetime(2026, 10, 27, tzinfo=UTC)
    with factory.begin() as s:
        for theme, title, author, original, url, summary in SAMPLES:
            key = "p1-demo:" + theme
            work = uuid5(NAMESPACE_URL, "wenyushu:" + key)
            s.execute(
                insert(works_table)
                .values(
                    id=work,
                    canonical_title=title,
                    author=author,
                    original_title=original,
                    normalized_key=key,
                )
                .on_conflict_do_nothing()
            )
            s.execute(
                insert(evidence_table)
                .values(
                    id=uuid5(work, "bibliography"),
                    work_id=work,
                    source_type="library",
                    source_url=url,
                    claim_type="bibliography",
                    evidence_summary=summary,
                    verification_status="verified",
                    checked_at=checked,
                    expires_at=checked + timedelta(days=180),
                )
                .on_conflict_do_nothing()
            )
