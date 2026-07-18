# media-to-doc 项目级错误库 — ERRORS

> **目的**:追踪重复出现的错误模式(Pattern-Key),由 LE L4 进化层自动晋升。
> **晋升规则**:同一 Pattern-Key 在 `work/<course>/ERRORS.md` 中出现 ≥ 3 次时,自动写入本文件。
> **幂等**:已存在的 Pattern-Key 不会重复写入(参见 `_research/le_prototype/learnings.py:escalate_recurring_errors`)。
> **使用**:`PipelineLogger` 启动时读本文件,命中已知模式时注入警告或前置校验。

---

## 晋升条目(自动写入)

<!--
Phase 5 时 LE L4 落地后,自动追加形如:
## [Connection:ollama]
**First promoted**: 2026-07-18 09:30:00
**Occurrences**: 3 (across 5 shown)
**Threshold**: 3
**Auto-detected**: True
**Examples**:
- `course1/ERRORS.md`
- `course2/ERRORS.md`
- `course3/ERRORS.md`

**Recommended action**: review / write rule / patch code
-->

(Phase 0 尚无条目,Phase 5 LE L4 落地后由 `post_pipeline_hook` 自动追加)

---

## 手动录入条目(可选)

```markdown
## [Custom:keyword]

**First seen**: YYYY-MM-DD HH:MM:SS
**Occurrences**: N
**Description**: <错误描述>
**Root cause**: <根因>
**Fix**: <修复方法>
**Affected code**: <src/.../file.py:line>
```
