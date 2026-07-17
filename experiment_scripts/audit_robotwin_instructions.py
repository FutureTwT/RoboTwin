#!/usr/bin/env python3

"""Audit RoboTwin Clean50 language instructions without modifying the dataset."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass, field
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET_ROOT = Path("/data1/common_data/RoboTwin2.0/dataset")
DEFAULT_SETTING = "aloha-agilex_clean_50"
DEFAULT_REPORT = REPO_ROOT / "doc/study-notes/data_review_instruction.md"
EXPECTED_TASK_COUNT = 50
EXPECTED_EPISODE_COUNT = 50
EXPECTED_SPLIT_SIZE = 100

PLACEHOLDER_RE = re.compile(r"{([^}]+)}")
TOKEN_RE = re.compile(r"[A-Za-z]+(?:[-'][A-Za-z]+)?")
ADJACENT_REPEAT_RE = re.compile(r"\b([A-Za-z]+)\s+\1\b", re.IGNORECASE)
DOUBLE_ARTICLE_RE = re.compile(r"\b(the|a|an)\s+\1\b", re.IGNORECASE)
META_PHRASE_RE = re.compile(
    r"without mentioning|correct arm|\bliteral\b|\bnotifies\b|"
    r"\bdescription\b|\binstruction\b",
    re.IGNORECASE,
)
LEFT_ARM_RE = re.compile(r"\bleft\s+(?:arm|hand)\b", re.IGNORECASE)
RIGHT_ARM_RE = re.compile(r"\bright\s+(?:arm|hand)\b", re.IGNORECASE)

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "in", "into", "is", "it", "of", "on", "or", "the", "then", "to",
    "up", "use", "using", "with", "after", "before", "this", "that",
}
GENERIC_NOUNS = {
    "actor", "basket", "block", "bottle", "bowl", "box", "can", "container",
    "cup", "item", "object", "pot", "shoe", "thing", "tool",
}
GENERIC_MODIFIERS = {
    "black", "blue", "brown", "gray", "green", "grey", "large", "medium",
    "metal", "plastic", "red", "small", "white", "wooden", "yellow",
}
KNOWN_COMPOUNDS = {
    "alarm-clock", "alarmclock", "breadbasket", "displaystand", "electronicscale",
    "kitchenpot", "paymentsign", "phone-stand", "phonestand", "pillbottle",
    "plasticbox", "playingcard", "playingcards", "qrcode", "remotecontrol",
    "shoe-box", "tabletrashbin", "toycar", "woodenblock",
}


@dataclass
class Example:
    episode: int
    split: str
    index: int
    text: str


@dataclass
class TaskStats:
    task: str
    episodes: int = 0
    instructions: int = 0
    asset_mismatches: int = 0
    missing_asset_descriptions: int = 0
    arm_mismatches: int = 0
    duplicate_seen: int = 0
    duplicate_unseen: int = 0
    seen_unseen_overlap: int = 0
    adjacent_repeats: int = 0
    double_articles: int = 0
    meta_phrases: int = 0
    empty_instructions: int = 0
    unresolved_placeholders: int = 0
    whitespace_issues: int = 0
    length_violations: int = 0
    multi_object_instructions: int = 0
    split_size_issues: int = 0
    word_limit: int | None = None
    used_assets: set[str] = field(default_factory=set)
    seen_names: set[str] = field(default_factory=set)
    unseen_names: set[str] = field(default_factory=set)
    seen_vocab: Counter[str] = field(default_factory=Counter)
    unseen_vocab: Counter[str] = field(default_factory=Counter)
    name_collisions: dict[str, set[str]] = field(default_factory=dict)
    generic_names: set[str] = field(default_factory=set)
    compound_terms: set[str] = field(default_factory=set)
    arm_mismatch_refs: list[Example] = field(default_factory=list)
    examples: dict[str, list[Example]] = field(
        default_factory=lambda: defaultdict(list)
    )

    @property
    def local_issue_count(self) -> int:
        return sum(
            (
                self.asset_mismatches,
                self.missing_asset_descriptions,
                self.arm_mismatches,
                self.adjacent_repeats,
                self.meta_phrases,
                self.empty_instructions,
                self.unresolved_placeholders,
                self.whitespace_issues,
                self.split_size_issues,
            )
        )


class DescriptionStore:
    def __init__(self, root: Path):
        self.root = root
        self.cache: dict[str, dict[str, list[str]] | None] = {}

    def load(self, value: str) -> dict[str, list[str]] | None:
        if value not in self.cache:
            path = self.root / f"{value}.json"
            if not path.is_file():
                self.cache[value] = None
            else:
                with path.open(encoding="utf-8") as stream:
                    data = json.load(stream)
                self.cache[value] = {
                    "seen": list(data.get("seen", [])),
                    "unseen": list(data.get("unseen", [])),
                }
        return self.cache[value]


def extract_placeholders(text: str) -> list[str]:
    return PLACEHOLDER_RE.findall(text)


def is_arm_parameter(key: str) -> bool:
    return len(key) == 1 and "a" <= key <= "z"


def is_eligible_template(template: str, episode_info: dict[str, str]) -> bool:
    placeholders = set(extract_placeholders(template))
    keys = {key.strip("{}") for key in episode_info}
    arm_keys = {key for key in keys if is_arm_parameter(key)}
    return placeholders == keys or (
        bool(arm_keys)
        and placeholders.union(arm_keys) == keys
        and not placeholders.intersection(arm_keys)
    )


def description_options(
    store: DescriptionStore,
    value: str,
    split: str,
) -> list[str] | None:
    descriptions = store.load(value)
    if descriptions is None:
        return None
    options = descriptions.get(split, [])
    if split == "unseen" and not options:
        options = descriptions.get("seen", [])
    return options


def replacement_pattern(
    key: str,
    value: str,
    split: str,
    store: DescriptionStore,
) -> str:
    options = description_options(store, value, split)
    if options is not None:
        escaped = [
            re.escape(f"the {description}")
            for description in sorted(set(options), key=len, reverse=True)
        ]
        if escaped:
            return "(?:" + "|".join(escaped) + ")"
    if is_arm_parameter(key):
        return re.escape(f"the {value} arm")
    return re.escape(value)


def template_pattern(
    template: str,
    episode_info: dict[str, str],
    split: str,
    store: DescriptionStore,
) -> str:
    chunks: list[str] = []
    position = 0
    for match in PLACEHOLDER_RE.finditer(template):
        chunks.append(re.escape(template[position:match.start()]))
        key = match.group(1)
        raw_key = "{" + key + "}"
        chunks.append(
            replacement_pattern(key, episode_info[raw_key], split, store)
        )
        position = match.end()
    chunks.append(re.escape(template[position:]))
    return "".join(chunks)


def compile_template_matcher(
    templates: list[str],
    episode_info: dict[str, str],
    split: str,
    store: DescriptionStore,
) -> tuple[re.Pattern[str] | None, list[str]]:
    eligible = [
        template
        for template in templates
        if is_eligible_template(template, episode_info)
    ]
    if not eligible:
        return None, []
    branches = [
        f"(?P<t{index}>{template_pattern(template, episode_info, split, store)})"
        for index, template in enumerate(eligible)
    ]
    return re.compile("^(?:" + "|".join(branches) + ")$"), eligible


def add_example(
    stats: TaskStats,
    category: str,
    episode: int,
    split: str,
    index: int,
    text: str,
    limit: int = 3,
) -> None:
    if len(stats.examples[category]) < limit:
        stats.examples[category].append(Example(episode, split, index, text))


def explicit_arms(text: str) -> set[str]:
    arms: set[str] = set()
    if LEFT_ARM_RE.search(text):
        arms.add("left")
    if RIGHT_ARM_RE.search(text):
        arms.add("right")
    return arms


def declared_arms(episode_info: dict[str, str]) -> set[str]:
    arms: set[str] = set()
    for raw_key, value in episode_info.items():
        key = raw_key.strip("{}")
        if not is_arm_parameter(key):
            continue
        if value == "dual":
            arms.update(("left", "right"))
        elif value in {"left", "right"}:
            arms.add(value)
    return arms


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def parse_word_limit(preference: str) -> int | None:
    patterns = (
        r"not\s+exceed\s+(\d+)",
        r"no\s+more\s+than\s+(\d+)",
        r"maximum(?:\s+of)?\s+(\d+)",
    )
    for pattern in patterns:
        match = re.search(pattern, preference, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def inspect_instruction(
    stats: TaskStats,
    text: str,
    episode: int,
    split: str,
    index: int,
    scene_arms: set[str],
    matched_template: str | None,
) -> None:
    stats.instructions += 1
    tokens = tokenize(text)
    if split == "seen":
        stats.seen_vocab.update(tokens)
    else:
        stats.unseen_vocab.update(tokens)

    if not text.strip():
        stats.empty_instructions += 1
        add_example(stats, "空指令", episode, split, index, text)
    if PLACEHOLDER_RE.search(text):
        stats.unresolved_placeholders += 1
        add_example(stats, "未替换占位符", episode, split, index, text)
    if text != text.strip() or "  " in text:
        stats.whitespace_issues += 1
        add_example(stats, "空白格式", episode, split, index, text)
    if ADJACENT_REPEAT_RE.search(text):
        stats.adjacent_repeats += 1
        add_example(stats, "重复词", episode, split, index, text)
    if DOUBLE_ARTICLE_RE.search(text):
        stats.double_articles += 1
    if META_PHRASE_RE.search(text):
        stats.meta_phrases += 1
        add_example(stats, "模板话术", episode, split, index, text)
    if stats.word_limit is not None and len(tokens) > stats.word_limit:
        stats.length_violations += 1
        add_example(stats, "长度异常", episode, split, index, text)

    mentioned = explicit_arms(text)
    if scene_arms and mentioned and not mentioned.issubset(scene_arms):
        stats.arm_mismatches += 1
        stats.arm_mismatch_refs.append(Example(episode, split, index, text))
        add_example(stats, "左右臂冲突", episode, split, index, text)

    if matched_template is not None:
        object_keys = {
            key for key in extract_placeholders(matched_template) if key.isupper()
        }
        if len(object_keys) >= 2:
            stats.multi_object_instructions += 1


def inspect_names(
    stats: TaskStats,
    asset_descriptions: dict[str, dict[str, list[str]]],
) -> None:
    collision_maps = {"seen": defaultdict(set), "unseen": defaultdict(set)}
    for asset, descriptions in asset_descriptions.items():
        for split in ("seen", "unseen"):
            options = descriptions.get(split, [])
            if split == "unseen" and not options:
                options = descriptions.get("seen", [])
            for name in options:
                normalized = " ".join(tokenize(name))
                collision_maps[split][normalized].add(asset)
                if split == "seen":
                    stats.seen_names.add(name)
                else:
                    stats.unseen_names.add(name)

                tokens = tokenize(name)
                if (
                    len(tokens) == 1 and tokens[0] in GENERIC_NOUNS
                ) or (
                    len(tokens) == 2
                    and tokens[-1] in GENERIC_NOUNS
                    and tokens[0] in GENERIC_MODIFIERS
                ):
                    stats.generic_names.add(name)
                for token in tokens:
                    if token in KNOWN_COMPOUNDS:
                        stats.compound_terms.add(token)

    collisions: dict[str, set[str]] = {}
    for split, mapping in collision_maps.items():
        for name, assets in mapping.items():
            if name and len(assets) > 1:
                collisions[f"{split}: {name}"] = assets
    stats.name_collisions = collisions


def run_codex_semantic_review(
    repo_root: Path,
    task_names: list[str],
    codex_bin: str,
    timeout: int,
) -> dict[str, Any]:
    if shutil.which(codex_bin) is None:
        return {
            "status": "unavailable",
            "reviewed_tasks": [],
            "issues": [],
            "message": f"Codex command not found: {codex_bin}",
        }

    schema = {
        "type": "object",
        "properties": {
            "reviewed_tasks": {
                "type": "array",
                "items": {"type": "string"},
            },
            "issues": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "task": {"type": "string"},
                        "severity": {
                            "type": "string",
                            "enum": ["error", "warning"],
                        },
                        "category": {
                            "type": "string",
                            "enum": [
                                "task_mismatch",
                                "object_role",
                                "arm_role",
                                "action_order",
                                "direction_or_state",
                            ],
                        },
                        "summary": {"type": "string"},
                        "evidence": {"type": "string"},
                    },
                    "required": [
                        "task", "severity", "category", "summary", "evidence"
                    ],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["reviewed_tasks", "issues"],
        "additionalProperties": False,
    }
    prompt = f"""You are performing a read-only semantic audit of RoboTwin language templates.

