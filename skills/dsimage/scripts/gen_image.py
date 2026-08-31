#!/usr/bin/env python3
"""统一图像生成脚本，同时兼容 OpenAI 同步 API 和 apimart.ai 异步 API。

单张模式：--prompt / --prompt-file
批量模式：--batch jobs.json —— 多图套图推荐用法，一次并发生成全部槽位；
失败槽位加 --skip-existing 重跑同一命令即可只补失败的图。

自动检测 API 模式：
  - 基础 URL 包含 "apimart" → 异步轮询模式
  - 其他 → OpenAI 同步模式
  - 可用 --mode sync|async 或环境变量 IMG_API_MODE 强制指定

配置来自环境变量或 .env 文件：
- IMG_BASE_URL: API 根地址
- IMG_MODEL: 图片模型名
- IMG_API_KEY: API key
- IMG_API_MODE（可选）: sync 或 async，覆盖自动检测
"""

from __future__ import annotations

import argparse
import base64
import binascii
import concurrent.futures
import http.client
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any, NoReturn

# Windows 控制台默认 GBK，重配为 UTF-8 避免中文输出崩溃
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


ENV_BASE_URL = "IMG_BASE_URL"
ENV_MODEL = "IMG_MODEL"
ENV_API_KEY = "IMG_API_KEY"
ENV_ALIASES = {
    ENV_BASE_URL: ("OPENAI_BASE_URL", "OPENAI_API_BASE"),
    ENV_MODEL: ("OPENAI_IMAGE_MODEL", "IMAGE_MODEL", "OPENAI_MODEL"),
    ENV_API_KEY: ("OPENAI_API_KEY",),
}

VALID_RATIOS = ("auto", "1:1", "3:2", "2:3", "4:3", "3:4", "5:4", "4:5",
                "16:9", "9:16", "2:1", "1:2", "21:9", "9:21")
VALID_RESOLUTIONS = ("1k", "2k", "4k")
VALID_FORMATS = ("png", "jpeg", "webp")

PIXEL_TO_RATIO: dict[str, str] = {
    "1024x1024": "1:1", "2048x2048": "1:1",
    "1536x1024": "3:2", "2048x1360": "3:2",
    "1024x1536": "2:3", "1360x2048": "2:3",
    "1024x768": "4:3", "2048x1536": "4:3",
    "768x1024": "3:4", "1536x2048": "3:4",
    "1280x1024": "5:4", "2560x2048": "5:4",
    "1024x1280": "4:5", "2048x2560": "4:5",
    "1536x864": "16:9", "2048x1152": "16:9", "3840x2160": "16:9",
    "864x1536": "9:16", "1152x2048": "9:16", "2160x3840": "9:16",
    "2048x1024": "2:1", "2688x1344": "2:1", "3840x1920": "2:1",
    "1024x2048": "1:2", "1344x2688": "1:2", "1920x3840": "1:2",
    "2016x864": "21:9", "2688x1152": "21:9", "3840x1648": "21:9",
    "864x2016": "9:21", "1152x2688": "9:21", "1648x3840": "9:21",
}

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"


class GenError(RuntimeError):
    """生成失败。批量模式下单个槽位的 GenError 不终止其他槽位。"""


def fail(message: str) -> NoReturn:
    raise GenError(message)


_print_lock = threading.Lock()


def log(label: str, message: str) -> None:
    with _print_lock:
        print(f"[{label}] {message}", file=sys.stderr)


# ── 配置与环境 ──────────────────────────────────────────────

def read_prompt_text(path: Path) -> str:
    try:
        prompt = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        fail(f"无法读取 prompt 文件：{exc}")
    if not prompt:
        fail(f"prompt 文件为空：{path}")
    return prompt


def read_prompt(args: argparse.Namespace) -> str:
    if args.prompt:
        prompt = args.prompt.strip()
        if not prompt:
            fail("prompt 不能为空。")
        return prompt
    return read_prompt_text(Path(args.prompt_file))


