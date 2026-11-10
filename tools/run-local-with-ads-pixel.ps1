$pixelLine = Get-Content -LiteralPath (Join-Path $PSScriptRoot '..\.env') |
    Where-Object { $_ -match '^OPENAI_ADS_PIXEL_ID=' } |
    Select-Object -First 1
if (-not $pixelLine) { throw 'OPENAI_ADS_PIXEL_ID is missing from local .env' }
$env:OPENAI_ADS_PIXEL_ID = $pixelLine.Substring('OPENAI_ADS_PIXEL_ID='.Length)
& (Join-Path $PSScriptRoot '..\.venv\Scripts\python.exe') (Join-Path $PSScriptRoot '..\app.py')
