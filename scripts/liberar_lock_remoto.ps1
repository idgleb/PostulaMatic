# Script PowerShell para liberar lock huérfano en el servidor remoto

param(
    [string]$SshKey = "$env:USERPROFILE\.ssh\postulamatic_win_ed25519",
    [string]$SshUser = "deploy",
    [string]$SshHost = "178.156.188.95"
)

Write-Host "🔓 Conectando al servidor para liberar lock huérfano..." -ForegroundColor Yellow
Write-Host "📡 Servidor: ${SshUser}@${SshHost}" -ForegroundColor Cyan
Write-Host ""

$sshCommand = @"
cd /home/deploy/postulamatic || cd ~/postulamatic || exit 1

echo "📋 Verificando estado actual del lock..."
echo ""
docker exec postulamatic-postulamatic_web-1 python manage.py check_active_scraping

echo ""
echo "🔓 Liberando lock huérfano..."
echo ""
docker exec postulamatic-postulamatic_web-1 python manage.py check_scraping_lock --force-release

echo ""
echo "📋 Verificando estado después de liberar..."
echo ""
docker exec postulamatic-postulamatic_web-1 python manage.py check_active_scraping
"@

ssh -i "$SshKey" "$SshUser@$SshHost" $sshCommand

Write-Host ""
Write-Host "✅ Proceso completado" -ForegroundColor Green

