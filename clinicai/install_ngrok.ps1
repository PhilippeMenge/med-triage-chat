# Script para instalar ngrok no Windows
Write-Host "🌐 Instalando ngrok..." -ForegroundColor Green

# Criar diretório para ngrok
$ngrokDir = "C:\ngrok"
if (-not (Test-Path $ngrokDir)) {
    New-Item -ItemType Directory -Path $ngrokDir -Force
    Write-Host "✅ Diretório criado: $ngrokDir" -ForegroundColor Green
}

# Baixar ngrok
$ngrokUrl = "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip"
$zipPath = "$ngrokDir\ngrok.zip"
$exePath = "$ngrokDir\ngrok.exe"

try {
    Write-Host "⬇️  Baixando ngrok..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri $ngrokUrl -OutFile $zipPath
    
    Write-Host "📦 Extraindo arquivo..." -ForegroundColor Yellow
    Expand-Archive -Path $zipPath -DestinationPath $ngrokDir -Force
    
    # Remover zip
    Remove-Item $zipPath -Force
    
    # Verificar se foi instalado
    if (Test-Path $exePath) {
        Write-Host "✅ ngrok instalado com sucesso!" -ForegroundColor Green
        Write-Host "📍 Localização: $exePath" -ForegroundColor Cyan
        
        # Adicionar ao PATH temporariamente
        $env:PATH += ";$ngrokDir"
        
        Write-Host "🎯 Para usar o ngrok:" -ForegroundColor White
        Write-Host "   1. Execute: $exePath http 8080" -ForegroundColor Gray
        Write-Host "   2. Ou adicione $ngrokDir ao PATH permanente" -ForegroundColor Gray
        Write-Host "   3. Depois use: ngrok http 8080" -ForegroundColor Gray
        
        # Testar instalação
        Write-Host "`n🧪 Testando instalação..." -ForegroundColor Yellow
        & $exePath version
        
    } else {
        Write-Host "❌ Falha na instalação" -ForegroundColor Red
    }
    
} catch {
    Write-Host "❌ Erro durante a instalação: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "🔧 Solução manual:" -ForegroundColor Yellow
    Write-Host "   1. Acesse: https://ngrok.com/download" -ForegroundColor Gray
    Write-Host "   2. Baixe ngrok para Windows" -ForegroundColor Gray
    Write-Host "   3. Extraia para C:\ngrok\" -ForegroundColor Gray
}

Write-Host "`n🏥 Próximos passos:" -ForegroundColor Green
Write-Host "   1. Execute sua aplicação: python clinicai_whatsapp.py" -ForegroundColor Gray
Write-Host "   2. Em outro terminal: ngrok http 8080" -ForegroundColor Gray
Write-Host "   3. Configure a URL no Meta for Developers" -ForegroundColor Gray
