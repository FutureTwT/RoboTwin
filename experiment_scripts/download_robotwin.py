#!/usr/bin/env python3

import argparse
from pathlib import Path

# 使用最新版 huggingface_hub，避免 Xet 下载兼容性问题
from huggingface_hub import HfApi, hf_hub_download


REPO_ID = "TianxingChen/RoboTwin2.0"
REVISION = "main"
# Supported filenames: aloha-agilex_clean_50.zip, aloha-agilex_randomized_500.zip, arx-x5_clean_50.zip, arx-x5_randomized_500.zip, franka_clean_50.zip, franka_randomized_500.zip, piper_clean_50.zip, piper_randomized_500.zip, ur5_clean_50.zip, ur5_randomized_500.zip
TARGET_FILENAME = "aloha-agilex_clean_50.zip"
SUPPORTED_FILENAMES = (
    "aloha-agilex_clean_50.zip",
    "aloha-agilex_randomized_500.zip",
    "arx-x5_clean_50.zip",
    "arx-x5_randomized_500.zip",
    "franka_clean_50.zip",
    "franka_randomized_500.zip",
    "piper_clean_50.zip",
    "piper_randomized_500.zip",
    "ur5_clean_50.zip",
    "ur5_randomized_500.zip",
)
EXPECTED_TASK_COUNT = 50
DEFAULT_OUTPUT_DIR = Path("/data1/tanwentao/datasets/RoboTwin2.0")


def find_target_files(target_filename):
    repo_items = HfApi().list_repo_tree(
        repo_id=REPO_ID,
        path_in_repo="dataset",
        recursive=True,
        repo_type="dataset",
        revision=REVISION,
    )
    repo_paths = (item.path for item in repo_items if hasattr(item, "path"))
    target_files = sorted(
        path
        for path in repo_paths
        if path.startswith("dataset/")
        and path.count("/") == 2
        and path.endswith(f"/{target_filename}")
    )
    if len(target_files) != EXPECTED_TASK_COUNT:
        raise RuntimeError(
            f"Expected {EXPECTED_TASK_COUNT} task archives named "
            f"{target_filename!r}, found {len(target_files)}."
        )
    return target_files


def main():
    parser = argparse.ArgumentParser(
        description="Download RoboTwin 2.0 per-task dataset archives."
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--filename",
        choices=SUPPORTED_FILENAMES,
        default=TARGET_FILENAME,
        help=f"Archive filename to download (default: {TARGET_FILENAME}).",
    )
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="List the matched task archives without downloading them.",
    )
    args = parser.parse_args()

    target_files = find_target_files(args.filename)
    print(f"Found {len(target_files)} task archives named {args.filename!r}:")
    for path in target_files:
        print(f"  {path}")

    if args.list_only:
        return

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for index, filename in enumerate(target_files, start=1):
        print(f"[{index:02d}/{len(target_files)}] Downloading {filename}")
        hf_hub_download(
            repo_id=REPO_ID,
            filename=filename,
            repo_type="dataset",
            revision=REVISION,
            local_dir=args.output_dir,
        )

    print(f"Download complete: {args.output_dir / 'dataset'}")


if __name__ == "__main__":
    main()
