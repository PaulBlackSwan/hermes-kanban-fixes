# Changelog

## 0.1.0-rc.2

- Add the omitted core local wake fix: `LocalSessionAdapter.__init__` binds
  `gateway_runner` to `authority.runner` immediately after storing the authority.
- Include synthetic default/beta profile regressions using the real local
  adapter, canonical wake, owner scope and temporary SQLite admission. Direct
  authorization of reconstructed notifier sources remains denied.
- Extend the exact-base manifest and installer allowlist from seven to nine
  paths; refresh patch/manifest hashes and the installer's manifest pin.
- Add distribution coverage for the new targets and refusal of rc.1's partial
  target state; make backup-tampering coverage follow the manifest version.
- Preserve exact base `bf0203a794a07aac3ff764972ab9087baa4e4f4e`, previous
  release assets, targeted rollback, no-write default and read-only plugin
  separation. Upgrades require rc.1 rollback or deliberate reconciliation.
- Qualification: 160 runtime tests across 18 files, 15 distribution tests and
  15 final extracted-archive tests passed. The two new wake cases fail when
  only the core runner binding is removed. No deployment/reload is included.

## 0.1.0-rc.1

Initial exact-base source patch distribution: TUI notification parity, blocked
card follow-up guidance/reporting, triage completion, bounded UTC validation,
qualified regression tests, hash-pinned installer and reproducible archive.
