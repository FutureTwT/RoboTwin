#!/usr/bin/env python3

"""Validate a 640x480 RoboTwin replay dataset against the original Clean50 data."""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
import time
from typing import Any, Iterable

import cv2
import h5py
import numpy as np
from tqdm import tqdm


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_ROOT = Path("/data1/common_data/RoboTwin2.0/dataset")
DEFAULT_REPLAY_ROOT = Path(
    "/data1/sunyang/datasets/RoboTwin2.0_640_480/dataset"
)
DEFAULT_SETTING = "aloha-agilex_clean_50"
DEFAULT_REPORT = REPO_ROOT / "doc/study-notes/data_review_replay.md"
EXPECTED_TASKS = 50
EXPECTED_EPISODES = 50
CAMERAS = ("front_camera", "head_camera", "left_camera", "right_camera")
TABLE_CAMERAS = ("table_left_camera", "table_right_camera")
CAMERA_FIELDS = ("rgb", "intrinsic_cv", "extrinsic_cv", "cam2world_gl")
INTRINSIC_SCALE = np.diag([2.0, 2.0, 1.0]).astype(np.float32)


@dataclass
class Failure:
    category: str
    location: str
    message: str


@dataclass
class AuditMetrics:
    counts: Counter[str] = field(default_factory=Counter)
    failures: list[Failure] = field(default_factory=list)
    max_image_mae: float = 0.0
    max_video_mae: float = 0.0

    def fail(self, category: str, location: str, message: str) -> None:
        self.counts[f"failed_{category}"] += 1
        self.failures.append(Failure(category, location, message))

    def merge_camera(self, result: "CameraResult") -> None:
        self.counts.update(result.counts)
        self.failures.extend(result.failures)
        for failure in result.failures:
            self.counts[f"failed_{failure.category}"] += 1
        self.max_image_mae = max(self.max_image_mae, result.max_image_mae)
        self.max_video_mae = max(self.max_video_mae, result.max_video_mae)


@dataclass
class CameraResult:
    counts: Counter[str] = field(default_factory=Counter)
    failures: list[Failure] = field(default_factory=list)
    max_image_mae: float = 0.0
    max_video_mae: float = 0.0

    def fail(self, category: str, location: str, message: str) -> None:
        self.failures.append(Failure(category, location, message))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate RoboTwin 640x480 replay data against the original "
            "Clean50 dataset."
        )
    )
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--replay-root", type=Path, default=DEFAULT_REPLAY_ROOT)
    parser.add_argument("--setting", default=DEFAULT_SETTING)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--expected-tasks", type=int, default=EXPECTED_TASKS)
    parser.add_argument("--expected-episodes", type=int, default=EXPECTED_EPISODES)
    parser.add_argument(
        "--task",
        action="append",
        dest="tasks",
        help="Validate only this task; repeat the option to select multiple tasks.",
    )
    parser.add_argument(
        "--episode",
        action="append",
        dest="episodes",
        type=int,
        help="Validate only this episode index; repeat to select multiple episodes.",
    )
    parser.add_argument("--image-mae-threshold", type=float, default=5.0)
    parser.add_argument("--video-mae-threshold", type=float, default=5.0)
    parser.add_argument("--max-failures", type=int, default=20)
    return parser.parse_args()


