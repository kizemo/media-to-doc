# Installation Guide

> 完整安装指引。所有平台先看 [§ 前置条件](#前置条件),然后选你的 OS 章节。

## 目录

- [前置条件](#前置条件)
- [Windows 11 (主要支持)](#windows-11-主要支持)
- [macOS](#macos)
- [Linux (Ubuntu 22.04+)](#linux-ubuntu-2204)
- [CUDA / GPU 加速 (可选)](#cuda--gpu-加速-可选)
- [中国大陆网络提示](#中国大陆网络提示)
- [Ollama 模型部署](#ollama-模型部署)
- [Claude Desktop MCP 集成](#claude-desktop-mcp-集成)
- [验证安装](#验证安装)
- [故障排除](#故障排除)

---

## 前置条件

| 工具 | 版本 | 用途 |
|---|---|---|
| **Python** | 3.11 / 3.12 / 3.13 / 3.14 | 运行时 |
| **uv** | 0.11+ | 包管理 + 项目管理 |
| **ffmpeg** | 4.0+ | 音视频抽音 + 关键帧 |

### 安装 Python + uv + ffmpeg

**Windows (winget)**:

```powershell
winget install Python.Python.3.12
winget install astral-sh.uv
winget install Gyan.FFmpeg
```

**macOS (Homebrew)**:

```bash
brew install python@3.12 uv ffmpeg
```

**Ubuntu 22.04+**:

```bash
sudo apt update
sudo apt install python3.12 python3.12-venv ffmpeg
# uv 见 https://docs.astral.sh/uv/
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## Windows 11 (主要支持)

这是官方支持的参考平台,RTX 3090 用户推荐配置。

```powershell
# 1. 克隆仓库
git clone https://github.com/media-to-doc/media-to-doc.git
cd media-to-doc

# 2. 装核心依赖(轻量,~150MB)
uv sync

# 3. 装全部功能依赖(可选,~5GB)
#    包含 faster-whisper / scenedetect / rapidocr / diffusers / anthropic / openai
uv sync --all-extras

# 4. 启动 Python REPL 试一下
uv run python -c "from media_to_doc import run_pipeline; print('OK')"
```

### 卸载

```powershell
# 干净卸(uninstall all deps + .venv)
uv cache clean
Remove-Item -Recurse -Force .venv, dist
```

---

## macOS

Intel + Apple Silicon 都支持。Apple Silicon(M1/M2/M3)上 torch 走 MPS 加速。

```bash
git clone https://github.com/media-to-doc/media-to-doc.git
cd media-to-doc
uv sync --all-extras
```

> **注意**:faster-whisper + MPS 在 Apple Silicon 上需要 `pyproject.toml` 加 `--config-settings torch.backends.mps.enabled=true`,默认 CPU 跑。

---

## Linux (Ubuntu 22.04+)

```bash
git clone https://github.com/media-to-doc/media-to-doc.git
cd media-to-doc
uv sync --all-extras
```

**faster-whisper 需要 CUDA**:

```bash
# 装 CUDA toolkit + cuDNN(版本见 PyTorch 官方矩阵)
# 例:CUDA 12.1
sudo apt install nvidia-cuda-toolkit
uv sync --all-extras
```

---

## CUDA / GPU 加速 (可选)

`media-to-doc` 默认 **CPU 模式** 跑(W5/W10-A 实测:107min 视频 CPU 跑 3h57min)。

装 PyTorch CUDA 后,faster-whisper + diffusers 用 GPU 加速(预估 5-10x):

### 步骤

```bash
# 1. 装 NVIDIA 驱动(Linux)
sudo apt install nvidia-driver-545

# 2. 装 CUDA 版 PyTorch
uv pip install torch --index-url https://download.pytorch.org/whl/cu121

# 3. 验证
uv run python -c "import torch; print('cuda:', torch.cuda.is_available())"
```

### 版本兼容矩阵

| CUDA Toolkit | PyTorch | ctranslate2 |
|---|---|---|
| 12.1 | 2.3.0+ | 4.0+ |
| 11.8 | 2.0+ | 3.20+ |

---

## 中国大陆网络提示

`media-to-doc` 默认从 HuggingFace 拉模型。中国大陆用户推荐设:

```bash
export HF_ENDPOINT=https://hf-mirror.com
export HF_HUB_DISABLE_XET=1
```

### 强制 unset 公司 VPN 代理

公司 VPN / 代理会拦 HF,加上下面的 unset 才稳(W5/W10-A 真实场景 fix):

```bash
env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY \
    -u http_proxy -u https_proxy -u all_proxy \
    HF_ENDPOINT=https://hf-mirror.com \
    HF_HUB_DISABLE_XET=1 \
    uv run mtd run ...
```

PowerShell 等价:

```powershell
$env:HTTP_PROXY = $null
$env:HTTPS_PROXY = $null
$env:HF_ENDPOINT = "https://hf-mirror.com"
$env:HF_HUB_DISABLE_XET = "1"
uv run mtd run ...
```

---

## Ollama 模型部署

`media-to-doc` 默认 LLM provider 是 Ollama。装 Ollama 后跑一条命令:

```bash
# 装 Ollama
# Linux / macOS:https://ollama.com/download
# Windows:同上,或 winget install Ollama.Ollama

# 拉默认模型(qwen3:14b,~9GB)
ollama pull qwen3:14b

# 跑一条流水线测试
mkdir -p inbox/test
echo "sample" > inbox/test/dummy.txt
uv run mtd run inbox/test/ --llm ollama --llm-model qwen3:14b --imagegen skip
```

### 替代 LLM 选项

| Provider | 装 SDK | 配 env |
|---|---|---|
| **Ollama** | `uv pip install ollama` | 默认本地 |
| **Anthropic** | `uv pip install anthropic` | `export ANTHROPIC_API_KEY=sk-ant-...` |
| **OpenAI-compatible** | `uv pip install openai` | `export OPENAI_API_KEY=sk-...` + `export OPENAI_BASE_URL=https://api.deepseek.com/v1`(DeepSeek 例) |

---

## Claude Desktop MCP 集成

`media-to-doc` 自带 MCP server(8 工具,详情见 `docs/MCP_INTEGRATION.md`)。

### Windows 11 配置

编辑 `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "media-to-doc": {
      "command": "uv",
      "args": ["--project", "F:/soft/00selfmade/media-to-doc", "run", "mtd-mcp"]
    }
  }
}
```

### macOS 配置

`~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "media-to-doc": {
      "command": "uv",
      "args": ["--project", "/path/to/media-to-doc", "run", "mtd-mcp"]
    }
  }
}
```

### 验证

重启 Claude Desktop,新对话里问 "你能调用 media-to-doc 的工具吗?"。
8 个工具(`list_courses` / `run_pipeline` / `resume_pipeline` / `check_status` / `list_outputs` / `read_lecture` / `get_run_metrics` / `list_runs`)应该出现在工具列表里。

---

## 验证安装

```bash
# 1. CLI 可执行
uv run mtd --version
# 期望:media-to-doc 1.0.0

# 2. 测试套件全过(529 个,2-5 分钟)
uv run pytest
# 期望:529 passed in <5min

# 3. 系统诊断
uv run mtd doctor
# 检查 ffmpeg / faster-whisper / Ollama / GPU 等依赖

# 4. 跑真视频(可选,~10 分钟)
uv run mtd run inbox/test_video/ --imagegen skip --stop-after chapters
# 应该 ~1 分钟内 chapters stage 完成
```

---

## 故障排除

### Q: faster-whisper 下载模型卡住

A: `ProxyError: HTTP 502`。中国大陆用户没 unset VPN proxy + HF_ENDPOINT 没设。详见 [§ 中国大陆网络提示](#中国大陆网络提示)。

### Q: `faster-whisper` 报 CUDA unavailable

A: 默认装的是 CPU 版。装 PyTorch CUDA 后重装:
```bash
uv pip install --force-reinstall torch --index-url https://download.pytorch.org/whl/cu121
uv pip install --force-reinstall ctranslate2
```

### Q: Ollama `qwen3:14b` 报 context overflow

A: `OLLAMA_NUM_CTX` 默认太小。建议设:
```bash
# Linux / macOS
export OLLAMA_NUM_CTX=32768

# Windows PowerShell
$env:OLLAMA_NUM_CTX = 32768

# 然后跑 mtd run(media-to-doc 默认 num_ctx=65536,内部已设)
```

### Q: 中文转写乱码

A: faster-whisper 默认 multilingual,中文用 `large-v3` 模型:
```bash
# 默认 large-v3 已支持中文,无需特别
# 如有问题,设环境变量
export WHISPER_MODEL=large-v3
export WHISPER_LANGUAGE=zh
```

### Q: 多视频目录,CLI 选错视频

A: 用 W10-A NTFS hardlink 单文件 inbox 技术:

```python
# 跨平台通用
import os
os.makedirs("_w11b_inbox", exist_ok=True)
os.link("我的培训.mp4", "_w11b_inbox/我的培训.mp4")
# 跑完 rm -rf _w11b_inbox/
```

### Q: gatekeeper FAIL 但 verify PASS

A: 这是 W10-A 之前的老 bug。W11-A (`d2b39d3`) 已修。装 1.0.0 后应该没这问题。如果还出现:

```bash
uv run python scripts/_w11a_consistency.py <work_dir>
```

退出码 2 = 不一致(BUG 回归),请贴 issue。

### Q: 重依赖缓存太大

A: 默认 `~/.cache/huggingface` + `~/.cache/uv`。清理:

```bash
uv cache clean --all
rm -rf ~/.cache/huggingface
```

### Q: 如何从源码升级到新版本

```bash
cd media-to-doc
git pull origin release/v1.0
uv sync --all-extras
uv run pytest  # 验证
```

---

## 下一步

- 看 [README.md](../README.md) 的 5 分钟快速开始
- 看 [docs/MCP_INTEGRATION.md](MCP_INTEGRATION.md) 配 Claude Desktop
- 看 [CLAUDE.md](../CLAUDE.md) 的项目指引 + 设计约束

需要帮助请开 issue 或看 `task.md` / `PRD.md` / `ROADMAP.md`。