def strip_env_value(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def env_defines_img_keys(env_file: Path) -> bool:
    try:
        text = env_file.read_text(encoding="utf-8")
    except OSError:
        return False
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if line.startswith("IMG_") and "=" in line:
            return True
    return False


def find_default_env_file() -> Path | None:
    # 向上查找时只认包含 IMG_ 配置的 .env，避免误用其他项目里给
    # 文本模型准备的 OPENAI_API_KEY
    for directory in (Path.cwd(), *Path.cwd().parents):
        env_file = directory / ".env"
        if env_file.is_file() and env_defines_img_keys(env_file):
            return env_file
    skill_env = Path(__file__).resolve().parent.parent / ".env"
    if skill_env.is_file():
        return skill_env
    return None


def load_env_file(env_file: Path | None) -> None:
    if env_file is None:
        return
    try:
        lines = env_file.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        fail(f"无法读取 .env 文件：{exc}")
    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if "=" not in line:
            fail(f".env 第 {line_number} 行格式不正确，应为 KEY=value。")
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            fail(f".env 第 {line_number} 行缺少变量名。")
        if key not in os.environ:
            os.environ[key] = strip_env_value(value)


def require_config(name: str) -> str:
    candidates = (name, *ENV_ALIASES.get(name, ()))
    for candidate in candidates:
        value = os.environ.get(candidate, "").strip()
        if value:
            return value
    accepted = "、".join(candidates)
    fail(
        f"缺少配置 {name}。请在 .env 中设置 IMG_BASE_URL、IMG_MODEL、IMG_API_KEY；"
        f"也兼容这些变量名：{accepted}。"
    )


# ── 模式检测 ──────────────────────────────────────────────

def detect_mode(base_url: str, explicit_mode: str | None) -> str:
    if explicit_mode in ("sync", "async"):
        return explicit_mode
    env_mode = os.environ.get("IMG_API_MODE", "").strip().lower()
    if env_mode in ("sync", "async"):
        return env_mode
    if "apimart" in base_url.lower():
        return "async"
    return "sync"


def size_to_ratio(size: str) -> str:
    if ":" in size:
        return size
    lower = size.lower()
    if lower in PIXEL_TO_RATIO:
        return PIXEL_TO_RATIO[lower]
    fail(f"无法将像素尺寸 '{size}' 转换为比例。请直接使用比例格式，如 1:1、16:9、2:3。")


def resolve_timeout(args: argparse.Namespace) -> int:
    if args.timeout is not None:
        return args.timeout
    return 480 if args.resolution == "4k" else 180


# ── 图片编码 ──────────────────────────────────────────────

def encode_image_data_uri(image_path: str) -> str:
    data, mime, _ = read_image_file(image_path)
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{b64}"


def read_image_file(image_path: str) -> tuple[bytes, str, str]:
    path = Path(image_path)
    if not path.is_file():
        fail(f"参考图片不存在：{image_path}")
    suffix = path.suffix.lower().lstrip(".")
    mime_map = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                "webp": "image/webp", "gif": "image/gif"}
    mime = mime_map.get(suffix)
    if not mime:
        fail(f"不支持的图片格式：.{suffix}，仅支持 png/jpg/jpeg/webp/gif。")
    try:
        data = path.read_bytes()
    except OSError as exc:
        fail(f"无法读取参考图片：{exc}")
    return data, mime, path.name


# ── HTTP 工具 ──────────────────────────────────────────────

def _post_json(request: urllib.request.Request, timeout: int, what: str) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        fail(f"{what}返回 HTTP {exc.code}：{detail}")
    except urllib.error.URLError as exc:
        fail(f"无法连接接口：{exc.reason}")
    except (http.client.RemoteDisconnected, TimeoutError):
        fail("接口连接失败或超时，请稍后重试。")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        fail(f"{what}返回的不是有效 JSON：{raw[:500]}")
    if not isinstance(parsed, dict):
        fail(f"{what}格式不正确：顶层结果不是对象。")
    return parsed


def http_post(url: str, api_key: str, payload: dict[str, Any], timeout: int = 120) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url, data=body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "User-Agent": UA},
        method="POST",
    )
    return _post_json(request, timeout, "接口")