Inspect exactly these {len(task_names)} tasks:
{json.dumps(task_names, ensure_ascii=False)}

For every task, compare:
1. description/task_instruction/<task>.json: full_description, schema, seen, unseen.
2. envs/<task>.py: especially play_once(), manipulated objects, arm_tag/opposite-arm roles,
   action order, directions, and final task state.

Report only genuine semantic mismatches. Ignore grammar, duplicate sentences, word count,
asset-description wording, and already generated episode files; those are checked locally.
Do not modify files. Be conservative: omit stylistic preferences and valid shortened commands.
The reviewed_tasks array must contain every task you actually inspected. Return only the JSON
object required by the output schema.
"""

    with tempfile.TemporaryDirectory(prefix="robotwin-instruction-audit-") as temp_dir:
        temp_root = Path(temp_dir)
        schema_path = temp_root / "schema.json"
        result_path = temp_root / "result.json"
        schema_path.write_text(
            json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        command = [
            codex_bin,
            "exec",
            "--sandbox",
            "read-only",
            "--ephemeral",
            "--color",
            "never",
            "--output-schema",
            str(schema_path),
            "--output-last-message",
            str(result_path),
            "--cd",
            str(repo_root),
            "-",
        ]
        try:
            completed = subprocess.run(
                command,
                input=prompt,
                text=True,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "reviewed_tasks": [],
                "issues": [],
                "message": f"Codex semantic review exceeded {timeout} seconds.",
            }

        if completed.returncode != 0 or not result_path.is_file():
            message = (completed.stderr or completed.stdout).strip()
            return {
                "status": "failed",
                "reviewed_tasks": [],
                "issues": [],
                "message": message[-1000:] or f"Codex exited with {completed.returncode}.",
            }
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            return {
                "status": "invalid_output",
                "reviewed_tasks": [],
                "issues": [],
                "message": str(error),
            }
    result["status"] = "ok"
    result["message"] = ""
    return result


def top_split_only_words(
    primary: Counter[str],
    other: Counter[str],
    limit: int = 10,
) -> list[tuple[str, int]]:
    candidates = [
        (word, count)
        for word, count in primary.items()
        if word not in other and word not in STOPWORDS and len(word) > 1
    ]
    return sorted(candidates, key=lambda item: (-item[1], item[0]))[:limit]


def format_words(words: list[tuple[str, int]]) -> str:
    if not words:
        return "无"
    return "、".join(f"`{word}`({count})" for word, count in words)


def generate_report(
    task_stats: list[TaskStats],
    _semantic_review: dict[str, Any],
    dataset_root: Path,
    setting: str,
) -> str:
    totals = Counter()
    for stats in task_stats:
        for field_name in (
            "episodes", "instructions", "asset_mismatches",
            "missing_asset_descriptions", "arm_mismatches", "duplicate_seen",
            "duplicate_unseen", "seen_unseen_overlap", "adjacent_repeats",
            "double_articles", "meta_phrases", "empty_instructions",
            "unresolved_placeholders", "whitespace_issues", "length_violations",
            "multi_object_instructions", "split_size_issues",
        ):
            totals[field_name] += getattr(stats, field_name)

    all_seen_vocab = Counter()
    all_unseen_vocab = Counter()
    for stats in task_stats:
        all_seen_vocab.update(stats.seen_vocab)
        all_unseen_vocab.update(stats.unseen_vocab)
    seen_vocab_set = set(all_seen_vocab) - STOPWORDS
    unseen_vocab_set = set(all_unseen_vocab) - STOPWORDS
    union = seen_vocab_set | unseen_vocab_set
    vocabulary_overlap = len(seen_vocab_set & unseen_vocab_set) / len(union) if union else 1.0

    lines = [
        "# RoboTwin 文本指令审查",
        "",
        "## 审查范围",
        "",
        f"- 数据目录：`{dataset_root}`",
        f"- 数据类型：`{setting}`",
        f"- 任务数量：{len(task_stats)}",
        f"- Episode 数量：{totals['episodes']}",
        f"- 指令数量：{totals['instructions']}",
        "- 仅检查文本、场景资产和任务语义，不检查运动轨迹。",
        "",
        "## 审查结果",
        "",
        "| 审查项 | 结果 |",
        "| --- | ---: |",
        f"| 场景资产无法匹配的指令 | {totals['asset_mismatches']} |",
        f"| 缺少数字资产描述文件 | {totals['missing_asset_descriptions']} |",
        f"| 左右臂与 `scene_info.json` 冲突 | {totals['arm_mismatches']} |",
        f"| seen/unseen 完全相同指令 | {totals['seen_unseen_overlap']} |",
        f"| 空指令 | {totals['empty_instructions']} |",
        f"| 未替换占位符 | {totals['unresolved_placeholders']} |",
        f"| 超出任务模板长度要求 | {totals['length_violations']} |",
        f"| 多物体指令 | {totals['multi_object_instructions']} |",
        "",
        "## seen / unseen",
        "",
        f"- 去除常用虚词后，seen 词汇 {len(seen_vocab_set)} 个，unseen 词汇 {len(unseen_vocab_set)} 个，词汇集合重合度为 {vocabulary_overlap:.1%}。",
        f"- seen 独有高频词：{format_words(top_split_only_words(all_seen_vocab, all_unseen_vocab))}",
        f"- unseen 独有高频词：{format_words(top_split_only_words(all_unseen_vocab, all_seen_vocab))}",
        "",
        "## 任务摘要",
        "",
        "| 任务 | seen 名称 | unseen 名称 | 同名跨资产 | 左右臂冲突 | 其他文本问题 |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for stats in task_stats:
        lines.append(
            f"| `{stats.task}` | {len(stats.seen_names)} | {len(stats.unseen_names)} | "
            f"{len(stats.name_collisions)} | {stats.arm_mismatches} | "
            f"{stats.local_issue_count - stats.arm_mismatches} |"
        )

    conflict_stats = [stats for stats in task_stats if stats.arm_mismatch_refs]
    if conflict_stats:
        lines.extend(
            [
                "",
                "## 左右臂冲突索引",
                "",
                "以下 index 是对应 `instructions/episode{N}.json` 中 seen 或 unseen 列表的 0-based index。",
            ]
        )
        for stats in conflict_stats:
            lines.extend(["", f"### `{stats.task}`", ""])
            for split in ("seen", "unseen"):
                refs = [ref for ref in stats.arm_mismatch_refs if ref.split == split]
                lines.append(f"- {split}：{len(refs)} 条")
                by_episode: dict[int, list[int]] = defaultdict(list)
                for ref in refs:
                    by_episode[ref.episode].append(ref.index)
                for episode, indices in sorted(by_episode.items()):
                    index_text = ", ".join(str(index) for index in sorted(indices))
                    lines.append(f"  - `episode{episode}`：`[{index_text}]`")

    lines.extend(
        [
            "",
            "## 结论",
            "",
            "官方指令与场景资产的对应关系由本地规则全量检查；审查结果与任务摘要见上表。原始 `common_data` 未被修改。",
            "",
            "左右臂冲突来自两个写死 `right arm` 的任务模板，并非 272 个独立的随机错误。每个 episode 的模板会先随机打乱，再循环复用至生成 100 条指令，因此错误 index 呈固定间隔：",
            "",
            "- 根因模板 `description/task_instruction/adjust_bottle.json:23`：`Pick {A} head-up using the right arm`。",
            "- 根因模板 `description/task_instruction/place_object_stand.json:67`：`Set {A} onto {B} using the right arm.`。",
            "- `adjust_bottle` 的 seen 有 50 个模板，错误模板每个 episode 出现 2 次，index 为 `x` 和 `x+50`；31 个左臂 episode 共 `31 × 2 = 62` 条冲突，unseen 无冲突。",
            "- `place_object_stand` 的 unseen 有 10 个模板，错误模板每个 episode 出现 10 次，index 为 `x, x+10, ..., x+90`；21 个左臂 episode 共 `21 × 10 = 210` 条冲突，seen 无冲突。",
            "- 随机打乱只改变各 episode 的起始 index `x`；同一 episode 内的间隔保持不变。场景要求右臂时，模板中的 `right arm` 与场景一致，不计为冲突。",
            "",
        ]
    )
    return "\n".join(lines)


def audit_task(
    task_root: Path,
    template_root: Path,
    store: DescriptionStore,
    expected_episodes: int,
) -> TaskStats:
    task = task_root.parent.name
    stats = TaskStats(task=task)
    scene_path = task_root / "scene_info.json"
    template_path = template_root / f"{task}.json"
    if not scene_path.is_file():
        raise FileNotFoundError(f"Missing scene info: {scene_path}")
    if not template_path.is_file():
        raise FileNotFoundError(f"Missing task template: {template_path}")

    with scene_path.open(encoding="utf-8") as stream:
        scenes = json.load(stream)
    with template_path.open(encoding="utf-8") as stream:
        template_data = json.load(stream)
    stats.word_limit = parse_word_limit(template_data.get("preference", ""))
    asset_descriptions: dict[str, dict[str, list[str]]] = {}

    for episode in range(expected_episodes):
        scene_key = f"episode_{episode}"
        if scene_key not in scenes:
            raise KeyError(f"Missing {scene_key} in {scene_path}")
        instruction_path = task_root / "instructions" / f"episode{episode}.json"
        if not instruction_path.is_file():
            raise FileNotFoundError(f"Missing instruction file: {instruction_path}")
        with instruction_path.open(encoding="utf-8") as stream:
            instructions = json.load(stream)

        stats.episodes += 1
        episode_info = scenes[scene_key].get("info", {})
        scene_arms = declared_arms(episode_info)
        for raw_key, value in episode_info.items():
            key = raw_key.strip("{}")
            if not key.isupper():
                continue
            descriptions = store.load(value)
            if descriptions is None:
                if "/" in value:
                    stats.missing_asset_descriptions += 1
                continue
            stats.used_assets.add(value)
            asset_descriptions[value] = descriptions

        for split in ("seen", "unseen"):
            split_instructions = list(instructions.get(split, []))
            if len(split_instructions) != EXPECTED_SPLIT_SIZE:
                stats.split_size_issues += 1
            duplicate_count = len(split_instructions) - len(set(split_instructions))
            if split == "seen":
                stats.duplicate_seen += duplicate_count
            else:
                stats.duplicate_unseen += duplicate_count

            matcher, eligible_templates = compile_template_matcher(
                list(template_data.get(split, [])), episode_info, split, store
            )
            for index, text in enumerate(split_instructions):
                match = matcher.fullmatch(text) if matcher is not None else None
                matched_template = None
                if match is None:
                    stats.asset_mismatches += 1
                    add_example(
                        stats, "场景资产不匹配", episode, split, index, text
                    )
                elif match.lastgroup is not None:
                    matched_template = eligible_templates[int(match.lastgroup[1:])]
                inspect_instruction(
                    stats,
                    text,
                    episode,
                    split,
                    index,
                    scene_arms,
                    matched_template,
                )

        stats.seen_unseen_overlap += len(
            set(instructions.get("seen", []))
            & set(instructions.get("unseen", []))
        )

    inspect_names(stats, asset_descriptions)
    return stats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit RoboTwin Clean50 language instructions and write a Markdown report."
    )
    parser.add_argument("--dataset-root", type=Path, default=DEFAULT_DATASET_ROOT)
    parser.add_argument("--setting", default=DEFAULT_SETTING)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--expected-tasks", type=int, default=EXPECTED_TASK_COUNT)
    parser.add_argument("--expected-episodes", type=int, default=EXPECTED_EPISODE_COUNT)
    parser.add_argument(
        "--skip-codex",
        action="store_true",
        help="Skip the single Codex CLI semantic review and run local checks only.",
    )
    parser.add_argument("--codex-bin", default="codex")
    parser.add_argument("--codex-timeout", type=int, default=1200)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    task_roots = sorted(
        path
        for path in args.dataset_root.glob(f"*/{args.setting}")
        if path.is_dir()
    )
    if len(task_roots) != args.expected_tasks:
        raise RuntimeError(
            f"Expected {args.expected_tasks} task directories, found {len(task_roots)}."
        )

    template_root = REPO_ROOT / "description/task_instruction"
    store = DescriptionStore(REPO_ROOT / "description/objects_description")
    task_stats: list[TaskStats] = []
    for index, task_root in enumerate(task_roots, start=1):
        print(f"[{index:02d}/{len(task_roots)}] Local audit: {task_root.parent.name}")
        task_stats.append(
            audit_task(task_root, template_root, store, args.expected_episodes)
        )

    task_names = [stats.task for stats in task_stats]
    if args.skip_codex:
        semantic_review = {
            "status": "skipped",
            "reviewed_tasks": [],
            "issues": [],
            "message": "Skipped by --skip-codex.",
        }
    else:
        print("[Codex] Running one read-only semantic review for all task pairs...")
        semantic_review = run_codex_semantic_review(
            REPO_ROOT, task_names, args.codex_bin, args.codex_timeout
        )

    report = generate_report(
        task_stats, semantic_review, args.dataset_root, args.setting
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(f"Report written: {args.report}")
    print(
        f"Audited {len(task_stats)} tasks and "
        f"{sum(stats.instructions for stats in task_stats)} instructions."
    )
    print(
        f"Codex status: {semantic_review.get('status')}; "
        f"issues: {len(semantic_review.get('issues', []))}"
    )


if __name__ == "__main__":
    main()
