<#
.SYNOPSIS
Installs dependencies (Python, Git) and sets up the hbUtil bot for Windows.
#>

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "    OwO HuntBot Installer (hbUtil)       " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check/Install Git
if (!(Get-Command "git" -ErrorAction SilentlyContinue)) {
    Write-Host "[*] Git is not installed. Installing via winget..." -ForegroundColor Yellow
    winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[-] Failed to install Git. Please install it manually." -ForegroundColor Red
        exit
    }
    Write-Host "[+] Git installed successfully." -ForegroundColor Green
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
} else {
    Write-Host "[+] Git is already installed." -ForegroundColor Green
}

# 2. Check/Install Python
if (!(Get-Command "python" -ErrorAction SilentlyContinue)) {
    Write-Host "[*] Python is not installed. Installing via winget..." -ForegroundColor Yellow
    winget install --id Python.Python.3.11 -e --source winget --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[-] Failed to install Python. Please install it manually." -ForegroundColor Red
        exit
    }
    Write-Host "[+] Python installed successfully." -ForegroundColor Green
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
} else {
    Write-Host "[+] Python is already installed." -ForegroundColor Green
}

# 3. Define target directory
$desktopPath = [Environment]::GetFolderPath("Desktop")
$repoDir = Join-Path -Path $desktopPath -ChildPath "hbUtil"

# 4. Clone Repository
if (Test-Path -Path $repoDir) {
    Write-Host "[*] Directory 'hbUtil' already exists on your Desktop. Pulling latest updates..." -ForegroundColor Yellow
    Set-Location -Path $repoDir
    git pull
} else {
    Write-Host "[*] Downloading the bot to your Desktop..." -ForegroundColor Yellow
    Set-Location -Path $desktopPath
    git clone https://github.com/diazdroid/hbUtil.git
    Set-Location -Path "hbUtil"
}

# 5. Install Python Dependencies
Write-Host "[*] Installing Python dependencies..." -ForegroundColor Yellow
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# 6. Copy tokens.txt if not exists
if (!(Test-Path -Path "tokens.txt")) {
    Copy-Item "tokens.example.txt" "tokens.txt"
    Write-Host "[!] Created tokens.txt from example. Please edit it and add your Discord tokens." -ForegroundColor Magenta
}

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "    Installation Complete!               " -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Go to your Desktop, open the 'hbUtil' folder,"
Write-Host "Edit 'tokens.txt', and double-click 'run.bat' to start the bot." -ForegroundColor White
Write-Host ""

Read-Host -Prompt "Press Enter to exit"
