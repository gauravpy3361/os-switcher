---- MODULE OSSwitcher ----
EXTENDS Naturals, TLC

CONSTANTS Windows, Linux, Null, MaxBootFailures

VARIABLES
    current_os,
    next_boot,
    rebooting,
    transition_lock,
    pending_transition,
    boot_fail_count,
    recovery_mode

OSes == {Windows, Linux}

vars ==
    <<current_os,
      next_boot,
      rebooting,
      transition_lock,
      pending_transition,
      boot_fail_count,
      recovery_mode>>

Init ==
    /\ current_os = Windows
    /\ next_boot = Null
    /\ rebooting = FALSE
    /\ transition_lock = FALSE
    /\ pending_transition = FALSE
    /\ boot_fail_count = 0
    /\ recovery_mode = FALSE

CanStartTransition(os) ==
    /\ current_os = os
    /\ transition_lock = FALSE
    /\ pending_transition = FALSE
    /\ recovery_mode = FALSE

WindowsToLinux ==
    /\ CanStartTransition(Windows)
    /\ next_boot' = Linux
    /\ rebooting' = TRUE
    /\ transition_lock' = TRUE
    /\ pending_transition' = TRUE
    /\ UNCHANGED <<current_os, boot_fail_count, recovery_mode>>

LinuxToWindows ==
    /\ CanStartTransition(Linux)
    /\ next_boot' = Windows
    /\ rebooting' = TRUE
    /\ transition_lock' = TRUE
    /\ pending_transition' = TRUE
    /\ UNCHANGED <<current_os, boot_fail_count, recovery_mode>>

BootComplete ==
    /\ rebooting = TRUE
    /\ next_boot \in OSes
    /\ current_os' = next_boot
    /\ next_boot' = Null
    /\ rebooting' = FALSE
    /\ transition_lock' = FALSE
    /\ UNCHANGED <<pending_transition, boot_fail_count, recovery_mode>>

MarkBootSuccess ==
    /\ current_os \in OSes
    /\ rebooting = FALSE
    /\ next_boot = Null
    /\ pending_transition \/ recovery_mode \/ boot_fail_count > 0
    /\ pending_transition' = FALSE
    /\ boot_fail_count' = 0
    /\ recovery_mode' = FALSE
    /\ UNCHANGED <<current_os, next_boot, transition_lock>>

BootTimeout ==
    /\ pending_transition = TRUE
    /\ rebooting = FALSE
    /\ next_boot = Null
    /\ boot_fail_count < MaxBootFailures
    /\ boot_fail_count' = boot_fail_count + 1
    /\ pending_transition' = FALSE
    /\ transition_lock' = FALSE
    /\ next_boot' = Null
    /\ UNCHANGED <<current_os, rebooting, recovery_mode>>

EnterRecovery ==
    /\ boot_fail_count >= MaxBootFailures
    /\ recovery_mode = FALSE
    /\ recovery_mode' = TRUE
    /\ pending_transition' = FALSE
    /\ transition_lock' = FALSE
    /\ next_boot' = Null
    /\ rebooting' = FALSE
    /\ UNCHANGED <<current_os, boot_fail_count>>

Next ==
    \/ WindowsToLinux
    \/ LinuxToWindows
    \/ BootComplete
    \/ MarkBootSuccess
    \/ BootTimeout
    \/ EnterRecovery

OnlyOneOSActive == current_os \in OSes

RebootHasTarget == rebooting => next_boot \in OSes

NoDuplicateTransition == transition_lock => pending_transition \/ rebooting

RecoveryStopsTransitions == recovery_mode => ~rebooting

TransitionEventuallySettles ==
    [](pending_transition => <>(~pending_transition \/ recovery_mode))

RecoveryCanBeCleared ==
    [](recovery_mode => <>~recovery_mode)

Spec ==
    /\ Init
    /\ [][Next]_vars
    /\ WF_vars(Next)
    /\ SF_vars(MarkBootSuccess)

====
