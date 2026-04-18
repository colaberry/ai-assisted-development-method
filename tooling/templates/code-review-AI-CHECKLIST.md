# AI-Assisted PR Review Checklist

Use this checklist on any PR where a coding agent (Claude Code, Copilot, Cursor, etc.) produced a material share of the diff. It targets failure modes that pattern-match as "AI code smell" — issues a human would usually catch but that pass review because the output *looks* correct.

**How to use it:**

1. Copy the checklist into the PR description (or reference it with "✅ AI-assist review: checklist-v1 completed by @reviewer").
2. Walk items top-to-bottom. Check each one or leave a note explaining why it doesn't apply.
3. If any item is a red flag, request changes — do **not** approve with caveats. The whole point of the checklist is to force the pause.
4. Items marked **[blocking]** are merge-blockers when they fail. Other items are strongly-worded defaults you may override with written justification.

---

## 1. Scope

- [ ] **[blocking] Diff matches the task's `Satisfies:` IDs.** No files changed outside what the IDs would require. If the diff touches code adjacent to the requirement "because it was messy," that's scope creep — either expand the task, open a new one, or revert the drift.
- [ ] **[blocking] No silent `[DEFERRED]` tasks.** Any task that wasn't finished is either complete (checked off), explicitly deferred in TASKS.md with a follow-up issue link, or visible in the PR description as "not done."
- [ ] **No dead code in the diff.** If a function, import, variable, or branch is added but never reached, delete it. Agents frequently hedge with unused helpers; the deletion is on you.

## 2. Correctness

- [ ] **Edge cases, not just the golden path.** Empty input, single-element input, duplicate input, `None`/`null`/`undefined`, unicode, timezone boundaries, off-by-one on loops, integer overflow where the language allows it. Tests exist for at least the ones that apply.
- [ ] **[blocking] Tests weren't modified to match the code.** If a test changed in this PR, the commit message explains *why the old assertion was wrong*. Use `state-check.py` to surface recently-modified test files if unsure.
- [ ] **[blocking] No invented APIs.** Every imported symbol, library method, CLI flag, config key, env variable, and type signature actually exists in the version pinned in lockfile/pyproject/package.json. Grep the vendor docs or `go doc` / `python -c 'import x; help(x.y)'` if you're not sure.
- [ ] **Concurrency claims are earned.** If the diff calls something "thread-safe," "atomic," "idempotent," or "race-free," there is either a test demonstrating it or a line of prose explaining the invariant that makes it true.

## 3. Error handling

- [ ] **No defensive coding for impossible states.** If a caller can only pass a non-null value (type system, framework guarantee, upstream validation), the function should not check for null. Agents love to add belt-and-suspenders guards that obscure real bugs.
- [ ] **Failures fail loudly.** `except: pass`, `catch { }`, swallowed promise rejections, ignored return codes — flag every one. If the error is genuinely ignorable, the code says *why* in one line.
- [ ] **Error messages name what failed, not what was attempted.** `"failed to parse config at line 42: unexpected indent"` beats `"error loading config"`.

## 4. Comments and documentation

- [ ] **Comments describe *why*, not *what*.** Any comment that re-narrates the next line of code should be deleted. Agents over-comment; leave the non-obvious invariant and cut the rest.
- [ ] **No comments that reference the agent or this task.** `# Added per user request`, `# Handles the case Claude identified`, `# Fix for the bug in the prompt` — all of these rot within a week. If the insight is load-bearing, put it in a commit message or design doc.
- [ ] **No plausible-but-wrong docstrings.** Read the docstring and the function body independently. If the docstring could plausibly describe any function in this codebase, it's probably hallucinated. Rewrite it to describe *this* function.

## 5. Security

- [ ] **User input never reaches a shell, SQL query, HTML body, template, or eval-like construct unescaped.** Parameterized queries, templating engines with autoescape, `shlex.quote`, framework-provided sanitizers — one of these is in the path.
- [ ] **No hardcoded secrets, keys, tokens, or credentials.** Not even in tests, not even in comments, not even "temporarily."
- [ ] **No new outbound network calls the agent added on its own initiative.** Every `requests.get`, `fetch`, `subprocess` that wasn't in the task description gets explicit justification.

## 6. Tests

- [ ] **New behavior has new tests.** Not "the build passes" — actual test function(s) asserting the behavior introduced by the diff.
- [ ] **Test names describe the behavior under test, not the implementation.** `test_returns_empty_list_when_input_is_empty` beats `test_parse_function_branch_3`.
- [ ] **At least one test in categories D (adversarial/security) or E (property/mutation) for any code on a trust boundary or arithmetic hot path.** See the method's test matrix.
- [ ] **No `@skip`, `xfail`, or `.only()` left in the diff** unless the skip has a follow-up issue linked in the comment.

## 7. Fit with existing code

- [ ] **Style matches the file, not the agent's defaults.** Indent, quote style, import ordering, naming conventions. If the surrounding file uses `snake_case` and the agent produced `camelCase`, fix it — don't let the codebase fork.
- [ ] **No duplicated helpers.** If the agent reimplemented `debounce`, `uniq`, `chunk`, a retry wrapper, or a timestamp-formatter that already exists in the repo, use the existing one. Grep before accepting.
- [ ] **No premature abstractions.** One caller ≠ generic helper. Three similar lines are fine; a `BaseGenericFactoryProvider<T>` for a two-call use case is not.

## 8. Commit hygiene

- [ ] **Commit messages explain intent.** "Add auth middleware" is worse than "Add auth middleware to satisfy SOW-§3.2 — blocks unauthenticated /admin/* access, returns 401 with Retry-After on rate limit."
- [ ] **No commits with "claude" / "copilot" / agent-branded messages** that leak into the shared history. Re-author or squash before merge; the tool is an implementation detail.

---

**Origin.** This checklist is maintained at [tooling/templates/code-review-AI-CHECKLIST.md](.). Propose additions via PR with a concrete failure-mode example — items not tied to a real failure get cut in the next pruning pass.
