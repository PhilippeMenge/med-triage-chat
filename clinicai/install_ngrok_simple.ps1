# Script simples para instalar ngrok
Write-Host "🌐 Instalando ngrok..." -ForegroundColor Green

$ngrokDir = "C:\ngrok"
$ngrokUrl = "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip"
$zipPath = "$ngrokDir\ngrok.zip"

# Criar diretório
New-Item -ItemType Directory -Path $ngrokDir -Force | Out-Null

try {
    Write-Host "⬇️  Baixando ngrok..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri $ngrokUrl -OutFile $zipPath
    
    Write-Host "📦 Extraindo..." -ForegroundColor Yellow
    Expand-Archive -Path $zipPath -DestinationPath $ngrokDir -Force
    
    Remove-Item $zipPath -Force
    
    if (Test-Path "$ngrokDir\ngrok.exe") {
        Write-Host "✅ ngrok instalado em: $ngrokDir\ngrok.exe" -ForegroundColor Green
        Write-Host "🎯 Use: $ngrokDir\ngrok.exe http 8080" -ForegroundColor Cyan
    }
}
catch {
    Write-Host "❌ Erro: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "🔧 Baixe manualmente: https://ngrok.com/download" -ForegroundColor Yellow
}
