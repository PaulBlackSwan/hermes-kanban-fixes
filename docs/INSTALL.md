# Installation and rollback

## Prerequisites

Use a trusted release and verify its external SHA-256 before extracting it into
a new empty directory. Do not merge an archive into an existing release tree.
Python 3.9+ and Git must be available. The target must be an explicit absolute
checkout root, with no symlink or `..` component. Git HEAD must equal
`bf0203a794a07aac3ff764972ab9087baa4e4f4e` and all seven target hashes must match
the manifest. Four new paths must be absent before installation.

Stop competing checkout writers before applying or rolling back. Coordinate any
runtime maintenance separately: this tool never stops, starts or reloads Hermes.
The package is not a plugin; installing a separate runtime plugin cannot replace
these core source changes and must not silently write this patch into core.

## Inspect and dry-run

From the extracted package directory:

```sh
python3 -B tools/package_release.py --verify "$HOME/downloads/kanban-fixes.zip"
git -C "$HOME/src/hermes-agent" rev-parse HEAD
python3 -B tools/install.py --source "$HOME/src/hermes-agent"
```

The default performs package integrity, checkout identity, target hashes and
`git apply --check`. It writes no target files, backups, locks or ledger.
The `-B` option also avoids interpreter bytecode-cache writes.

## Explicit application

```sh
python3 -B tools/install.py --source "$HOME/src/hermes-agent" --apply
```

The installer validates every target before writing. It uses an exclusive
installer lock under `.hermes-kanban-fixes/`, saves only the three existing
modified source files with their modes, records absent new paths, then applies
the single patch. It verifies all seven after hashes and a reverse patch check.
It never invokes Git reset/stash/checkout, package installs or core imports.
Unrelated dirty files are preserved. The backup is:

```text
<source>/.hermes-kanban-fixes/0.1.0-rc.1/
  ledger.json
  before/<three existing target paths>
```

An identical second apply returns `already_applied` only when all seven after
hashes match. This is not proof that a running process reloaded the code.

## Rollback

```sh
python3 -B tools/install.py --source "$HOME/src/hermes-agent" --rollback
python3 -B tools/install.py --source "$HOME/src/hermes-agent" --rollback --apply
```

Rollback requires the original exact checkout HEAD, valid matching ledger,
valid before-file backup hashes and **all seven current files exactly matching
the installed after hashes**. It restores the three originals and their modes,
removes only the four files introduced by the patch, verifies the before hashes
and retains the backups and ledger. Empty directories can remain. Unrelated
files are untouched. A second rollback is refused rather than overwriting edits.

Retained backup state intentionally prevents a new installation after rollback.
Archive and reconcile that state manually before a fresh application; the tool
has no cleanup, force or ignore-checks option.

## Refusals and interrupted operations

Exit 0 means dry-run, applied, already_applied or rolled_back as reported in JSON.
Exit 2 (`REFUSED`) means no supported completion. A partial state is never treated
as installed. Preserve local edits and compare all seven paths to the manifest.
Do not force an overwrite or reset unrelated changes.

Git apply preflight and its normal atomic patch checks prevent ordinary patch
failures. The overall backup/apply/rollback operation is **not crash-atomic**.
Power loss, disk-full, malicious concurrent writers or permissions changing
mid-operation can leave a retained ledger and partial state. The installer
refuses such states; manual recovery from the hash-checked targeted backups is
required. Never delete a stale lock before confirming no installer is running.
Rollback preflights all files but can also be interrupted during restoration.
The installer does not provide automatic recovery from an interrupted rollback.

Do not edit installed target files if you expect automatic rollback to work.
Copy edits elsewhere, then reconcile deliberately. Backups contain only source
files, never databases, credentials, settings, profile state or application caches.
