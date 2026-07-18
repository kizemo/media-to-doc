"""media_to_doc 路径常量。

定义 workspace / inbox / work / config / logs / models 等默认路径。
所有路径基于 ``WORKSPACE_ROOT``,可在 cli / 配置 / 环境变量覆盖。

参考:ROADMAP §3.1 Phase 0 + TDD §2.1 总架构 + TDD §4.4.2 文件结构。
"""

from __future__ import annotations

import os
from pathlib import Path

# ─────────────────────────────────────────────────────────────
# 环境变量(用户可覆盖)
# ─────────────────────────────────────────────────────────────

ENV_WORKSPACE = "MEDIA_TO_DOC_WORKSPACE"
ENV_CONFIG_DIR = "MEDIA_TO_DOC_CONFIG_DIR"


# ─────────────────────────────────────────────────────────────
# 路径解析函数
# ─────────────────────────────────────────────────────────────


def _resolve_workspace_root() -> Path:
  """解析 workspace 根目录。

  优先级:
  1. 环境变量 ``MEDIA_TO_DOC_WORKSPACE``
  2. 当前目录下的 ``./workspace``
  3. 用户主目录 ``~/media-to-doc-workspace``
  """
  env_value = os.environ.get(ENV_WORKSPACE)
  if env_value:
    return Path(env_value).expanduser().resolve()

  cwd_workspace = Path.cwd() / "workspace"
  if cwd_workspace.exists():
    return cwd_workspace.resolve()

  return (Path.home() / "media-to-doc-workspace").resolve()


def _resolve_config_dir() -> Path:
  """解析配置目录(``%APPDATA%/media-to-doc`` 或环境变量)。"""
  env_value = os.environ.get(ENV_CONFIG_DIR)
  if env_value:
    return Path(env_value).expanduser().resolve()

  if os.name == "nt":
    appdata = os.environ.get("APPDATA")
    if appdata:
      return Path(appdata) / "media-to-doc"

  xdg_config = os.environ.get("XDG_CONFIG_HOME")
  if xdg_config:
    return Path(xdg_config) / "media-to-doc"

  return Path.home() / ".config" / "media-to-doc"


# ─────────────────────────────────────────────────────────────
# 全局路径常量(只读,模块加载时解析)
# ─────────────────────────────────────────────────────────────

WORKSPACE_ROOT: Path = _resolve_workspace_root()
INBOX_DIR: Path = WORKSPACE_ROOT / "inbox"
WORK_DIR: Path = WORKSPACE_ROOT / "work"

CONFIG_DIR: Path = _resolve_config_dir()
CONFIG_FILE: Path = CONFIG_DIR / "config.yaml"

# 日志 / 模型 / 学习库(项目级)
LOGS_DIR: Path = CONFIG_DIR / "logs"
MODELS_CACHE_DIR: Path = CONFIG_DIR / "cache"

# 学习库(项目根目录的 ``.learnings/``,与 ``workspace/`` 分离,
# 跟踪 LEARNINGS.md / ERRORS.md 跨 run 的累积)
LEARNINGS_DIR_NAME = ".learnings"


def project_root() -> Path:
  """media_to_doc 项目根目录(即 ``pyproject.toml`` 所在目录)。

  从 ``__file__`` 向上查找 ``pyproject.toml``。
  """
  current = Path(__file__).resolve().parent
  for parent in [current, *current.parents]:
    if (parent / "pyproject.toml").exists():
      return parent
  return current.parent


# 计算型常量(模块加载时一次性解析)
LEARNINGS_DIR: Path = project_root() / LEARNINGS_DIR_NAME


def ensure_dirs() -> None:
  """确保所有默认目录存在(惰性创建,幂等)。"""
  for path in [WORKSPACE_ROOT, INBOX_DIR, WORK_DIR, CONFIG_DIR, LOGS_DIR, MODELS_CACHE_DIR]:
    path.mkdir(parents=True, exist_ok=True)


__all__ = [
  "ENV_WORKSPACE",
  "ENV_CONFIG_DIR",
  "WORKSPACE_ROOT",
  "INBOX_DIR",
  "WORK_DIR",
  "CONFIG_DIR",
  "CONFIG_FILE",
  "LOGS_DIR",
  "MODELS_CACHE_DIR",
  "LEARNINGS_DIR_NAME",
  "LEARNINGS_DIR",
  "project_root",
  "ensure_dirs",
]
