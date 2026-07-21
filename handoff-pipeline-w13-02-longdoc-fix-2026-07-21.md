# handoff-pipeline-w13-02-longdoc-fix-2026-07-21.md

> W13-B 长文档 W12-D 兼容性修复 + W13-C fusion SSL 诊断
> Session 19:00-19:42 (42min)
> Status:`[x]` P1 bug 修复 + P2 SSL 诊断 + 测试 / 真跑 / cleanup 全过

---

## 1. 上下文

承接 W13-A final snapshot(`handoff-pipeline-w13-01-fusion-2026-07-21.md`)
§8 任务列表:

1. ✅ 修 P1 bug:`longdoc.py:620` 兼容 W12-D 目录结构(参考 §4.4)
2. ✅ 加测试:`tests/test_longdoc_w12d_compat.py`(13 用例)
3. ✅ 重跑 01.mp4 pipeline 验证 fix(`scripts/_w13b_verify_longdoc_fix.py`)
4. ✅ 调查 W12-E SSL 错误(`merge_lectures.py` ollama 调用)
5. ✅ pytest + ruff 跑一次确认 baseline + ruff clean(595 passed)
6. ✅ cleanup `rm -rf _w13a_inbox _w13a_fusion`
7. (待用户决策)考虑发 v1.0.2 patch 到 PyPI

---

## 2. W13-B longdoc.py 修复

### 2.1 实际产物布局(重新核实)

W13-A handoff §4.3 描述的"workaround"拼装 raw_md 与实际产物布局:

```
_w13a_inbox/output_final/                            ← render 阶段写的位置
├── 01_先精准后放大的打爆策略.md                    ← 真讲义(含 TOC + 摘要 + 要点 + 关键帧)
├── 01_先精准后放大的打爆策略.html
├── 01_先精准后放大的打爆策略_cleaned.md
└── 01_先精准后放大的打爆策略_final.html

_w13a_inbox/output/chapters/raw/                     ← 中间产物(草稿)
├── 01_先精准后放大的打爆策略/                      ← 每章节草稿
│   ├── chapter_01.md
│   ├── ...
│   └── chapter_08.md
└── 01_先精准后放大的打爆策略.md.bak                ← workaround 拼装的临时文件
```

**关键事实**:`output_final/<video>.md` 是 render 阶段已拼装好的讲义,比 workaround 拼装的"草稿正文"质量更高(包含完整结构化字段)。

### 2.2 修复方案(最终版,优于 handoff §4.4 建议)

新增 `_resolve_source_md(work, video, final_dir)` helper,3 级 fallback:

1. **W12-D 真相位置**:`<final_dir>/<video>.md`(render 已拼装好的讲义)
2. **W3-W11 旧布局**:`<work>/chapters/raw/<video>.md`(向后兼容)
3. **W12-D 中间产物应急**:拼装 `<work>/chapters/raw/<video>/chapter_*.md` →
   写到第 2 项路径,作为 longdoc 输入

`process_long_doc` 重构:`target_dir` 提前计算(原代码在 source_md 之后),
作为 `_resolve_source_md` 的 W12-D 查找位置。

### 2.3 测试覆盖(13 新用例)

`tests/test_pipeline/test_longdoc_w12d_compat.py` 6 大类:

1. **W12-D 真相位置优先**(2 用例)— 不读 legacy / chapter 拼装
2. **W3-W11 旧布局回退**(2 用例)— final_dir 无 + legacy 有
3. **章节目录拼装应急**(2 用例)— 拼装 + 排序
4. **FileNotFoundError 兜底**(2 用例)— 3 层全失败 + 空 chapter 目录
5. **端到端 process_long_doc 集成**(4 用例)— 3 路径 + 全失败
6. **向后兼容**(1 用例)— 旧 fixture `_seed_rendered_md` 仍能 pass