def sha256_file(path: Path, chunk_size: int = 4 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def task_names(root: Path, setting: str) -> set[str]:
    if not root.is_dir():
        return set()
    return {
        path.parent.name
        for path in root.glob(f"*/{setting}")
        if path.is_dir()
    }


def episode_names(prefix: str, suffix: str, count: int) -> set[str]:
    return {f"{prefix}{index}{suffix}" for index in range(count)}


def dataset_paths(handle: h5py.File) -> set[str]:
    paths: set[str] = set()

    def visit(name: str, value: Any) -> None:
        if isinstance(value, h5py.Dataset):
            paths.add(name)

    handle.visititems(visit)
    return paths


def check_file_sets(
    task_root: Path,
    expected_episodes: int,
    metrics: AuditMetrics,
    location_prefix: str,
) -> None:
    expected_top = {
        "seed.txt",
        "scene_info.json",
        "_traj_data",
        "data",
        "instructions",
        "video",
    }
    if not task_root.is_dir():
        metrics.fail("organization", location_prefix, "task setting directory missing")
        return
    actual_top = {path.name for path in task_root.iterdir()}
    if actual_top != expected_top:
        metrics.fail(
            "organization",
            location_prefix,
            f"top entries differ: expected={sorted(expected_top)}, actual={sorted(actual_top)}",
        )

    expected_by_dir = {
        "_traj_data": episode_names("episode", ".pkl", expected_episodes),
        "data": episode_names("episode", ".hdf5", expected_episodes),
        "instructions": episode_names("episode", ".json", expected_episodes),
        "video": episode_names("episode", ".mp4", expected_episodes),
    }
    for dirname, expected in expected_by_dir.items():
        directory = task_root / dirname
        if not directory.is_dir():
            metrics.fail(
                "organization", f"{location_prefix}/{dirname}", "directory missing"
            )
            continue
        actual = {path.name for path in directory.iterdir() if path.is_file()}
        if actual != expected:
            missing = sorted(expected - actual)
            extra = sorted(actual - expected)
            metrics.fail(
                "organization",
                f"{location_prefix}/{dirname}",
                f"episode files differ: missing={missing[:10]}, extra={extra[:10]}",
            )


def compare_hash(
    source: Path,
    replay: Path,
    metrics: AuditMetrics,
    location: str,
) -> None:
    if not source.is_file() or not replay.is_file():
        metrics.fail(
            "hash",
            location,
            f"missing file: source={source.is_file()}, replay={replay.is_file()}",
        )
        return
    metrics.counts["hash_files_compared"] += 1
    if source.stat().st_size != replay.stat().st_size:
        metrics.fail(
            "hash",
            location,
            f"size differs: source={source.stat().st_size}, replay={replay.stat().st_size}",
        )
        return
    if sha256_file(source) != sha256_file(replay):
        metrics.fail("hash", location, "SHA256 differs")


def compare_dataset_exact(
    source: h5py.Dataset,
    replay: h5py.Dataset,
    metrics: AuditMetrics,
    location: str,
) -> None:
    metrics.counts["numeric_datasets_compared"] += 1
    if source.shape != replay.shape:
        metrics.fail(
            "numeric",
            location,
            f"shape differs: source={source.shape}, replay={replay.shape}",
        )
        return
    if source.dtype != replay.dtype:
        metrics.fail(
            "numeric",
            location,
            f"dtype differs: source={source.dtype}, replay={replay.dtype}",
        )
        return
    if not np.array_equal(source[...], replay[...]):
        metrics.fail("numeric", location, "values are not exactly equal")


def check_first_dimension(
    handle: h5py.File,
    paths: Iterable[str],
    expected_t: int,
    metrics: AuditMetrics,
    location_prefix: str,
) -> None:
    for path in paths:
        dataset = handle[path]
        if dataset.ndim == 0 or dataset.shape[0] != expected_t:
            metrics.fail(
                "time",
                f"{location_prefix}:{path}",
                f"first dimension is {dataset.shape}, expected T={expected_t}",
            )


def check_hdf5_numeric(
    source_path: Path,
    replay_path: Path,
    metrics: AuditMetrics,
    task: str,
    episode: int,
) -> int | None:
    location = f"{task}/episode{episode}.hdf5"
    if not source_path.is_file() or not replay_path.is_file():
        metrics.fail(
            "hdf5",
            location,
            f"missing file: source={source_path.is_file()}, replay={replay_path.is_file()}",
        )
        return None
    try:
        with h5py.File(source_path, "r") as source, h5py.File(
            replay_path, "r"
        ) as replay:
            source_paths = dataset_paths(source)
            replay_paths = dataset_paths(replay)
            allowed_extra = {
                f"observation/{camera}/{field}"
                for camera in TABLE_CAMERAS
                for field in CAMERA_FIELDS
            }
            if not source_paths.issubset(replay_paths):
                metrics.fail(
                    "schema",
                    location,
                    f"missing replay datasets: {sorted(source_paths - replay_paths)}",
                )
            extra = replay_paths - source_paths
            if extra != allowed_extra:
                metrics.fail(
                    "schema",
                    location,
                    f"unexpected replay datasets: {sorted(extra - allowed_extra)}; "
                    f"missing legal additions: {sorted(allowed_extra - extra)}",
                )

            vector_path = "joint_action/vector"
            if vector_path not in source_paths or vector_path not in replay_paths:
                metrics.fail("schema", location, f"missing {vector_path}")
                return None
            source_t = source[vector_path].shape[0]
            replay_t = replay[vector_path].shape[0]
            if source_t != replay_t:
                metrics.fail(
                    "time",
                    location,
                    f"T differs: source={source_t}, replay={replay_t}",
                )
                return None

            check_first_dimension(
                source, source_paths, source_t, metrics, f"source/{location}"
            )
            check_first_dimension(
                replay, replay_paths, replay_t, metrics, f"replay/{location}"
            )

            changed_paths = {
                f"observation/{camera}/{field}"
                for camera in CAMERAS
                for field in ("rgb", "intrinsic_cv")
            }
            for path in sorted(source_paths - changed_paths):
                if path in replay_paths:
                    compare_dataset_exact(
                        source[path], replay[path], metrics, f"{location}:{path}"
                    )

            for camera in CAMERAS:
                path = f"observation/{camera}/intrinsic_cv"
                if path not in source_paths or path not in replay_paths:
                    continue
                source_intrinsic = source[path][...]
                replay_intrinsic = replay[path][...]
                expected = np.einsum(
                    "ij,tjk->tik",
                    INTRINSIC_SCALE.astype(source_intrinsic.dtype),
                    source_intrinsic,
                )
                metrics.counts["intrinsic_datasets_compared"] += 1
                if (
                    source_intrinsic.shape != replay_intrinsic.shape
                    or source[path].dtype != replay[path].dtype
                    or not np.array_equal(expected, replay_intrinsic)
                ):
                    metrics.fail(
                        "intrinsic",
                        f"{location}:{path}",
                        "replay intrinsic is not exact 2x image scaling of source",
                    )

            required_vector_paths = (
                "joint_action/left_arm",
                "joint_action/left_gripper",
                "joint_action/right_arm",
                "joint_action/right_gripper",
                "joint_action/vector",
            )
            if all(path in replay_paths for path in required_vector_paths):
                expected_vector = np.concatenate(
                    [
                        replay["joint_action/left_arm"][...],
                        replay["joint_action/left_gripper"][...][..., None],
                        replay["joint_action/right_arm"][...],
                        replay["joint_action/right_gripper"][...][..., None],
                    ],
                    axis=1,
                )
                if not np.array_equal(
                    expected_vector, replay["joint_action/vector"][...]
                ):
                    metrics.fail(
                        "vector",
                        f"{location}:joint_action/vector",
                        "vector is not the ordered concatenation of the four action fields",
                    )

            for camera in TABLE_CAMERAS:
                expected_shapes = {
                    "rgb": (replay_t,),
                    "intrinsic_cv": (replay_t, 3, 3),
                    "extrinsic_cv": (replay_t, 3, 4),
                    "cam2world_gl": (replay_t, 4, 4),
                }
                for field, shape in expected_shapes.items():
                    path = f"observation/{camera}/{field}"
                    if path in replay_paths and replay[path].shape != shape:
                        metrics.fail(
                            "schema",
                            f"{location}:{path}",
                            f"shape is {replay[path].shape}, expected {shape}",
                        )

            metrics.counts["hdf5_files_compared"] += 1
            return replay_t
    except (OSError, KeyError, ValueError) as error:
        metrics.fail("hdf5", location, str(error))
        return None


def decode_jpeg(value: Any) -> np.ndarray | None:
    if isinstance(value, np.bytes_):
        payload = value.tobytes()
    elif isinstance(value, bytes):
        payload = value
    else:
        payload = bytes(value)
    return cv2.imdecode(np.frombuffer(payload, dtype=np.uint8), cv2.IMREAD_COLOR)


def mean_absolute_error(left: np.ndarray, right: np.ndarray) -> float:
    return float(
        np.mean(np.abs(left.astype(np.int16) - right.astype(np.int16)))
    )


def check_camera_stream(
    source_hdf5: Path,
    replay_hdf5: Path,
    replay_video: Path,
    task: str,
    episode: int,
    camera: str,
    image_threshold: float,
    video_threshold: float,
) -> CameraResult:
    result = CameraResult()
    prefix = f"{task}/episode{episode}:{camera}"
    capture: cv2.VideoCapture | None = None
    try:
        with h5py.File(source_hdf5, "r") as source, h5py.File(
            replay_hdf5, "r"
        ) as replay:
            path = f"observation/{camera}/rgb"
            if path not in source or path not in replay:
                result.fail("media", prefix, f"missing {path}")
                return result
            source_rgb = source[path]
            replay_rgb = replay[path]
            if len(source_rgb) != len(replay_rgb):
                result.fail(
                    "media",
                    prefix,
                    f"frame count differs: source={len(source_rgb)}, replay={len(replay_rgb)}",
                )
            frame_count = min(len(source_rgb), len(replay_rgb))

            if camera == "head_camera":
                capture = cv2.VideoCapture(str(replay_video))
                if not replay_video.is_file() or not capture.isOpened():
                    result.fail("video", prefix, f"cannot open {replay_video}")
                    capture = None
                else:
                    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    fps = float(capture.get(cv2.CAP_PROP_FPS))
                    declared_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
                    if (width, height) != (640, 480):
                        result.fail(
                            "video",
                            prefix,
                            f"video resolution is {width}x{height}, expected 640x480",
                        )
                    if abs(fps - 30.0) > 1e-3:
                        result.fail(
                            "video", prefix, f"video FPS is {fps}, expected 30"
                        )
                    if declared_frames != len(replay_rgb):
                        result.fail(
                            "video",
                            prefix,
                            f"video declares {declared_frames} frames, expected {len(replay_rgb)}",
                        )

            for index in range(frame_count):
                source_image = decode_jpeg(source_rgb[index])
                replay_image = decode_jpeg(replay_rgb[index])
                frame_location = f"{prefix}/frame{index}"
                if source_image is None:
                    result.fail(
                        "media", frame_location, "source JPEG cannot be decoded"
                    )
                    continue
                if replay_image is None:
                    result.fail(
                        "media", frame_location, "replay JPEG cannot be decoded"
                    )
                    continue
                result.counts["source_rgb_frames_decoded"] += 1
                result.counts["replay_rgb_frames_decoded"] += 1
                if source_image.shape != (240, 320, 3):
                    result.fail(
                        "media",
                        frame_location,
                        f"source shape is {source_image.shape}, expected (240, 320, 3)",
                    )
                if replay_image.shape != (480, 640, 3):
                    result.fail(
                        "media",
                        frame_location,
                        f"replay shape is {replay_image.shape}, expected (480, 640, 3)",
                    )
                if (
                    source_image.shape == (240, 320, 3)
                    and replay_image.shape == (480, 640, 3)
                ):
                    downsampled = cv2.resize(
                        replay_image, (320, 240), interpolation=cv2.INTER_AREA
                    )
                    image_mae = mean_absolute_error(source_image, downsampled)
                    result.max_image_mae = max(
                        result.max_image_mae, image_mae
                    )
                    result.counts["image_frames_compared"] += 1
                    if image_mae > image_threshold:
                        result.fail(
                            "media",
                            frame_location,
                            f"source/replay MAE {image_mae:.4f} exceeds {image_threshold}",
                        )

                if camera == "head_camera" and capture is not None:
                    ok, video_bgr = capture.read()
                    if not ok:
                        result.fail(
                            "video", frame_location, "video frame cannot be decoded"
                        )
                        capture.release()
                        capture = None
                    else:
                        result.counts["video_frames_decoded"] += 1
                        if video_bgr.shape != (480, 640, 3):
                            result.fail(
                                "video",
                                frame_location,
                                f"video frame shape is {video_bgr.shape}",
                            )
                        elif replay_image.shape == (480, 640, 3):
                            video_rgb = cv2.cvtColor(
                                video_bgr, cv2.COLOR_BGR2RGB
                            )
                            video_mae = mean_absolute_error(
                                video_rgb, replay_image
                            )
                            result.max_video_mae = max(
                                result.max_video_mae, video_mae
                            )
                            result.counts["video_frames_compared"] += 1
                            if video_mae > video_threshold:
                                result.fail(
                                    "video",
                                    frame_location,
                                    f"video/head RGB MAE {video_mae:.4f} "
                                    f"exceeds {video_threshold}",
                                )

            if capture is not None:
                ok, _ = capture.read()
                if ok:
                    result.fail(
                        "video",
                        prefix,
                        "video contains extra decodable frames after HDF5 T",
                    )
    except (OSError, KeyError, ValueError) as error:
        result.fail("media", prefix, str(error))
    finally:
        if capture is not None:
            capture.release()
    return result


def generate_report(
    args: argparse.Namespace,
    tasks: list[str],
    episodes: list[int],
    metrics: AuditMetrics,
    elapsed_seconds: float,
) -> str:
    failure_categories = Counter(failure.category for failure in metrics.failures)
    local_ok = not metrics.failures
    overall = "PASS" if local_ok else "FAIL"
    scope = "full" if args.tasks is None and args.episodes is None else "partial"
    scope_label = "全量" if scope == "full" else "局部"
    lines = [
        "# RoboTwin 640×480 Replay 数据验证",
        "",
        "## 验证范围",
        "",
        f"- 原始数据：{args.source_root}",
        f"- Replay 数据：{args.replay_root}",
        f"- 数据类型：{args.setting}",
        f"- 范围：{scope}，{len(tasks)} 个任务 × {len(episodes)} 个 episode",
        "- 媒体：front/head/left/right 四路并行逐帧解码；head MP4 逐帧核对",
        f"- 耗时：{elapsed_seconds / 60:.1f} 分钟",
        "",
        "## 验证结果",
        "",
        "| 检查项 | 结果 | 数量或说明 |",
        "| --- | --- | --- |",
        f"| 总体 | {overall} | Python failures: {len(metrics.failures)} |",
        f"| 组织结构 | "
        f"{'PASS' if failure_categories['organization'] == 0 else 'FAIL'} | "
        f"{len(tasks)} tasks / {len(episodes)} selected episodes |",
        f"| SHA256 文件对照 | {'PASS' if failure_categories['hash'] == 0 else 'FAIL'} | "
        f"{metrics.counts['hash_files_compared']} |",
        f"| HDF5 数值对照 | "
        f"{'PASS' if sum(failure_categories[name] for name in ('hdf5', 'schema', 'time', 'numeric', 'vector')) == 0 else 'FAIL'} | "
        f"{metrics.counts['hdf5_files_compared']} files / "
        f"{metrics.counts['numeric_datasets_compared']} datasets |",
        f"| 相机内参缩放 | {'PASS' if failure_categories['intrinsic'] == 0 else 'FAIL'} | "
        f"{metrics.counts['intrinsic_datasets_compared']} datasets |",
        f"| 四路 RGB | {'PASS' if failure_categories['media'] == 0 else 'FAIL'} | "
        f"{metrics.counts['image_frames_compared']} frame pairs，"
        f"max MAE={metrics.max_image_mae:.4f} |",
        f"| Head MP4 | {'PASS' if failure_categories['video'] == 0 else 'FAIL'} | "
        f"{metrics.counts['video_frames_compared']} frames，"
        f"max MAE={metrics.max_video_mae:.4f} |",
    ]

    lines.extend(["", "## 失败统计", ""])
    if not metrics.failures:
        lines.append("- 无。")
    else:
        for category, count in sorted(failure_categories.items()):
            lines.append(f"- {category}: {count}")
        lines.extend(["", f"前 {min(args.max_failures, len(metrics.failures))} 个失败：", ""])
        for failure in metrics.failures[: args.max_failures]:
            lines.append(
                f"- [{failure.category}] {failure.location}: {failure.message}"
            )

    lines.extend(
        [
            "",
            "## 结论",
            "",
            (
                f"Replay 数据通过本次{scope_label}验证。"
                if overall == "PASS"
                else "Replay 数据未通过本次验证，具体失败见上文。"
            ),
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    started = time.monotonic()
    metrics = AuditMetrics()

    source_tasks = task_names(args.source_root, args.setting)
    replay_tasks = task_names(args.replay_root, args.setting)
    if args.tasks is None and source_tasks != replay_tasks:
        metrics.fail(
            "organization",
            "dataset root",
            f"task sets differ: source_only={sorted(source_tasks - replay_tasks)}, "
            f"replay_only={sorted(replay_tasks - source_tasks)}",
        )
    if args.tasks is None and (
        len(source_tasks) != args.expected_tasks
        or len(replay_tasks) != args.expected_tasks
    ):
        metrics.fail(
            "organization",
            "dataset root",
            f"expected {args.expected_tasks} tasks, "
            f"found source={len(source_tasks)}, replay={len(replay_tasks)}",
        )

    if args.tasks:
        requested = set(args.tasks)
        missing = requested - (source_tasks & replay_tasks)
        if missing:
            metrics.fail(
                "organization",
                "task selection",
                f"requested tasks missing from one or both roots: {sorted(missing)}",
            )
        selected_tasks = sorted(requested & source_tasks & replay_tasks)
    else:
        selected_tasks = sorted(source_tasks & replay_tasks)

    if args.episodes:
        selected_episodes = sorted(set(args.episodes))
    else:
        selected_episodes = list(range(args.expected_episodes))
    invalid_episodes = [
        episode
        for episode in selected_episodes
        if episode < 0 or episode >= args.expected_episodes
    ]
    if invalid_episodes:
        raise ValueError(f"Episode indices out of range: {invalid_episodes}")

    for task in selected_tasks:
        source_task = args.source_root / task / args.setting
        replay_task = args.replay_root / task / args.setting
        if args.tasks is None and args.episodes is None:
            check_file_sets(
                source_task,
                args.expected_episodes,
                metrics,
                f"source/{task}",
            )
            check_file_sets(
                replay_task,
                args.expected_episodes,
                metrics,
                f"replay/{task}",
            )
        for filename in ("seed.txt", "scene_info.json"):
            compare_hash(
                source_task / filename,
                replay_task / filename,
                metrics,
                f"{task}/{filename}",
            )

    total_episodes = len(selected_tasks) * len(selected_episodes)
    with ThreadPoolExecutor(max_workers=4) as executor, tqdm(
        total=total_episodes,
        desc="Replay validation",
        unit="episode",
        dynamic_ncols=True,
        mininterval=0.5,
    ) as progress:
        for task in selected_tasks:
            source_task = args.source_root / task / args.setting
            replay_task = args.replay_root / task / args.setting
            for episode in selected_episodes:
                compare_hash(
                    source_task / f"_traj_data/episode{episode}.pkl",
                    replay_task / f"_traj_data/episode{episode}.pkl",
                    metrics,
                    f"{task}/_traj_data/episode{episode}.pkl",
                )
                compare_hash(
                    source_task / f"instructions/episode{episode}.json",
                    replay_task / f"instructions/episode{episode}.json",
                    metrics,
                    f"{task}/instructions/episode{episode}.json",
                )
                source_hdf5 = source_task / f"data/episode{episode}.hdf5"
                replay_hdf5 = replay_task / f"data/episode{episode}.hdf5"
                replay_video = replay_task / f"video/episode{episode}.mp4"
                replay_t = check_hdf5_numeric(
                    source_hdf5, replay_hdf5, metrics, task, episode
                )
                if replay_t is not None:
                    futures = {
                        executor.submit(
                            check_camera_stream,
                            source_hdf5,
                            replay_hdf5,
                            replay_video,
                            task,
                            episode,
                            camera,
                            args.image_mae_threshold,
                            args.video_mae_threshold,
                        ): camera
                        for camera in CAMERAS
                    }
                    for future in as_completed(futures):
                        camera = futures[future]
                        try:
                            metrics.merge_camera(future.result())
                        except Exception as error:  # keep auditing other episodes
                            metrics.fail(
                                "media",
                                f"{task}/episode{episode}:{camera}",
                                f"worker crashed: {error}",
                            )
                metrics.counts["episodes_checked"] += 1
                progress.set_postfix(
                    task=task,
                    episode=episode,
                    failures=len(metrics.failures),
                    refresh=False,
                )
                progress.update(1)

    elapsed = time.monotonic() - started
    report = generate_report(
        args,
        selected_tasks,
        selected_episodes,
        metrics,
        elapsed,
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(f"Report written: {args.report}")
    print(
        f"Checked {metrics.counts['episodes_checked']} episodes; "
        f"failures={len(metrics.failures)}; "
        f"elapsed={elapsed / 60:.1f} min"
    )
    return 0 if not metrics.failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