def http_post_multipart(url: str, api_key: str, fields: dict[str, str], file_field: str,
                        filename: str, file_data: bytes, file_mime: str,
                        timeout: int = 300) -> dict[str, Any]:
    """以 multipart/form-data 提交（OpenAI /images/edits 图生图标准格式）。"""
    boundary = "dsimage-" + uuid.uuid4().hex
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n".encode("utf-8")
            + str(value).encode("utf-8") + b"\r\n"
        )
    chunks.append(
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"{file_field}\"; filename=\"{filename}\"\r\n"
        f"Content-Type: {file_mime}\r\n\r\n".encode("utf-8") + file_data + b"\r\n"
    )
    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    request = urllib.request.Request(
        url, data=b"".join(chunks),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": f"multipart/form-data; boundary={boundary}", "User-Agent": UA},
        method="POST",
    )
    return _post_json(request, timeout, "图生图接口")


def http_get(url: str, api_key: str, timeout: int = 30) -> dict[str, Any]:
    request = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {api_key}", "User-Agent": UA}, method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        fail(f"查询接口返回 HTTP {exc.code}：{detail}")
    except (urllib.error.URLError, http.client.RemoteDisconnected, TimeoutError):
        fail("查询接口连接失败或超时。")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        fail(f"查询接口返回的不是有效 JSON：{raw[:500]}")
    return parsed


# ── 输出命名 ──────────────────────────────────────────────

def output_name(name_prefix: str | None, index: int, suffix: str) -> str:
    """批量模式按槽位命名（h1.png、h1-2.png）；单张模式带随机段防止同秒覆盖。"""
    suffix = suffix.lstrip(".")
    if name_prefix:
        stem = name_prefix if index == 0 else f"{name_prefix}-{index + 1}"
        return f"{stem}.{suffix}"
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    return f"image-{timestamp}-{uuid.uuid4().hex[:6]}-{index + 1:02d}.{suffix}"


# ── 同步模式（OpenAI 兼容）──────────────────────────────────

SYNC_SIZE_MAP: dict[str, str] = {
    "1:1": "1024x1024",
    "2:3": "1024x1536", "3:4": "1024x1536", "4:5": "1024x1536",
    "9:16": "1024x1536", "1:2": "1024x1536", "9:21": "1024x1536",
    "3:2": "1536x1024", "4:3": "1536x1024", "5:4": "1536x1024",
    "16:9": "1536x1024", "2:1": "1536x1024", "21:9": "1536x1024",
}


def sync_size(size: str) -> str:
    """同步端点只接受像素尺寸或 auto；把比例翻译成最接近的档位。"""
    lowered = size.lower()
    if "x" in lowered or lowered == "auto":
        return lowered
    return SYNC_SIZE_MAP.get(size_to_ratio(size), "auto")


def build_sync_payload(args: argparse.Namespace, prompt: str, model: str) -> dict[str, Any]:
    payload: dict[str, Any] = {"model": model, "prompt": prompt, "n": args.n, "size": sync_size(args.size)}
    if args.quality:
        payload["quality"] = args.quality
    return payload


def run_sync(base_url: str, api_key: str, args: argparse.Namespace, prompt: str,
             model: str, output_dir: Path, fmt: str,
             label: str = "sync", name_prefix: str | None = None) -> list[Path]:
    if args.image:
        endpoint = f"{base_url}/images/edits"
        file_data, file_mime, filename = read_image_file(args.image)
        fields = {"model": model, "prompt": prompt, "n": str(args.n), "size": sync_size(args.size)}
        if args.quality:
            fields["quality"] = args.quality
        log(label, f"图生图模式：参考图经 {endpoint} 提交...")
        result = http_post_multipart(endpoint, api_key, fields, "image", filename, file_data, file_mime)
        return save_sync_images(result, output_dir, fmt, name_prefix)
    payload = build_sync_payload(args, prompt, model)
    endpoint = f"{base_url}/images/generations"
    log(label, f"提交生成请求到 {endpoint}...")
    result = http_post(endpoint, api_key, payload, timeout=300)
    return save_sync_images(result, output_dir, fmt, name_prefix)