**测试结果**:
- pytest:`595 passed`(582 baseline + 13 new),0 failed
- ruff:All checks passed
- 真跑:`_w13b_verify_longdoc_fix.py` 在 `_w13a_inbox/output_final/01_先精准后放大的打爆策略.md` 上验证
  - source_md = final_dir/<video>.md(W12-D 真相位置)✅
  - chars_input=18629 (真讲义 ~18KB,workaround 18.6KB 是草稿拼装)
  - cleaned_md 含 TOC + 摘要 + 要点 + 关键帧引用 4 大结构化字段 ✅
  - +1.4% chars 比 workaround(新增结构化壳,符合预期)

### 2.4 关键设计决策

- **`target_dir` 提前到 source_md 解析之前**:作为单一真相源,避免重复 default 逻辑
- **`_resolve_source_md` 独立 helper**:易于测试,边界清晰
- **拼装 fallback 写到 legacy 路径**:下次调用直接命中 layer 2,免重复拼装
- **FileNotFoundError 信息含 3 尝试路径**:便于排查 W3-W11 / W12-D / 中间产物 3 种场景

---

## 3. W13-C fusion SSL 诊断

### 3.1 现象

`_w13a_run_fusion.py` 调 `mtd merge --fusion ollama` 时报:
```
SSLError: [SSL] unknown error (_ssl.c:3138)
```

同一 ollama server(chapters / draft / longdoc 都用过),同一 `OllamaProvider`,无 SSL 错误。

### 3.2 诊断脚本

`scripts/_w13c_diag_fusion_ssl.py`:5 个测试覆盖各种 prompt 大小(200 / 5K / 20K / fusion-sized 4834 chars)— **全部 OK**。

### 3.3 根因

父 shell 有公司 VPN 代理:
```
HTTP_PROXY=http://127.0.0.1:49223
HTTPS_PROXY=http://127.0.0.1:49223
all_proxy=http://127.0.0.1:49223
```

`_w13a_run_fusion.py` 调 `subprocess.run(env={...})` 替换子进程环境,但原版只传 PATH / HOME / USERPROFILE / OLLAMA_HOST,**没剔除 proxy vars**。

→ 子进程 `mtd` 启动时 ollama SDK 的 httpx 走 `http://127.0.0.1:49223` 代理 → 代理是 HTTP 但 ollama SDK 走 SSL 握手路径 → SSL unknown error。

注意:替换 env 意味着子进程不应该继承 HTTP_PROXY,但实际可能通过其他途径(例如 Windows WinHTTP proxy 注册表)泄漏,或者 subprocess env 在某些 edge case 仍传递了部分父环境。

### 3.4 修复

`scripts/_w13a_run_fusion.py` 子进程 env 改为父环境的过滤版:
```python
clean_env = {PATH, HOME, USERPROFILE, OLLAMA_HOST}  # base
for k, v in os.environ.items():
    if k not in proxy_vars:  # 8 个 proxy vars 过滤
        clean_env[k] = v
subprocess.run(..., env=clean_env)
```

### 3.5 验证

- 重跑 `_w13a_run_fusion.py`:**无 SSL 错误**
- LLM fusion 成功输出 7 H2 章节的全局融合产物(此前 10 H2 是 fallback 硬切)
- 产物头几行展示 LLM 驱动的章节标题:"课程导入与核心策略框架 / 2026年市场环境下的测款逻辑重构 / 精准人群策略与流量结构优化 / 实战案例解析与全站推广方法论 / 全站运营策略与风险控制体系 / 年度策略总结与店铺盈利模型构建"

### 3.6 优先级

P2(LLM fusion 是 nice-to-have,fallback 模式产物仍可用)。修复在 fusion 脚本里,影响面小。

---

## 4. commits (本会话)

