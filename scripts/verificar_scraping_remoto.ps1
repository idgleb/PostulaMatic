# Script PowerShell para verificar scraping activo en el servidor remoto

param(
    [string]$SshKey = "$env:USERPROFILE\.ssh\postulamatic_win_ed25519",
    [string]$SshUser = "deploy",
    [string]$SshHost = "178.156.188.95"
)

Write-Host "🔍 Conectando al servidor para verificar scraping activo..." -ForegroundColor Cyan
Write-Host "📡 Servidor: ${SshUser}@${SshHost}" -ForegroundColor Cyan
Write-Host ""

$sshCommand = @"
cd /home/deploy/postulamatic || cd ~/postulamatic || exit 1

echo "📋 Verificando estado del scraping..."
echo ""

# Verificar lock y estado de la tarea
docker exec postulamatic-postulamatic_web-1 python manage.py check_active_scraping

echo ""
echo "📋 Si hay un lock huérfano, puedes liberarlo con:"
echo "docker exec postulamatic-postulamatic_web-1 python manage.py check_scraping_lock --force-release"
"@

ssh -i "$SshKey" "$SshUser@$SshHost" $sshCommand

Write-Host ""
Write-Host "✅ Verificación completada" -ForegroundColor Green

