param(
    [Parameter(Mandatory = $true)]
    [string]$RendererPath,
    [string]$OutputPath = "oes-core-renderer-performance.json",
    [int]$Seconds = 10
)

$ErrorActionPreference = "Stop"
$process = Start-Process -FilePath $RendererPath -PassThru
try {
    Start-Sleep -Seconds 2
    $samples = @()
    $previousCpu = $process.CPU
    $logicalProcessors = [Environment]::ProcessorCount
    for ($index = 0; $index -lt $Seconds; $index++) {
        $process.Refresh()
        $currentCpu = $process.CPU
        $gpu = $null
        $nvidiaSmi = Get-Command nvidia-smi.exe -ErrorAction SilentlyContinue
        if ($nvidiaSmi) {
            $gpu = & $nvidiaSmi.Source --query-gpu=name,utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits
        }
        $samples += [ordered]@{
            captured_at_utc = [DateTime]::UtcNow.ToString("o")
            cpu_seconds = $currentCpu
            cpu_percent = (($currentCpu - $previousCpu) / [Math]::Max(1, $logicalProcessors)) * 100
            working_set_bytes = $process.WorkingSet64
            private_memory_bytes = $process.PrivateMemorySize64
            nvidia_gpu = @($gpu)
        }
        $previousCpu = $currentCpu
        Start-Sleep -Seconds 1
    }
    [ordered]@{
        renderer = (Resolve-Path $RendererPath).Path
        process_id = $process.Id
        samples = $samples
        note = "nvidia-smi utilization is adapter-wide. Use Task Manager GPU Engine or GPUView to isolate this graphics process."
    } | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 $OutputPath
    Write-Host "Performance samples written to $OutputPath"
}
finally {
    if (!$process.HasExited) { $process.CloseMainWindow() | Out-Null }
}
