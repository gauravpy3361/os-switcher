BeforeAll {
    $script:Root = Split-Path -Parent $PSScriptRoot
    $script:SwitchScript = Join-Path $script:Root "windows\switch-to-linux.ps1"
    $script:MarkScript  = Join-Path $script:Root "windows\mark-boot-success.ps1"
    $script:RollbackScript = Join-Path $script:Root "windows\rollback.ps1"
    $script:FirmwareFixture = Join-Path $script:Root "tests\fixtures\bcdedit_firmware.txt"

    function New-TestConfig {
        param([string]$StateDir)

        $config = [ordered]@{
            windows = [ordered]@{
                targetLabel          = "Linux Workspace"
                rebootTimeoutSeconds = 5
                stateDir             = $StateDir
            }
            linux = [ordered]@{
                targetLabel       = "Windows Boot Manager"
                rebootDelaySeconds = 5
                stateDir          = "/var/lib/os-switcher"
            }
            safety = [ordered]@{
                requireConfirmation             = $true
                pendingTransitionTimeoutMinutes = 10
                maxBootFailures                 = 3
            }
        }

        return ($config | ConvertTo-Json -Depth 5)
    }
}

Describe "Windows switch script" {
    It "dry-runs from fixture output without writing pending state" {
        $stateDir = Join-Path $TestDrive "state"
        New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
        $configPath = Join-Path $TestDrive "config.json"
        New-TestConfig -StateDir $stateDir | Set-Content -LiteralPath $configPath -Encoding UTF8

        $output = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $script:SwitchScript -ConfigPath $configPath -FirmwareEntriesPath $script:FirmwareFixture -DryRun 2>&1
        $exitCode = $LASTEXITCODE

        $exitCode | Should -Be 0
        ($output -join "`n") | Should -Match "Target Linux firmware entry"
        ($output -join "`n") | Should -Match "Dry run: would run bcdedit"
        Test-Path -LiteralPath (Join-Path $stateDir "pending-transition.json") | Should -BeFalse
    }

    It "rejects config with maxBootFailures set to 0" {
        $stateDir = Join-Path $TestDrive "state-invalid"
        New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
        $configPath = Join-Path $TestDrive "config-invalid.json"

        $config = [ordered]@{
            windows = [ordered]@{
                targetLabel          = "Linux Workspace"
                rebootTimeoutSeconds = 5
                stateDir             = $stateDir
            }
            linux = [ordered]@{
                targetLabel        = "Windows Boot Manager"
                rebootDelaySeconds = 5
                stateDir           = "/var/lib/os-switcher"
            }
            safety = [ordered]@{
                requireConfirmation             = $true
                pendingTransitionTimeoutMinutes = 10
                maxBootFailures                 = 0
            }
        }
        ($config | ConvertTo-Json -Depth 5) | Set-Content -LiteralPath $configPath -Encoding UTF8

        $output = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $script:SwitchScript -ConfigPath $configPath -FirmwareEntriesPath $script:FirmwareFixture -DryRun 2>&1
        $exitCode = $LASTEXITCODE

        $exitCode | Should -Not -Be 0
        ($output -join "`n") | Should -Match "maxBootFailures"
    }

    It "rejects config with negative rebootTimeoutSeconds" {
        $stateDir = Join-Path $TestDrive "state-neg"
        New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
        $configPath = Join-Path $TestDrive "config-neg.json"

        $config = [ordered]@{
            windows = [ordered]@{
                targetLabel          = "Linux Workspace"
                rebootTimeoutSeconds = -1
                stateDir             = $stateDir
            }
            linux = [ordered]@{
                targetLabel        = "Windows Boot Manager"
                rebootDelaySeconds = 5
                stateDir           = "/var/lib/os-switcher"
            }
            safety = [ordered]@{
                requireConfirmation             = $true
                pendingTransitionTimeoutMinutes = 10
                maxBootFailures                 = 3
            }
        }
        ($config | ConvertTo-Json -Depth 5) | Set-Content -LiteralPath $configPath -Encoding UTF8

        $output = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $script:SwitchScript -ConfigPath $configPath -FirmwareEntriesPath $script:FirmwareFixture -DryRun 2>&1
        $exitCode = $LASTEXITCODE

        $exitCode | Should -Not -Be 0
        ($output -join "`n") | Should -Match "rebootTimeoutSeconds"
    }
}