def save_sync_images(result: dict[str, Any], output_dir: Path, fmt: str,
                     name_prefix: str | None = None) -> list[Path]:
    data = result.get("data")
    if not isinstance(data, list) or not data:
        fail(f"接口返回中没有 data 图片数组：{json.dumps(result)[:300]}")
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            fail("接口返回格式不正确：data 中包含非对象项目。")
        if item.get("b64_json"):
            try:
                image_bytes = base64.b64decode(item["b64_json"])
            except (binascii.Error, ValueError) as exc:
                fail(f"无法解码 b64_json 图片：{exc}")
            p = output_dir / output_name(name_prefix, index, fmt)
            p.write_bytes(image_bytes)
            paths.append(p)
        elif item.get("url"):
            image_url = item["url"]
            p = output_dir / output_name(name_prefix, index, _suffix_from_url(image_url, fmt))
            dl_req = urllib.request.Request(image_url, headers={"User-Agent": UA})
            with urllib.request.urlopen(dl_req, timeout=120) as resp:
                p.write_bytes(resp.read())
            paths.append(p)
        else:
            fail("图片结果既没有 b64_json，也没有 url。")
    return paths


# ── 异步模式（apimart.ai）──────────────────────────────────

def build_async_payload(args: argparse.Namespace, prompt: str, model: str) -> dict[str, Any]:
    ratio = size_to_ratio(args.size)
    payload: dict[str, Any] = {"model": model, "prompt": prompt, "n": 1, "size": ratio, "resolution": args.resolution}
    if args.image:
        payload["image_urls"] = [encode_image_data_uri(args.image)]
    return payload


def run_async(base_url: str, api_key: str, payload: dict[str, Any],
              output_dir: Path, fmt: str, poll_interval: int, timeout: int,
              label: str = "async", name_prefix: str | None = None) -> list[Path]:
    endpoint = f"{base_url}/images/generations"
    log(label, f"提交异步任务到 {endpoint}...")
    result = http_post(endpoint, api_key, payload, timeout=30)

    code = result.get("code")
    if code and code != 200:
        error = result.get("error", {})
        fail(f"提交失败（code={code}）：{error.get('message', json.dumps(result))}")

    data = result.get("data")
    if not isinstance(data, list) or not data:
        fail(f"提交响应缺少 data 数组：{json.dumps(result)[:300]}")
    task_id = data[0].get("task_id")
    if not task_id:
        fail(f"提交响应缺少 task_id：{json.dumps(data[0])[:300]}")

    log(label, f"任务已提交: {task_id}，等待 15s 后开始轮询...")
    time.sleep(15)

    task_data = _poll_task(base_url, api_key, task_id, poll_interval, timeout, label)
    try:
        cost = float(task_data.get("cost", 0) or 0)
    except (TypeError, ValueError):
        cost = 0.0
    log(label, f"任务完成，耗时 {task_data.get('actual_time', 0)}s，费用 ${cost:.4f}")

    return _save_async_images(task_data, output_dir, fmt, name_prefix, label)


def _poll_task(base_url: str, api_key: str, task_id: str,
               poll_interval: int, timeout: int, label: str = "async") -> dict[str, Any]:
    url = f"{base_url}/tasks/{task_id}"
    start = time.time()
    while True:
        elapsed = time.time() - start
        if elapsed > timeout:
            fail(f"任务 {task_id} 超时（{timeout}s），请稍后手动查询。")
        result = http_get(url, api_key)
        task_data = result.get("data", {})
        status = task_data.get("status", "")
        if status == "completed":
            return task_data
        if status == "failed":
            error = task_data.get("error", {})
            fail(f"任务 {task_id} 失败：{error.get('message', json.dumps(task_data)[:300])}")
        progress = task_data.get("progress", 0)
        log(label, f"轮询中... 状态={status} 进度={progress}% 耗时={elapsed:.0f}s")
        time.sleep(poll_interval)


