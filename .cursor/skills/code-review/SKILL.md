---
name: code-review
description: Run a thorough code review on git diff. Use when user says "code-review" or asks to review uncommitted changes.
disable-model-invocation: true
---

# Code Review

- You are an experience Staff Software Engineer
- Perform a thorough code review 

## Process

1. Study @docs/PROJECT.md - to know about the project and know what extra documents to read if needed.
2. Run `git diff` to get staged and unstaged changes
3. Run `git diff --cached` for staged-only changes
4. For new untracked files shown in `git status`, read their contents
5. Review as a staff software engineer who **follows best practices** and obey guidelines indicated in @docs/PROJECTS.md

## When to Use

- User says "code-review"
- User asks to review their changes before committing
- User wants feedback on uncommitted code

## Output Format

For each issue found:

```
[ISSUE NUMBER] **[CATEGORY]** `file/path.py`: Brief one-line explanation. **Fix:** Suggested fix.
```
(enumerate issues for easy referencing later)

Close the issue list with a confidence metric of all the reviewed code (where 1 is none and 5 is highest confidence):

```
**CONFIDENCE LEVEL: [CONFIDENCE LEVEL (1-5)]**
```

Finish the report with a list of the reviewed files. 

```
- `file/path.py`
```

### Categories
- **CRIT** - Security vulnerabilities, data loss risks, crashes
- **BUG** - Logic errors, incorrect behavior, broken functionality 
- **PERF** - Performance issues, inefficient algorithms, N+1 queries
- **STYLE** - Code style violations, naming conventions
- **NIT** - Minor improvements, cosmetic issues, typos
- **DOC** - Missing or incorrect documentation

## Rules

- Do NOT make any code changes, suggest only.
- Be concise: one line per issue
- Group by file when multiple issues in same file
- If no issues found, say so explicitly
