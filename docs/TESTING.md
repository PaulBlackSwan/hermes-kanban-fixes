# Tests and reproducible releases

## Distribution acceptance suite

```sh
KANBAN_TEST_REPOSITORY="$HOME/src/hermes-agent" \
  python3 -B -m unittest discover -s tests -v
```

The local fixture repository must contain the exact qualified base commit.
Tests clone it with `--shared --no-checkout` into disposable scratch directories
and check out that base in the clone. They never mutate the original repository,
import Hermes, run application code or access a real database. Each child
installer has a disposable HOME. `TMPDIR` must name a user-owned scratch directory
(not a live checkout); if absent, the suite uses the user's `.cache` directory.
Without `KANBAN_TEST_REPOSITORY`, fixture tests are explicitly skipped, not proof
of a successful acceptance run. No network or dependencies are needed.

Coverage includes default no-write dry-run, explicit apply, all-nine hashes,
idempotence, rollback dry-run, rollback, unrelated file preservation, modified or
missing targets, partial state, symlink leaf and ancestors, path traversal,
unsupported HEAD, altered manifest/patch/backup, reproducible archives, member
checksums, and installation/rollback from an extracted release.

## Runtime regression tests

The rc.3 documentation/privacy release preserves the rc.2 patch and all nine
before/after source hashes exactly. Its 15 distribution tests passed without
skips both from source and the final extracted archive. Reproducibility and
independent forward/reverse source hash checks were rerun. The runtime results
below are historical rc.2 evidence, not a new runtime run for rc.3.

The unified patch includes existing qualified regression tests. Run the target
checkout's documented isolated runner for these files and relevant regressions:

- `tests/gateway/test_kanban_block_followup_wake.py`
- `tests/gateway/test_local_kanban_wake.py` (uses the base's existing
  `tests/gateway/test_local_producer_admission.py` helper)
- `tests/hermes_cli/test_kanban_block_followup.py`
- `tests/tui_gateway/test_kanban_block_followup_notifications.py`

For rc.2, **160 runtime tests across 18 files passed, 0 failed**, using the
checkout's isolated runner in a disposable exact-base clone. This includes the
16 previously qualified Kanban files, the existing local producer admission
suite and the new default/beta local wake regression. Removing only the runner
binding reproduced **2 failing local wake cases**; restoring it passed both.
Runtime tests use temporary state, not live databases. Separately, **15
distribution tests passed without skips**, and the same suite was rerun from
the final extracted archive. Prior anonymized fixtures and UTC-boundary
validation corrections remain unchanged. No new independent review is claimed.
Re-run the relevant tests for your own environment.

No live deployment, route receipt or background-process reload is implied.

## Build

```sh
python3 -B tools/package_release.py --output "$HOME/kanban-fixes-a.zip"
python3 -B tools/package_release.py --output "$HOME/kanban-fixes-b.zip"
cmp "$HOME/kanban-fixes-a.zip" "$HOME/kanban-fixes-b.zip"
python3 -B tools/package_release.py --verify "$HOME/kanban-fixes-a.zip"
```

The ZIP uses sorted exact-allowlist members, fixed timestamps, fixed regular-file
permissions and ZIP_STORED (no compression-library variability). `SHA256SUMS`
inside the ZIP covers every other member including the compatibility manifest.
The adjacent `.zip.sha256` records the whole archive hash. Neither checksum is a
publisher signature. Existing output paths are refused. Documentation/tool edits
change the archive hash and require a fresh build and rerun.

Local `verification/`, `dist/`, Git internals, caches and logs are never copied.
The builder refuses nonregular/hardlinked/symlink sources and obvious private
absolute paths in public text. Verification checks the complete allowlist,
duplicate members, regular modes, canonical timestamps and every checksum.
