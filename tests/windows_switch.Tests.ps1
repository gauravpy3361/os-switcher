BeforeAll {
    $script:Root = Split-Path -Parent $PSScriptRoot
    $script:SwitchScript = Join-Path $script:Root "windows\switch-to-linux.ps1"
    $script:MarkScript = Join-Path $script:Root "windows\mark-boot-success.ps1"
    $script:FirmwareFixture = Join-Path $script:Root "tests\fixtures\bcdedit_firmware.txt"

    function New-TestConfig {
        param([string]$StateDir)

        $config = [ordered]@{
            windows = [ordered]@{
                targetLabel = "Linux Workspace"
                rebootTimeoutSeconds = 5
                stateDir = $StateDir
            }
            linux = [ordered]@{
                targetLabel = "Windows Boot Manager"
                rebootDelaySeconds = 5
                stateDir = "/var/lib/os-switcher"
            }
            safety = [ordered]@{
                requireConfirmation = $true
                pendingTransitionTimeoutMinutes = 10
                maxBootFailures = 3
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
}

Describe "Windows boot success marker" {
    It "clears pending only when Windows was the target" {
        $stateDir = Join-Path $TestDrive "state-success"
        New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
        $configPath = Join-Path $TestDrive "config-success.json"
        New-TestConfig -StateDir $stateDir | Set-Content -LiteralPath $configPath -Encoding UTF8
        @{
            target = "Windows"
            identifier = "{bootmgr}"
            startedAt = "2026-05-20T00:00:00Z"
            source = "Linux"
            state = "pending"
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
            target = "Linux"
            identifier = "{11111111-1111-1111-1111-111111111111}"
            startedAt = "2026-05-20T00:00:00Z"
            source = "Windows"
            state = "pending"
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
