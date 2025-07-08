# Script to test bug detection discrepancy between batch and individual scans

Write-Host "Starting bug detection comparison..." -ForegroundColor Cyan

# List of files reported to have bugs from batch scan
$buggy_files = @(
    "C:\Users\Yusuf\Downloads\FixWurx\cli.py",
    "C:\Users\Yusuf\Downloads\FixWurx\hub.py",
    "C:\Users\Yusuf\Downloads\FixWurx\main.py",
    "C:\Users\Yusuf\Downloads\FixWurx\meta_agent.py",
    "C:\Users\Yusuf\Downloads\FixWurx\optimizer.py",
    "C:\Users\Yusuf\Downloads\FixWurx\replay_buffer.py",
    "C:\Users\Yusuf\Downloads\FixWurx\scheduler.py",
    "C:\Users\Yusuf\Downloads\FixWurx\Specialized_agents.py",
    "C:\Users\Yusuf\Downloads\FixWurx\test_runner.py",
    "C:\Users\Yusuf\Downloads\FixWurx\triangulation_engine.py"
)

# Create a log file
$log_file = "bug_detection_comparison_log.md"
"# Bug Detection Comparison: Batch vs Individual Scanning" | Out-File -FilePath $log_file
"" | Out-File -FilePath $log_file -Append
"Comparison performed on $(Get-Date)" | Out-File -FilePath $log_file -Append
"" | Out-File -FilePath $log_file -Append
"## Background" | Out-File -FilePath $log_file -Append
"We observed that when scanning files individually, the bug detector shows 0 bugs, but when scanning the entire directory, it reports bugs in multiple files. This script tests each file individually to compare the results." | Out-File -FilePath $log_file -Append
"" | Out-File -FilePath $log_file -Append
"## Results" | Out-File -FilePath $log_file -Append
"" | Out-File -FilePath $log_file -Append

# Test each file individually
foreach ($file in $buggy_files) {
    $file_name = Split-Path $file -Leaf
    Write-Host "Testing $file_name individually..." -ForegroundColor Yellow
    
    "### $file_name" | Out-File -FilePath $log_file -Append
    "```" | Out-File -FilePath $log_file -Append
    $result = python scripts/bug_detector_cli.py --scan $file --verify --show-bugs 2>&1 | Out-String
    $result | Out-File -FilePath $log_file -Append
    "```" | Out-File -FilePath $log_file -Append
    
    if ($result -like "*Found 0 potential bugs*") {
        "**Result:** No bugs found in individual scan, but bugs reported in batch scan. INCONSISTENT" | Out-File -FilePath $log_file -Append
    } else {
        "**Result:** Bugs found in both individual and batch scans. CONSISTENT" | Out-File -FilePath $log_file -Append
    }
    "" | Out-File -FilePath $log_file -Append
}

# Run a batch scan for comparison
"## Batch Scan Results" | Out-File -FilePath $log_file -Append
"```" | Out-File -FilePath $log_file -Append
python scripts/bug_detector_cli.py --scan C:\Users\Yusuf\Downloads\FixWurx --verify --show-bugs 2>&1 | Out-File -FilePath $log_file -Append
"```" | Out-File -FilePath $log_file -Append

# Add analysis section
"" | Out-File -FilePath $log_file -Append
"## Analysis" | Out-File -FilePath $log_file -Append
"This section will be completed after reviewing the results." | Out-File -FilePath $log_file -Append

Write-Host "Comparison completed. See $log_file for results." -ForegroundColor Green