def _save_async_images(task_data: dict[str, Any], output_dir: Path, fmt: str,
                       name_prefix: str | None = None, label: str = "async") -> list[Path]:
    result = task_data.get("result", {})
    images = result.get("images")
    if not isinstance(images, list) or not images:
        fail(f"任务结果中缺少 images 数组：{json.dumps(task_data)[:300]}")
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for index, img_item in enumerate(images):
        url_list = img_item.get("url")
        if not isinstance(url_list, list) or not url_list:
            fail(f"图片结果缺少 url 数组：{json.dumps(img_item)[:300]}")
        image_url = url_list[0]
        output_path = output_dir / output_name(name_prefix, index, _suffix_from_url(image_url, fmt))
        log(label, f"下载图片: {image_url}")
        dl_req = urllib.request.Request(image_url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(dl_req, timeout=120) as resp:
                output_path.write_bytes(resp.read())
        except urllib.error.URLError as exc:
            fail(f"无法下载图片：{exc.reason}")
        except TimeoutError:
            fail("下载图片超时。")
        paths.append(output_path)
    return paths


# ── 单张任务入口 ──────────────────────────────────────────

def generate_one(base_url: str, api_key: str, model: str, mode: str,
                 args: argparse.Namespace, prompt: str, output_dir: Path,
                 label: str, name_prefix: str | None = None) -> list[Path]:
    if mode == "async":
        payload = build_async_payload(args, prompt, model)
        return run_async(base_url, api_key, payload, output_dir, args.format,
                         args.poll_interval, resolve_timeout(args), label, name_prefix)
    return run_sync(base_url, api_key, args, prompt, model, output_dir, args.format, label, name_prefix)


def is_rate_limit(exc: BaseException) -> bool:
    return is_backoff_error(str(exc))


def is_backoff_error(message: str) -> bool:
    """并发上限、超时、5xx 等可回退重试；401/文件错误不回退。"""
    text = message.lower()
    if any(x in text for x in ("401", "403", "不存在", "prompt 为空", "缺少配置")):
        return False
    return any(x in text for x in (
        "429", "rate_limit", "concurrency limit", "超时", "timeout",
        "连接失败", "http 5", "503", "502", "500",
    ))


def generate_with_retry(base_url: str, api_key: str, model: str, mode: str,
                        args: argparse.Namespace, prompt: str, output_dir: Path,
                        label: str, name_prefix: str | None = None,
                        retries: int = 4) -> list[Path]:
    """单张：额度/超时退避重试。批量模式由 run_batch 降并发回退，不走这里。"""
    delay = 15
    last: BaseException | None = None
    for attempt in range(1, retries + 1):
        try:
            return generate_one(base_url, api_key, model, mode, args, prompt,
                                output_dir, label, name_prefix)
        except GenError as exc:
            last = exc
            if not is_backoff_error(str(exc)) or attempt == retries:
                raise
            log(label, f"出错，{delay}s 后重试（{attempt}/{retries - 1}）...")
            time.sleep(delay)
            delay = min(delay * 2, 60)
    raise last  # pragma: no cover


# ── 批量模式 ──────────────────────────────────────────────

JOB_FIELDS = ("size", "resolution", "quality", "n", "image", "format")


def _resolve_path(value: str, base_dir: Path) -> str:
    path = Path(value)
    return str(path if path.is_absolute() else base_dir / path)


def load_batch(manifest_path: Path, args: argparse.Namespace) -> tuple[Path, list[dict[str, Any]]]:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except OSError as exc:
        fail(f"无法读取批量清单：{exc}")
    except json.JSONDecodeError as exc:
        fail(f"批量清单不是有效 JSON：{exc}")
    raw_jobs = manifest.get("jobs") if isinstance(manifest, dict) else None
    if not isinstance(raw_jobs, list) or not raw_jobs:
        fail("批量清单必须是 JSON 对象且包含非空 jobs 数组。")
    defaults = manifest.get("defaults") or {}
    if not isinstance(defaults, dict):
        fail("批量清单 defaults 应为对象。")

    # 清单内的相对路径（prompt_file / image / output_dir）都相对清单文件所在目录
    base_dir = manifest_path.resolve().parent
    output_dir = Path(manifest.get("output_dir") or args.output_dir)
    if not output_dir.is_absolute():
        output_dir = base_dir / output_dir

    jobs: list[dict[str, Any]] = []
    seen_slots: set[str] = set()
    for index, raw in enumerate(raw_jobs, start=1):
        if not isinstance(raw, dict):
            fail(f"jobs[{index}] 应为对象。")
        slot = str(raw.get("slot") or f"job{index:02d}")
        if slot.lower() in seen_slots:
            fail(f"jobs 中槽位重复：{slot}")
        seen_slots.add(slot.lower())

        if raw.get("prompt"):
            prompt = str(raw["prompt"]).strip()
        elif raw.get("prompt_file"):
            prompt = read_prompt_text(Path(_resolve_path(str(raw["prompt_file"]), base_dir)))
        else:
            fail(f"槽位 {slot} 缺少 prompt 或 prompt_file。")
        if not prompt:
            fail(f"槽位 {slot} 的 prompt 为空。")

        job_args = argparse.Namespace(**vars(args))
        for key in JOB_FIELDS:
            for source in (defaults, raw):
                if key in source and source[key] is not None:
                    value = source[key]
                    if key == "image":
                        value = _resolve_path(str(value), base_dir)
                    setattr(job_args, key, value)
        if job_args.format not in VALID_FORMATS:
            fail(f"槽位 {slot} 的 format 非法：{job_args.format}（允许 {'/'.join(VALID_FORMATS)}）")
        if job_args.resolution not in VALID_RESOLUTIONS:
            fail(f"槽位 {slot} 的 resolution 非法：{job_args.resolution}（允许 {'/'.join(VALID_RESOLUTIONS)}）")
        try:
            job_args.n = int(job_args.n)
        except (TypeError, ValueError):
            fail(f"槽位 {slot} 的 n 应为整数。")
        jobs.append({"slot": slot, "prompt": prompt, "args": job_args})
    return output_dir, jobs


def run_batch(args: argparse.Namespace, base_url: str, api_key: str, model: str) -> None:
    output_dir, jobs = load_batch(Path(args.batch), args)
    mode = detect_mode(base_url, args.mode)
    log("batch", f"API 模式: {mode} | base_url={base_url} | model={model}")

    results: dict[str, tuple[str, Any]] = {}
    pending: list[dict[str, Any]] = []
    for job in jobs:
        slot = job["slot"]
        name_prefix = slot.lower()
        primary = output_dir / f"{name_prefix}.{job['args'].format}"
        if args.skip_existing and primary.exists():
            results[slot] = ("skip", [primary])
        else:
            pending.append(job)

    concurrency = max(1, args.concurrency)
    log("batch", f"共 {len(jobs)} 个槽位，起始并发 {concurrency}，输出目录 {output_dir}")

    def run_wave(wave: list[dict[str, Any]], workers: int) -> dict[str, tuple[str, Any]]:
        wave_results: dict[str, tuple[str, Any]] = {}

        def worker(job: dict[str, Any]) -> tuple[str, Any]:
            slot = job["slot"]
            try:
                paths = generate_one(
                    base_url, api_key, model, mode, job["args"],
                    job["prompt"], output_dir, slot, slot.lower(),
                )
                return "ok", paths
            except GenError as exc:
                return "fail", str(exc)
            except Exception as exc:
                return "fail", f"{type(exc).__name__}: {exc}"

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(worker, job): job["slot"] for job in wave}
            for future in concurrent.futures.as_completed(futures):
                slot = futures[future]
                wave_results[slot] = future.result()
                status, payload = wave_results[slot]
                if status == "ok":
                    log("batch", f"{slot} 完成")
                else:
                    log("batch", f"{slot} 失败：{payload}")
        return wave_results

    while pending:
        workers = min(concurrency, len(pending))
        log("batch", f"本轮 {len(pending)} 个槽位，并发 {workers}")
        wave_results = run_wave(pending, workers)
        next_pending: list[dict[str, Any]] = []
        hit_limit = False
        for job in pending:
            slot = job["slot"]
            status, payload = wave_results[slot]
            if status == "ok":
                results[slot] = (status, payload)
            elif is_backoff_error(str(payload)):
                hit_limit = True
                next_pending.append(job)
            else:
                results[slot] = (status, payload)
        if not next_pending:
            break
        if not hit_limit:
            for job in next_pending:
                results[job["slot"]] = wave_results[job["slot"]]
            break
        if concurrency <= 1:
            log("batch", "并发已降到 1 仍失败，停止回退")
            for job in next_pending:
                results[job["slot"]] = wave_results[job["slot"]]
            break
        concurrency = max(1, concurrency // 2)
        log("batch", f"报错回退，并发改为 {concurrency}，15s 后重试 {len(next_pending)} 个槽位")
        time.sleep(15)
        pending = next_pending

    counts = {"ok": 0, "skip": 0, "fail": 0}
    failed: list[str] = []
    print("批量结果：")
    for job in jobs:
        slot = job["slot"]
        status, payload = results[slot]
        counts[status] += 1
        if status == "ok":
            print(f"  {slot}  OK    " + " ".join(str(p) for p in payload))
        elif status == "skip":
            print(f"  {slot}  SKIP  已存在 {payload[0]}")
        else:
            failed.append(slot)
            print(f"  {slot}  FAIL  {payload}")
    print(f"成功 {counts['ok']} / 跳过 {counts['skip']} / 失败 {counts['fail']}，输出目录：{output_dir}")
    if failed:
        print(f"失败槽位：{'、'.join(failed)}。加 --skip-existing 重跑同一命令即可只补失败的槽位。", file=sys.stderr)
        raise SystemExit(1)


# ── CLI ──────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="统一图像生成脚本，自动兼容 OpenAI 同步 API 和 apimart.ai 异步 API；--batch 批量并发生成整套图。"
    )
    prompt_group = parser.add_mutually_exclusive_group()
    prompt_group.add_argument("--prompt", help="直接传入图片生成 Prompt。")
    prompt_group.add_argument("--prompt-file", help="从文本文件读取图片生成 Prompt。")
    prompt_group.add_argument("--batch", help="批量清单 JSON 路径（含 output_dir / defaults / jobs 数组），并发生成整套图，输出按槽位命名。")
    parser.add_argument("--concurrency", type=int, default=8, help="批量模式起始并发数，默认 8；429/超时自动 8→4→2→1 回退。")
    parser.add_argument("--skip-existing", action="store_true", help="批量模式跳过输出文件已存在的槽位，用于失败后重跑补齐。")
    parser.add_argument("--output-dir", default="generated-images", help="图片输出目录，默认 generated-images。")
    parser.add_argument("--env-file", help="指定 .env 配置文件；不指定时从当前目录向上查找（只认含 IMG_ 配置的），兜底 Skill 目录。")
    parser.add_argument("--mode", choices=("sync", "async"), help="API 模式。不指定时根据 base URL 自动检测（含 apimart → async，其他 → sync）。")
    parser.add_argument("--size", default="1:1", help="图片尺寸。异步模式用比例格式（1:1、16:9 等），同步模式用像素格式（1024x1024 等）。默认 1:1。")
    parser.add_argument("--resolution", default="1k", choices=VALID_RESOLUTIONS, help="异步模式分辨率档位，默认 1k。")
    parser.add_argument("--quality", choices=("low", "medium", "high"), help="同步模式图片质量参数。")
    parser.add_argument("--n", type=int, default=1, help="同步模式生成图片数量，默认 1。")
    parser.add_argument("--image", help="参考产品图片路径，传入以提升产品一致性。")
    parser.add_argument("--poll-interval", type=int, default=5, help="异步模式轮询间隔秒数，默认 5。")
    parser.add_argument("--timeout", type=int, help="异步模式轮询超时秒数；默认 1k/2k 为 180，4k 为 480。")
    parser.add_argument("--format", choices=VALID_FORMATS, default="png", help="图片保存格式，默认 png。")
    args = parser.parse_args()
    if not (args.prompt or args.prompt_file or args.batch):
        parser.error("必须提供 --prompt、--prompt-file 或 --batch 之一。")
    return args


def main() -> None:
    args = parse_args()
    try:
        env_file = Path(args.env_file) if args.env_file else find_default_env_file()
        load_env_file(env_file)
        base_url = require_config(ENV_BASE_URL).rstrip("/")
        model = require_config(ENV_MODEL)
        api_key = require_config(ENV_API_KEY)

        if args.batch:
            run_batch(args, base_url, api_key, model)
            return

        prompt = read_prompt(args)
        mode = detect_mode(base_url, args.mode)
        log(mode, f"API 模式: {mode} | base_url={base_url} | model={model}")
        paths = generate_with_retry(base_url, api_key, model, mode, args, prompt, Path(args.output_dir), mode)
        print("生成完成：")
        for path in paths:
            print(path)
    except GenError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
