# How to work on two Git branches at once (Git worktrees + Cursor)

This guide describes how to work on **two branches in parallel** in the CloudScope
repository — for example, one task on `main` and another on
`feature/fix-disconnect-reconnect-bug` — using **Git worktrees** and **two Cursor
windows**.

---

## Problem

CloudScope is a single Git repository checked out at a path such as:

```text
/Users/cudmore/Sites/cloudscope
```

The normal workflow is:

1. Open Cursor on that folder.
2. `git switch <branch>` when you change tasks.
3. Edit, commit, push on whatever branch is currently checked out.

That works well for **sequential** work. It breaks down when you want to:

- Keep **uncommitted or in-progress work** on a feature branch while doing a
  quick fix on `main`.
- Run **two Cursor agents** (or two chat sessions) on **different branches at
  the same time**.
- Open **two Cursor windows** on the same repo and expect each to stay on its
  own branch.

### Why two Cursor windows on one folder do not work

A Git repository has **one working tree per checkout directory**. Every file on
disk (`src/cloudscope/pages/home_page.py`, etc.) exists in exactly one state: the
state of **whatever branch is currently checked out** in that directory.

If you open two Cursor windows on `/Users/cudmore/Sites/cloudscope`:

- Both windows read and write the **same files**.
- `git switch` in either window (or in a terminal, or via an agent) changes the
  branch for **both** windows.
- Agents in both windows see the same branch and the same uncommitted edits.

Cursor does not isolate branches per window when both windows point at the same
folder. The limitation is Git’s one-branch-per-checkout model, not Cursor
itself.

---

## Solution

Use **Git worktrees**: multiple checkout directories that share one `.git`
database but have **independent working trees and branches**.

```text
/Users/cudmore/Sites/
  cloudscope/                    # original clone (optional “hub”)
  cloudscope-main/               # worktree → branch main
  cloudscope-fix-disconnect/     # worktree → feature/fix-disconnect-reconnect-bug
```

Open **one Cursor window per worktree folder**. Each window (and each agent
session in that window) operates on a fixed branch. Switching or committing in
one worktree does not change the files visible in the other.

| Folder | Branch | Cursor window |
|--------|--------|---------------|
| `cloudscope-main/` | `main` | Window 1 — e.g. small fix on `main` |
| `cloudscope-fix-disconnect/` | `feature/fix-disconnect-reconnect-bug` | Window 2 — e.g. disconnect/reconnect bug |

Commits, pushes, and pull requests work exactly as in a single checkout. All
worktrees share history and remotes because they use the same repository object
database.

---

## Recipe

### Prerequisites

- A clean enough state to add worktrees. If you have uncommitted changes on the
  branch you want to check out in a new worktree, **commit or stash** first. Git
  will refuse to create a worktree if that branch is already checked out
  elsewhere (including in your original `cloudscope/` folder).

- Git 2.5+ (worktrees have been stable for years; any recent Git is fine).

### Step 1 — Create the feature branch (if needed)

From your existing clone:

```bash
cd /Users/cudmore/Sites/cloudscope

# Create the branch from your current HEAD (adjust base as needed)
git branch feature/fix-disconnect-reconnect-bug

# Or create and switch in the main clone only if you are not using a worktree yet:
# git switch -c feature/fix-disconnect-reconnect-bug
```

### Step 2 — Add worktrees

Use **sibling directories** next to the original clone (common convention; paths
are arbitrary):

```bash
cd /Users/cudmore/Sites/cloudscope

git worktree add ../cloudscope-main main
git worktree add ../cloudscope-fix-disconnect feature/fix-disconnect-reconnect-bug
```

Verify:

```bash
git worktree list
```

Example output:

```text
/Users/cudmore/Sites/cloudscope                 abc1234 [some-branch]
/Users/cudmore/Sites/cloudscope-main            def5678 [main]
/Users/cudmore/Sites/cloudscope-fix-disconnect  ghi9012 [feature/fix-disconnect-reconnect-bug]
```

The first line is the **primary** worktree (your original clone). The others are
linked checkouts.

### Step 3 — Open two Cursor windows

1. **File → New Window** (or from terminal: `cursor /Users/cudmore/Sites/cloudscope-main`).
2. In window 1: **File → Open Folder** → `cloudscope-main`.
3. In window 2: **File → Open Folder** → `cloudscope-fix-disconnect`.

Do **not** open the same path in both windows if you need independent branches.

### Step 4 — Work with agents

- Treat **each window as owning one branch**.
- Start a separate agent or chat per window for parallel tasks.
- Agents only see the files and Git state of the folder that window has open.
- Run `git` commands in the terminal **inside that window** (or let the agent run
  them); the cwd should be that worktree’s root.

### Step 5 — Run CloudScope from each worktree (optional)

Each worktree is a full copy of the project tree. You can run the app from
either. Use **different ports** so two servers do not conflict:

```bash
# In cloudscope-main worktree
CLOUDSCOPE_NATIVE=0 CLOUDSCOPE_PORT=8766 CLOUDSCOPE_SHOW=0 uv run python src/cloudscope/app.py

# In cloudscope-fix-disconnect worktree
CLOUDSCOPE_NATIVE=0 CLOUDSCOPE_PORT=8767 CLOUDSCOPE_SHOW=0 uv run python src/cloudscope/app.py
```