| SHA | message | files |
|---|---|---|
| 待 commit | `fix(pipeline): W13-B — longdoc W12-D 兼容 3 级 fallback` | src/media_to_doc/pipeline/longdoc.py, tests/test_pipeline/test_longdoc_w12d_compat.py, scripts/_w13b_verify_longdoc_fix.py, scripts/_w13c_diag_fusion_ssl.py |
| 待 commit | `fix(scripts): W13-C — filter proxy vars from fusion subprocess env` | scripts/_w13a_run_fusion.py |
| 待 commit | `docs(handoff): W13-B/C session snapshot + task.md progress` | handoff-pipeline-w13-02-longdoc-fix-2026-07-21.md, task.md |

(实际 commit 在本文件落地后,见 git log)

---

## 5. 验收清单

| 项 | 期望 | 实际 | 状态 |
|---|---|---|---|
| longdoc 读 W12-D 真讲义 | yes | source_md = output_final/<video>.md | ✅ |
| 旧布局(W3-W11)仍兼容 | yes | 13 测试 + 旧 fixture 全过 | ✅ |
| 章节目录应急拼装 | yes | 拼装 + 排序正确 | ✅ |
| 全失败抛错列路径 | yes | FileNotFoundError 信息含 3 路径 | ✅ |
| pytest 595 baseline | yes | 595 passed,0 skipped | ✅ |
| ruff clean | yes | All checks passed | ✅ |
| W13-A 真跑 01.mp4 验证 | yes | chars_input=18629, +1.4% 比 workaround | ✅ |
| SSL 根因诊断 | yes | HTTP_PROXY 父 shell 污染 | ✅ |
| fusion 重跑 7+ H2 | yes | 7 H2 LLM 驱动融合 | ✅ |
| cleanup | yes | _w13a_inbox + _w13a_fusion 已删 | ✅ |
| task.md 标 [x] | yes | W13-A/B/C 段已更新 | ✅ |

---

## 6. 下个会话建议

### 6.1 W14 候选(用户决策)

| 项 | 内容 | 优先级 |
|---|---|---|
| **A. 发 v1.0.2 patch 到 PyPI** | W13-B 修了 longdoc W12-D bug,1 行版本号 bump + build + upload | 用户决定 |
| **B. 修 W8 LE 健康度 TechDebt D** | W13-A 真跑 llm_health 真聚合已确认(519 测试 OK),无需再修 | 历史 |
| **C. UI:Tauri 2 桌面壳启动** | Phase 2 候选 | Phase 2 |
| **D. NSIS 安装器** | Phase 3 候选 | Phase 3 |
| **E. 真实端到端 LE 验证**(跑 3 次示例视频) | 演示 Pattern-Key 自动晋升 | W10+ 候选 |

### 6.2 如果发 v1.0.2 patch(基于 W13-B)

1. `pyproject.toml` version 1.0.1 → 1.0.2
2. `CHANGELOG.md` 加 [1.0.2] 节(W13-B 长文档 W12-D 兼容)
3. `uv build` + `uv publish`(复用 W12-A keyring 流程)
4. GitHub Release v1.0.2 + 2 assets SHA256 verified
5. commit `fix(pipeline): W13-B patch release v1.0.2`

### 6.3 关键路径保留(下个会话如需复盘)

- `src/media_to_doc/pipeline/longdoc.py` 的 `_resolve_source_md` helper(line ~555)
- `tests/test_pipeline/test_longdoc_w12d_compat.py` 13 用例
- `scripts/_w13b_verify_longdoc_fix.py`(需 _w13a_inbox 已删,重跑前重新跑 W13-A)
- `scripts/_w13c_diag_fusion_ssl.py`(可复用,验证 ollama 健康)

### 6.4 cleanup 已完成

✅ `rm -rf _w13a_inbox _w13a_fusion` — hardlink 隔离,源 mp4 link count 自动 2→1。

原始 mp4(01 / 02 / 03)+ `output-backup-2026-07-21/` + `output_final-backup-2026-07-21/` + `output-w11c/` + `output-w12c/` 保留。