Describe "Windows boot success marker" {
    It "clears pending only when Windows was the target" {
        $stateDir = Join-Path $TestDrive "state-success"
        New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
        $configPath = Join-Path $TestDrive "config-success.json"
        New-TestConfig -StateDir $stateDir | Set-Content -LiteralPath $configPath -Encoding UTF8
        @{
            target    = "Windows"
            identifier = "{bootmgr}"
            startedAt = "2026-05-20T00:00:00Z"
            source    = "Linux"
            state     = "pending"
        } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $stateDir "pending-transition.json") -Encoding UTF8

        $output = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $script:MarkScript -ConfigPath $configPath 2>&1
        $exitCode = $LASTEXITCODE

        $exitCode | Should -Be 0
        ($output -join "`n") | Should -Match "Marked Windows boot success"
        Test-Path -LiteralPath (Join-Path $stateDir "pending-transition.json") | Should -BeFalse
        Test-Path -LiteralPath (Join-Path $stateDir "last-boot-success.json") | Should -BeTrue
    }

    It "records failure when Linux was the target" {
        $stateDir = Join-Path $TestDrive "state-failure"
        New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
        $configPath = Join-Path $TestDrive "config-failure.json"
        New-TestConfig -StateDir $stateDir | Set-Content -LiteralPath $configPath -Encoding UTF8
        @{
            target    = "Linux"
            identifier = "{11111111-1111-1111-1111-111111111111}"
            startedAt = "2026-05-20T00:00:00Z"
            source    = "Windows"
            state     = "pending"
        } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $stateDir "pending-transition.json") -Encoding UTF8

        $output = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $script:MarkScript -ConfigPath $configPath 2>&1
        $exitCode = $LASTEXITCODE

        $exitCode | Should -Be 1
        ($output -join "`n") | Should -Match "Boot target mismatch recorded"
        Test-Path -LiteralPath (Join-Path $stateDir "pending-transition.json") | Should -BeFalse
        Test-Path -LiteralPath (Join-Path $stateDir "boot-fail-count.txt") | Should -BeTrue
        Test-Path -LiteralPath (Join-Path $stateDir "last-boot-mismatch.json") | Should -BeTrue
    }
}

Describe "Windows rollback script" {
    It "exits 0 and says no recovery when recovery-mode.json is absent" {
        $stateDir = Join-Path $TestDrive "state-no-recovery"
        New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
        $configPath = Join-Path $TestDrive "config-no-recovery.json"
        New-TestConfig -StateDir $stateDir | Set-Content -LiteralPath $configPath -Encoding UTF8

        $output = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $script:RollbackScript -ConfigPath $configPath 2>&1
        $exitCode = $LASTEXITCODE

        $exitCode | Should -Be 0
        ($output -join "`n") | Should -Match "No recovery mode active"
    }

    It "exits 1 and prints RECOVERY MODE ACTIVE when recovery-mode.json exists" {
        $stateDir = Join-Path $TestDrive "state-recovery"
        New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
        $configPath = Join-Path $TestDrive "config-recovery.json"
        New-TestConfig -StateDir $stateDir | Set-Content -LiteralPath $configPath -Encoding UTF8
        '{"recoveryAt":"2026-05-20T00:00:00Z","reason":"consecutive boot failures"}' |
            Set-Content -LiteralPath (Join-Path $stateDir "recovery-mode.json") -Encoding UTF8

        $output = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $script:RollbackScript -ConfigPath $configPath 2>&1
        $exitCode = $LASTEXITCODE

        $exitCode | Should -Be 1
        ($output -join "`n") | Should -Match "RECOVERY MODE ACTIVE"
    }

    It "prints newest backup path when an EFI backup file exists" {
        $stateDir = Join-Path $TestDrive "state-backup"
        New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
        $configPath = Join-Path $TestDrive "config-backup.json"
        New-TestConfig -StateDir $stateDir | Set-Content -LiteralPath $configPath -Encoding UTF8
        '{"recoveryAt":"2026-05-20T00:00:00Z"}' |
            Set-Content -LiteralPath (Join-Path $stateDir "recovery-mode.json") -Encoding UTF8
        "BootCurrent: 0001`nBoot0000* Windows" |
            Set-Content -LiteralPath (Join-Path $stateDir "efi-backup-20260520-120000.txt") -Encoding UTF8

        $output = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $script:RollbackScript -ConfigPath $configPath 2>&1

        ($output -join "`n") | Should -Match "efi-backup-20260520-120000.txt"
    }

    It "prints no-backup message when no EFI backup files exist" {
        $stateDir = Join-Path $TestDrive "state-nobackup"
        New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
        $configPath = Join-Path $TestDrive "config-nobackup.json"
        New-TestConfig -StateDir $stateDir | Set-Content -LiteralPath $configPath -Encoding UTF8
        '{"recoveryAt":"2026-05-20T00:00:00Z"}' |
            Set-Content -LiteralPath (Join-Path $stateDir "recovery-mode.json") -Encoding UTF8

        $output = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $script:RollbackScript -ConfigPath $configPath 2>&1

        ($output -join "`n") | Should -Match "No backup files found"
    }
}