Shared tooling (`uv`, virtualenv, `pyproject.toml`) is the same across worktrees.
If you use a local `.env`, each worktree can have its own copy or you can export
variables on the command line.

### Step 6 — Commit, push, and merge as usual

From each worktree:

```bash
git status
git add <files>
git commit -m "..."
git push -u origin <branch>
```

Open PRs from the feature worktree branch. Merge on GitHub (or locally), then
update other worktrees:

```bash
cd /Users/cudmore/Sites/cloudscope-main
git pull origin main
```

### Step 7 — Clean up when finished

After the feature is merged and you no longer need the extra checkout:

```bash
cd /Users/cudmore/Sites/cloudscope

git worktree remove ../cloudscope-fix-disconnect
# Remove cloudscope-main too if you only needed it temporarily:
# git worktree remove ../cloudscope-main
```

If the worktree directory was deleted manually, prune stale entries:

```bash
git worktree prune
```

Delete the feature branch locally when appropriate:

```bash
git branch -d feature/fix-disconnect-reconnect-bug
```

### Ongoing maintenance

| Task | Command |
|------|---------|
| List worktrees | `git worktree list` |
| Fetch for all | `git fetch` (from any worktree) |
| See which branch a folder is on | `git branch --show-current` in that folder |
| Add another worktree | `git worktree add <path> <branch>` |

**Rule:** A given branch can only be checked out in **one** worktree at a time.
To work on `main` in two places, you would need two different branch names (not
typical).

### Suggested layout for CloudScope

Many people keep the **original** `cloudscope/` folder as the hub for `git fetch`,
`git worktree` management, and merges, and use named sibling folders only for
day-to-day editing:

```text
/Users/cudmore/Sites/cloudscope/           # hub; run worktree commands here
/Users/cudmore/Sites/cloudscope-main/      # Cursor window A
/Users/cudmore/Sites/cloudscope-<topic>/   # Cursor window B, C, …
```

Alternatively, use the original folder as one of the task checkouts and add only
one extra worktree. Any layout is fine as long as each active branch lives in
exactly one directory.

---

## Alternative techniques

### 1. Single folder — switch branches (status quo)

**What:** One clone, `git switch` / `git checkout` when changing tasks.

**Pros:** Simple; no extra directories; familiar.

**Cons:** Only one branch’s files on disk at a time; parallel agent work on two
branches is impossible; context switching cost; easy to lose flow on the branch
you switched away from.

**When to use:** Sequential tasks, one active ticket, or quick “peek” at another
branch.

---

### 2. Stash, switch, restore

**What:** `git stash push`, `git switch other-branch`, work, `git switch` back,
`git stash pop`.

**Pros:** No new folders; good for a **short** interruption on another branch.

**Cons:** Stash conflicts; not true parallelism; agents cannot work both sides at
once; messy with multiple stashes.

**When to use:** Five-minute fix on `main` while feature work is dirty and not
ready to commit.

---

### 3. Second full clone (`git clone` again)

**What:** Clone the same remote into a second directory, e.g.
`/Users/cudmore/Sites/cloudscope-2`, check out a different branch there.

**Pros:** Completely separate directories; easy to understand.

**Cons:** Duplicates object storage (mitigated by `git clone --reference` but still
heavier than worktrees); two remotes to keep in sync; more disk use; easy to
push from the “wrong” clone by mistake.

**When to use:** Rarely needed for CloudScope if worktrees are available; sometimes
used when worktree rules or tooling confuse people.

---

### 4. Two Cursor windows, same folder

**What:** Open `/Users/cudmore/Sites/cloudscope` twice.

**Pros:** None for multi-branch work.

**Cons:** Both windows share one branch and one set of files; actively harmful
for parallel branch work.

**When to use:** Only if both windows are for the **same** branch (e.g. reference
code on one monitor, edit on another) — and even then one window is usually
enough.

---

### 5. Cloud / background agents on a branch

**What:** Some Cursor flows run agents against a branch in the cloud while you
work locally.

**Pros:** Can offload one task without a local worktree.

**Cons:** Depends on product features and network; harder to run the app locally
against both lines of work; not a substitute for two local checkouts when you
need to run tests and GUI in both.

**When to use:** Supplement to worktrees, not a replacement, when you want async
help on a well-scoped ticket.

---

### 6. Stacked branches in one checkout

**What:** Feature B branches off feature A; you only ever have one branch checked
out but build PRs in sequence.

**Pros:** Good for **dependent** work; one folder.

**Cons:** Does not help with **independent** parallel tasks on `main` vs a
feature branch.

**When to use:** PR stacks, not “main + unrelated feature at the same time.”

---

## Comparison summary

| Technique | Parallel branches | Parallel agents | Complexity | Recommended |
|-----------|-------------------|-----------------|------------|-------------|
| Git worktrees + 2 Cursor windows | Yes | Yes | Low–medium | **Yes** |
| Switch branch in one folder | No | No | Low | Sequential work only |
| Stash / switch | No | No | Low | Short interruptions |
| Second full clone | Yes | Yes | Medium | Optional |
| Two windows, same folder | No | No | Low | **No** for this goal |

---

## References

- Git documentation: [git-worktree](https://git-scm.com/docs/git-worktree)
- CloudScope dev notes: `README-DEV.md` (running the app, ports, environment)
- Cursor rules in this repo assume a single running app instance per port; use
  different `CLOUDSCOPE_PORT` values when running from multiple worktrees.
