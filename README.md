# Hermes Kanban fixes — 0.1.0-rc.1

Standalone, offline **source patch bundle**, not a runtime plugin. This release
preserves seven qualified Kanban changes without redesigning their behavior.
It contains no audio integration and does not install or enable any plugin.

## Exact compatibility

Only Git checkouts with HEAD exactly
`bf0203a794a07aac3ff764972ab9087baa4e4f4e` are supported. Each of the seven
paths must also match its before SHA-256 (or be absent for new files).
A different revision, partial application or local edits to these targets is
refused. An already-applied result requires **all seven** after hashes, not
merely a matching version or receipt. Unrelated files are not reset or stashed.

`manifest.json` records before/after hashes, explicit null for absent base paths,
base revision, release version and the unified patch hash. This is integrity
metadata, **not a cryptographic signature or publisher authentication**.
Obtain the ZIP and its checksum from a trusted channel.

## Changes, in one ordered patch

1. **TUI notification parity and blocked-card guidance:** consume block-loop,
   review-requested and changes-requested events; show the coordinator a next
   action and dated review, without automatic unblock/retry.
2. **Block follow-up and administrative closure:** watcher wake guidance,
   completion from triage, and a read-only `BLOCK_FOLLOWUP_V1` reporting script
   using existing native card comments. No database migration or scheduler.
3. **Regression tests:** three new test files accompany the four runtime paths.

One patch avoids ambiguous ordering between interdependent notification and
follow-up changes. The script only reports; recording comments, activating a
native loop, running SQL or changing cards is outside installation scope.

## Use

Read [installation and rollback](docs/INSTALL.md) and
[security and limitations](docs/SECURITY.md) first.

```sh
python3 -B tools/install.py --source "$HOME/src/hermes-agent"
python3 -B tools/install.py --source "$HOME/src/hermes-agent" --apply
python3 -B tools/install.py --source "$HOME/src/hermes-agent" --rollback
python3 -B tools/install.py --source "$HOME/src/hermes-agent" --rollback --apply
```

The first and third commands are dry-runs. No checkout is discovered implicitly.
No process is restarted: an already-running process may still use old code.

## Build and test

Python 3.9+ and Git are sufficient for distribution tools. The bundled
runtime script requires Python 3.11+ (`datetime.UTC`). See
[testing and reproducibility](docs/TESTING.md).

```sh
KANBAN_TEST_REPOSITORY="$HOME/src/hermes-agent" python3 -B -m unittest discover -s tests -v
python3 -B tools/package_release.py --output "$HOME/kanban-fixes.zip"
python3 -B tools/package_release.py --verify "$HOME/kanban-fixes.zip"
```

This release candidate is limited to the exact source base above, not a claim of
compatibility with future versions. Distribution acceptance tests do not replace
runtime regression tests or prove a live session received a notification.
