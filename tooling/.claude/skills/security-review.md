# /security-review — Manual security review for the current sprint

This skill runs the judgment layer of sprint security. The Semgrep CI gate catches mechanically-detectable issues; this skill catches the design-level ones — threat-model gaps, auth-flow changes, data-handling changes, new integrations, new surfaces. Output is a committed `sprints/vN/SECURITY-REVIEW.md` artifact that `sprint_close.py` structurally requires when the PRD declared `` `/security-review` required: Yes ``.

`sprint_close.py` is the authority. If the PRD flag is `Yes` and the artifact is missing or marked `Decision: blocked`, the sprint refuses to lock. That refusal is what makes Method rule 6 real.

## When to invoke

- The PRD for the active sprint has `` `/security-review` required: **Yes** ``.
- Enough implementation work has landed that the security review has something concrete to examine — typically immediately before `/sprint-close`, or after the last security-touching `/dev` session.
- The designated reviewer is available (this is a human-in-the-loop skill; Claude can draft the artifact but the reviewer's name goes on the `Decision:` line).

Do not invoke `/security-review` to:
- Rubber-stamp a sprint because CI is green. The Semgrep gate and this review are different layers; both are required when the PRD says so.
- Satisfy the gate by writing an empty artifact. `sprint_close.py` parses `Decision:` and requires `passed`, `n/a`, or `blocked` — it rejects malformed artifacts.
- Skip the review on a sprint the PRD marked `No` by flipping the flag post-hoc. If the scope changed, edit the PRD explicitly and run the review.

## Preconditions

- `sprints/vN/PRD.md` exists and has the security-scope line set to `Yes`.
- Tests are green; the review runs against a landed, coherent codebase rather than mid-flight changes.

Refuse to proceed if:
- **PRD flag is `No` or unset.** If the reviewer believes security review is warranted despite the PRD, update the PRD first — silent flag flipping loses the audit trail.
- **No sprint directory.** `/security-review` scopes itself to a specific sprint; there is no "repo-wide review" mode.

## What this skill does

1. **Reads the PRD's security scope line and the Architectural/Security sections.** Summarizes what the sprint declared in scope.
2. **Enumerates security-touching changes since the last lock.** `git log sprints/v{N-1}/.lock..HEAD` + parses the sprint's TASKS.md for tasks whose `Files:` touch `src/auth/`, `src/integrations/`, database migrations, API surface, or any path the project's CLAUDE.md security section flagged.
3. **Runs a threat-model pass on the enumerated changes.** Walks the reviewer through:
   - Authentication / authorization surface — new endpoints, new middleware, new roles.
   - Data handling — new PII, new logs, new persistence, new exports.
   - Integrations — new outbound calls, new secrets, new dependencies.
   - Input surfaces — new user input paths, new file uploads, new parsers.
   - Supply chain — new or updated dependencies; any unpinned or typosquat-adjacent names.
   - Secrets & config — any new secret referenced in code; any secret material that may have landed in logs, CLAUDE.md, or committed fixtures.
4. **Checks the failures log.** `docs/failures/` entries tagged `security` that haven't been closed out should show up as either already-addressed or explicitly accepted this sprint.
5. **Drafts `sprints/vN/SECURITY-REVIEW.md`** from `tooling/templates/security-review-TEMPLATE.md`. Fills in scope, findings, suppressions. Leaves `Reviewer:` and `Decision:` for the reviewer to own on commit.
6. **Surfaces the blocker decision clearly.** If the draft contains findings that the reviewer judges blocking, the `Decision:` line goes to `blocked` and the draft names exactly what must change. The reviewer commits that explicitly — `sprint_close.py` will refuse to lock.
7. **On passed clean reviews,** the `Findings` section reads `- None identified.` — that one-line form is the structural signal that the review ran and found nothing, not that the review was skipped.

## What this skill does NOT do

- **Does not set `Decision: passed` on the reviewer's behalf.** The `Decision:` line is reviewer-authored. The skill can draft everything else; a human commits the decision.
- **Does not flip the PRD flag.** If the sprint actually had no security-relevant changes, the flag was set incorrectly; fix the PRD and leave the `n/a` decision path for sprints where the flag was right but nothing landed to review.
- **Does not suppress findings without a registered entry.** Any new `# nosemgrep` added this sprint must be paired with a `docs/security/suppressions.md` entry. Unregistered suppressions are a blocker, not a passed finding.
- **Does not skip the review because "the code didn't really touch security."** That judgment is the review itself; running it and writing `- None identified.` is the correct output when the judgment is true.

## Handling the common refusal modes

- **`sprint_close.py` refuses with "SECURITY-REVIEW.md is missing".** The PRD says `Yes` but no artifact exists. Run `/security-review` and commit the result.
- **`sprint_close.py` refuses with "missing field(s): Decision".** The artifact exists but the `Decision:` line wasn't filled in. That's the reviewer's line; get it signed.
- **`sprint_close.py` refuses with "Decision: blocked".** This is working as intended. Resolve the blocker, re-run `/security-review`, commit the updated artifact with `Decision: passed`.
- **Reviewer disagrees with a finding Claude drafted.** Edit the draft; the skill is a starting point, not an authority. What ships is whatever the reviewer commits.

## Interaction with other skills

- `/sprint-close` structurally requires this artifact when the PRD says so. This skill produces it.
- `/incident` runs the failures-log loop. A security incident becomes a failures-log entry; subsequent `/security-review` passes should check that entry's prevention rule is in place.
- `/dev` produces the code that this review examines. A `/dev` session that touches new security surface should flag that in its session log so this review has a pointer.

## Deliverables at the end of `/security-review`

- `sprints/vN/SECURITY-REVIEW.md` committed, with:
  - `Reviewer:` with a real name.
  - `Date:` with today's date in `YYYY-MM-DD`.
  - `Decision:` one of `passed`, `n/a`, or `blocked`.
  - Scope, findings (or `- None identified.`), and suppressions sections non-stub.
- Any new failures-log entries created for issues found.
- Any new suppressions registered in `docs/security/suppressions.md`.
