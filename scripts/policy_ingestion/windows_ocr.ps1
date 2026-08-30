param(
    [Parameter(Mandatory = $true)][string]$InputDirectory,
    [Parameter(Mandatory = $true)][string]$OutputJson,
    [string]$Language = "ja"
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Runtime.WindowsRuntime
[Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null
[Windows.Globalization.Language, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null
[Windows.Storage.StorageFile, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null

$asTaskMethods = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq "AsTask" -and $_.IsGenericMethod -and $_.GetParameters().Count -eq 1
}
$asTaskMethod = $asTaskMethods | Select-Object -First 1

function Await-WinRt($operation, [Type]$resultType) {
    $task = $asTaskMethod.MakeGenericMethod($resultType).Invoke($null, @($operation))
    $task.Wait()
    return $task.Result
}

$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage(
    [Windows.Globalization.Language]::new($Language)
)
if ($null -eq $engine) {
    throw "Windows OCR language '$Language' is not installed."
}

$records = @()
$images = Get-ChildItem -LiteralPath $InputDirectory -File -Filter "*.png" | Sort-Object Name
foreach ($image in $images) {
    $storageFile = Await-WinRt ([Windows.Storage.StorageFile]::GetFileFromPathAsync($image.FullName)) ([Windows.Storage.StorageFile])
    $stream = Await-WinRt ($storageFile.OpenReadAsync()) ([Windows.Storage.Streams.IRandomAccessStreamWithContentType])
    $decoder = Await-WinRt ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
    $bitmap = Await-WinRt ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
    $result = Await-WinRt ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])

    $lineRecords = @()
    foreach ($line in $result.Lines) {
        $words = @()
        foreach ($word in $line.Words) {
            $rect = $word.BoundingRect
            $words += [ordered]@{
                text = $word.Text
                x = [math]::Round($rect.X, 2)
                y = [math]::Round($rect.Y, 2)
                width = [math]::Round($rect.Width, 2)
                height = [math]::Round($rect.Height, 2)
            }
        }
        $lineRecords += [ordered]@{ text = $line.Text; words = $words }
    }
    $pageNumber = 0
    if ($image.BaseName -match '(\d+)$') { $pageNumber = [int]$Matches[1] }
    $records += [ordered]@{
        page = $pageNumber
        image = $image.Name
        text = $result.Text
        lines = $lineRecords
    }
    $stream.Dispose()
    $bitmap.Dispose()
}

$json = $records | ConvertTo-Json -Depth 8
[System.IO.File]::WriteAllText($OutputJson, $json, [System.Text.UTF8Encoding]::new($false))

