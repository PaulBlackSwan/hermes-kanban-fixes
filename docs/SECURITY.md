# Security and scope

- Source changes are opt-in via `--source` and `--apply`; rollback also defaults
  to dry-run. No profile auto-detection, network, token lookup or credentials.
- Seven exact paths only. Unknown HEAD, edited/missing target, partial install,
  symlink ancestors/leaf, traversal, special files and hardlinks are refused.
- The manifest hash is pinned in the installer. Patch bytes are bound by the
  manifest. Archive checksums bind all release members. None is a signature.
  Replacing both tools and checksums is possible for an attacker controlling the
  delivery channel: authenticate the distribution channel independently.
- Installer and package tools use only Python standard library and local Git.
  The package builder copies a fixed file allowlist, not the working tree.
- No database migration, SQLite backup, card mutation, SQL execution, scheduler,
  settings change, cache clearing, plugin activation or process restart.
- No Git reset, stash, checkout, commit or push in the installer. Installation
  does not alter Git HEAD or index. The patch remains an ordinary working-tree
  change until a maintainer deliberately commits it.
- Run only in a quiescent, trusted checkout under your own account. Path checks
  and a cooperative installer lock are not a security boundary against another
  process racing symlinks or replacing files between checks. Arbitrary concurrent
  writers and hostile filesystem races are not supported. There is no sandbox.
- Git must be trusted; the installer removes ambient `GIT_*` overrides and
  disables global/system configuration for its subprocesses, but repository
  configuration and the Git executable are part of the trust boundary.
- Rollback validates all installed files and backup contents before restoring.
  Backup metadata permissions are not independently authenticated; protect the
  backup directory as local user-owned state. Backups are retained, not deleted.
- Apply and rollback are not crash-atomic; see the manual recovery limitations
  in INSTALL.md. Do not infer success from existence of a ledger.

Public archives exclude local evidence, Git metadata, dependency directories,
logs and machine-specific paths. Local qualification evidence stays outside the
archive. A clean distribution test does not prove live runtime delivery.
