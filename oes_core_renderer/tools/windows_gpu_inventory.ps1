param(
    [string]$OutputPath = "oes-core-gpu-inventory.json"
)

$ErrorActionPreference = "Stop"
$controllers = Get-CimInstance Win32_VideoController | ForEach-Object {
    [ordered]@{
        name = $_.Name
        driver_version = $_.DriverVersion
        vram_bytes = [uint64]$_.AdapterRAM
        pnp_device_id = $_.PNPDeviceID
        status = $_.Status
    }
}

$nvidia = $null
$nvidiaSmi = Get-Command nvidia-smi.exe -ErrorAction SilentlyContinue
if ($nvidiaSmi) {
    $nvidia = & $nvidiaSmi.Source --query-gpu=name,driver_version,memory.total,pci.bus_id,pci.device_id --format=csv,noheader,nounits
}

$dxdiagPath = Join-Path $env:TEMP "oes-core-dxdiag.txt"
Start-Process -FilePath "dxdiag.exe" -ArgumentList "/whql:off", "/t", $dxdiagPath -Wait
$dxdiag = Get-Content $dxdiagPath -Raw
$featureLevels = [regex]::Matches($dxdiag, "Feature Levels:\s*([^\r\n]+)") |
    ForEach-Object { $_.Groups[1].Value.Trim() } |
    Select-Object -Unique

$inventory = [ordered]@{
    captured_at_utc = [DateTime]::UtcNow.ToString("o")
    computer_name = $env:COMPUTERNAME
    video_controllers = @($controllers)
    nvidia_smi = @($nvidia)
    directx_feature_levels = @($featureLevels)
    hybrid_gpu_configuration = ($controllers.Count -gt 1)
    dxdiag_path = $dxdiagPath
    note = "Adapter selection is proven by the renderer diagnostics, not inferred from this inventory."
}

$inventory | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 $OutputPath
Write-Host "GPU inventory written to $OutputPath"
