# Changelog

## 0.1.0-rc.3

- Documentation/privacy release: remove unrelated integration references from
  current documentation and publish under the public maintainer pseudonym.
- The functional patch, exact base and all nine source before/after hashes are
  byte-for-byte unchanged from rc.2. Refresh the release version, manifest digest
  and installer pin only; existing release assets remain unchanged.
- This is not an incremental upgrade. An rc.2-patched tree is already equivalent
  in target bytes, but rollback still requires the rc.2 installer and its ledger.
  The rc.3 installer does not adopt another release's backup ownership.
- Qualification: 15 distribution tests passed without skips, including from the
  extracted archive; reproducible archives and forward/reverse source hashes
  verified. No new runtime test run or deployment is claimed for this release.

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
