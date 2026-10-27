"""Private development content importer. Not a public endpoint."""

import argparse
from datetime import datetime
from zoneinfo import ZoneInfo

from app.infrastructure.settings.config import Settings
from app.modules.catalog.infrastructure.seed import seed_catalog
from app.modules.content.infrastructure.seed import seed_content
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--publish-current-version",
        action="store_true",
        help="Explicitly publish the current seed version into the selected 7-day schedule",
    )
    parser.add_argument(
        "--start-date",
        type=lambda value: datetime.strptime(value, "%Y-%m-%d").date(),
        default=datetime.now(ZoneInfo("Asia/Shanghai")).date(),
    )
    args = parser.parse_args()
    engine = create_engine(Settings().database_url.get_secret_value(), hide_parameters=True)
    try:
        factory = sessionmaker(engine)
        seed_content(factory, args.start_date, args.publish_current_version)
        seed_catalog(factory)
        print("Imported seven daily schedules, reviewed fallback and three sourced samples")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
