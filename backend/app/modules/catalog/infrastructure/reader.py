from datetime import UTC, datetime

from sqlalchemy import select

from app.modules.catalog.infrastructure.models import evidence_table as evidence
from app.modules.catalog.infrastructure.models import works_table as works


class SqlBookCatalog:
    def __init__(self, factory):
        self.factory = factory

    def verified_samples(self, themes, limit):
        with self.factory() as s:
            rows = s.execute(
                select(works, evidence.c.source_url, evidence.c.evidence_summary)
                .join(evidence, works.c.id == evidence.c.work_id)
                .where(
                    evidence.c.verification_status == "verified",
                    evidence.c.claim_type == "bibliography",
                    evidence.c.expires_at > datetime.now(UTC),
                    evidence.c.checked_at.is_not(None),
                    works.c.normalized_key.like("p1-demo:%"),
                )
                .order_by(works.c.normalized_key)
            ).mappings()
            candidates = []
            for row in rows:
                theme = row["normalized_key"].split(":")[-1]
                candidates.append(
                    (
                        0 if theme in themes else 1,
                        str(row["id"]),
                        {
                            "work_id": row["id"],
                            "title": row["canonical_title"],
                            "author": row["author"],
                            "summary": row["evidence_summary"],
                            "verification_status": "verified",
                            "evidence_urls": [row["source_url"]],
                        },
                    )
                )
            seen, result = set(), []
            for score, _, item in sorted(candidates, key=lambda x: (x[0], x[1])):
                if score == 0 and item["work_id"] not in seen:
                    result.append(item)
                    seen.add(item["work_id"])
            return result[:limit]
