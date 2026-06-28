import argparse
import asyncio
import json
import os
from collections.abc import Sequence
from urllib.parse import urlparse

from recallops.config import Settings


async def _run_read_only_probe() -> int:
    settings = Settings(_env_file=None)
    if settings.cognee_base_url is None or settings.cognee_api_key is None:
        print("Live Cognee probe unavailable: cloud configuration is incomplete")
        return 2
    parsed_url = urlparse(settings.cognee_base_url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        print(
            "Live Cognee probe unavailable: COGNEE_BASE_URL must be an "
            "absolute HTTP(S) URL",
        )
        return 2

    from recallops.memory.cognee_cloud import CogneeCloudAdapter

    try:
        memory = CogneeCloudAdapter(
            base_url=settings.cognee_base_url,
            api_key=settings.cognee_api_key.get_secret_value(),
        )
        datasets = await memory.list_datasets()
    except Exception as error:
        print(f"Live Cognee probe failed: {type(error).__name__}")
        return 1

    print(json.dumps({"connected": True, "dataset_count": len(datasets)}))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Probe Cognee Cloud safely.")
    parser.add_argument(
        "--read-only",
        action="store_true",
        required=True,
        help="Only list datasets; never mutate Cognee state.",
    )
    parser.parse_args(argv)

    if os.getenv("RUN_COGNEE_INTEGRATION") != "1":
        print("Live Cognee probe skipped: set RUN_COGNEE_INTEGRATION=1")
        return 0
    return asyncio.run(_run_read_only_probe())


if __name__ == "__main__":
    raise SystemExit(main())
