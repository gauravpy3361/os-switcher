# Safety Notes

This project edits firmware boot settings. Test in this order:

1. Confirm both operating systems boot normally from your firmware boot menu.
2. Disable disk encryption surprises, or make sure you know the recovery flow.
3. Run dry runs on both operating systems.
4. Run the real command once from a terminal before using the GUI.
5. Keep firmware boot-menu access available during testing.

## What The Scripts Change

Windows:

```powershell
bcdedit /set "{fwbootmgr}" bootsequence "{target-id}"
```

Linux:

```bash
efibootmgr -n TARGET_ID
```

Both are intended as one-time boot selections.

## Transition State

Each OS can keep a local state directory from `config.json`:

- Windows default: `C:\ProgramData\OSSwitcher`
- Linux default: `/var/lib/os-switcher`

Local state is good for development, but shared state is strongly recommended for real switching. In shared mode, `state.shared.windowsStateDir` and `state.shared.linuxStateDir` must point to the same durable storage location from each OS. This lets the OS that actually booted clear or fail the exact pending transition.

The switch scripts create:

- `transition.lock` while a transition command is running.
- `transition-staged.json` while the firmware command is being prepared.
- `pending-transition.json` after the firmware command succeeds and before rebooting.
- `boot-fail-count.txt` when a pending transition expires.
- `recovery-mode.json` when failures reach `safety.maxBootFailures`.
- `failed-transition-*.json` when a pending transition times out.
- `last-boot-success.json` when `mark-boot-success` is run.

This is basic boot validation. It catches stale, failed, incomplete, and wrong-target transitions before the next switch request. It does not yet repair firmware entries automatically.

Use `windows/install-boot-success-task.ps1` and `linux/install-boot-success-service.sh` to make success marking automatic after startup.

The Windows scheduled task runs at logon, and the Linux service runs as root at startup. Both success scripts exit without writing anything when there is no transition state. If the current OS is not the pending target, the success script records a failed transition instead of clearing it.

Failure and recovery state are not cleared automatically. After you inspect boot health, run `windows/mark-boot-success.ps1 -ClearRecovery` or `linux/mark-boot-success.sh --clear-recovery`.

The Linux installer uses a stable wrapper at `/usr/local/lib/os-switcher/mark-boot-success-wrapper.sh` so project paths with spaces do not affect the systemd unit.

## Power Failure & Stale Transitions

In rare circumstances, a **graceful power failure** can occur. This happens when the switch script successfully configures the UEFI variable (`BootSequence` on Windows or `BootNext` on Linux) and writes `pending-transition.json`, but the system loses power or fails to shut down before a proper reboot can occur.

If this happens:
1. The transition files remain in the `pending` state permanently.
2. The target OS is never booted, so the transition cannot be marked as successful or failed by the success monitoring scripts.
3. Future switch commands are blocked because a transition is apparently already in progress.

### Diagnosis & Recovery

You can diagnose this scenario using the preflight doctor tool:

```bash
python tools/doctor.py --check-stale [MINUTES]
```

If a pending transition is older than the threshold (defaults to `safety.pendingTransitionTimeoutMinutes` in `config.json`), the doctor will report a warning explaining that a stale transition was detected.

To recover from this state:
- If the reboot never happened and you want to abort the switch, run the rollback script to clean up transition files and restore your original firmware entries:
  - **Windows**: `powershell -ExecutionPolicy Bypass -File "windows/rollback.ps1"`
  - **Linux**: `sudo bash "linux/rollback.sh"`
- Alternatively, you can run `mark-boot-success` manually on the target platform to mark the transition as complete.

## What The Scripts Do Not Do Yet

- They do not repair broken boot entries.
- They do not automatically schedule boot-success marking.
- They do not optimize startup services.
- They do not choose or create the shared state storage for you.

Those belong in later phases after the manual switching path is proven.
