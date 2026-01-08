# 🐳 Docker Desktop Installation Guide (Windows)

## ნაბიჯი 1: System Requirements შემოწმება

### Windows-ის ვერსია:
- ✅ **Windows 10 64-bit**: Pro, Enterprise, ან Education (Build 19041 ან უფრო ახალი)
- ✅ **Windows 11 64-bit**
- ❌ Windows 10 Home (ძველი ვერსიები) - საჭიროა WSL 2

### Hardware:
- **RAM**: მინიმუმ 4GB (8GB რეკომენდებული speaker detection-სთვის)
- **CPU**: 64-bit processor with virtualization support
- **Disk Space**: 4GB+ თავისუფალი

### როგორ შევამოწმო Windows ვერსია?

1. დააჭირეთ `Windows Key + R`
2. აკრიფეთ: `winver`
3. დააჭირეთ Enter
4. ამოვა შეტყობინება Windows version-ით

**ან:**

1. დააჭირეთ `Windows Key + I` (Settings)
2. System → About
3. ნახეთ "Windows specifications"

---

## ნაბიჯი 2: Docker Desktop-ის ჩამოტვირთვა

### Option A: Automatic Download (რეკომენდებული)

მოდით ვჩამოვტვირთოთ installer:

```powershell
# PowerShell-ში გაუშვით:
Start-BitsTransfer -Source "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe" -Destination "$env:USERPROFILE\Downloads\DockerDesktopInstaller.exe"
```

ან უბრალოდ:

### Option B: Manual Download

**📥 Direct Download Link:**
```
https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe
```

**Size:** ~500-600 MB
**Location:** Downloads ფოლდერში შეინახება

---

## ნაბიჯი 3: Installation

### 1. გაუშვით Installer

- გადადით Downloads ფოლდერში
- Double-click: `Docker Desktop Installer.exe`
- თუ UAC prompt-ი გამოვა → დააჭირეთ **Yes**

### 2. Configuration

Installer გთხოვთ 2 option-ის არჩევას:

#### ✅ **Option 1: Use WSL 2 instead of Hyper-V** (რეკომენდებული)
```
[✓] Use WSL 2 instead of Hyper-V (recommended)
```
**რატომ?** უკეთესი performance და compatibility

#### ✅ **Option 2: Add shortcut to desktop**
```
[✓] Add shortcut to desktop
```

### 3. Install

- დააჭირეთ **OK**
- მოითმინეთ 5-10 წუთი (დამოკიდებულია internet-ის სიჩქარეზე)
- Progress bar გიჩვენებთ სტატუსს

### 4. Restart (აუცილებელია!)

როცა installation დასრულდება:
```
Installation succeeded
[Close and restart]
```

**⚠️ IMPORTANT:** კომპიუტერის restart აუცილებელია!

---

## ნაბიჯი 4: WSL 2 Setup (თუ საჭიროა)

თუ Docker-მა გითხრა "WSL 2 is not installed":

### Windows 11 / Windows 10 (Recent):

1. **გახსენით PowerShell როგორც Administrator:**
   - Windows Key → აკრიფეთ "PowerShell"
   - Right-click → "Run as Administrator"

2. **გაუშვით:**
   ```powershell
   wsl --install
   ```

3. **Restart Computer**

4. **შემოწმება:**
   ```powershell
   wsl --version
   ```

### თუ wsl --install არ მუშაობს:

```powershell
# Step 1: Enable WSL
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart

# Step 2: Enable Virtual Machine Platform
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

# Step 3: Restart computer
shutdown /r /t 0

# Step 4: Download WSL 2 kernel update (after restart)
# Go to: https://aka.ms/wsl2kernel
# Install: wsl_update_x64.msi

# Step 5: Set WSL 2 as default
wsl --set-default-version 2
```

---

## ნაბიჯი 5: Docker Desktop-ის გაშვება

### 1. Start Docker Desktop

- Desktop-ზე double-click: **Docker Desktop** icon
- ან Start Menu → "Docker Desktop"

### 2. First Launch

პირველ გაშვებისას:
1. **Service Agreement** → Accept
2. **Use recommended settings** → Continue
3. **Skip Tutorial** (ან გაიარეთ თუ გინდათ)

### 3. მოელოდეთ სანამ Started იქნება

System Tray-ში (ქვემოთ მარჯვნივ) Docker icon:
- 🟡 Yellow = Starting...
- 🟢 Green = Running ✅

**Status:** "Docker Desktop is running"

---

## ნაბიჯი 6: ვერიფიკაცია (შემოწმება)

### 1. გახსენით PowerShell (როგორც Administrator)

### 2. გაუშვით შემდეგი ბრძანებები:

```powershell
# Check Docker version
docker --version
```

**Expected Output:**
```
Docker version 24.x.x, build xxxxxxx
```

```powershell
# Check docker-compose
docker-compose --version
```

**Expected Output:**
```
Docker Compose version v2.x.x
```

```powershell
# Test Docker
docker run hello-world
```

**Expected Output:**
```
Hello from Docker!
This message shows that your installation appears to be working correctly.
```

---

## ნაბიჯი 7: Speaker Detection Setup

ახლა რომ Docker მუშაობს, დავაყენოთ Speaker Detection service!

### PowerShell-ში (project directory-ში):

```powershell
# Navigate to project
cd C:\Users\user\voiceover-vo

# Run setup script
.\setup_speaker_detection.bat
```

ან ხელით:

```powershell
# Build speaker detection container
docker-compose build speaker-detection

# Start service
docker-compose up -d speaker-detection

# Check status
docker ps

# Check logs
docker logs voyoutube-speaker-detection

# Test API
curl http://localhost:5002/health
```

---

## 🎯 ხშირი პრობლემები და გადაწყვეტილებები

### Problem 1: "Hardware assisted virtualization is not enabled"

**გადაწყვეტა:**
1. Restart computer
2. შედით BIOS-ში (F2, F10, ან DEL ჩვეულებრივ)
3. Enable: "Intel VT-x" ან "AMD-V" (Virtualization)
4. Save and Exit
5. Restart

### Problem 2: "WSL 2 installation is incomplete"

**გადაწყვეტა:**
```powershell
# Re-install WSL 2 kernel
# Download: https://aka.ms/wsl2kernel
# Install: wsl_update_x64.msi
# Restart Docker Desktop
```

### Problem 3: Docker Desktop არ იწყება

**გადაწყვეტა:**
```powershell
# Reset Docker Desktop
# System Tray → Docker Icon → Troubleshoot → Reset to factory defaults
```

### Problem 4: "Docker Desktop requires a newer WSL kernel version"

**გადაწყვეტა:**
```powershell
wsl --update
wsl --shutdown
# Restart Docker Desktop
```

### Problem 5: "Access denied" errors

**გადაწყვეტა:**
- გაუშვით PowerShell/cmd როგორც Administrator
- Docker Desktop-ს დაამატეთ Windows Firewall exception-ში

---

## 📊 Docker Desktop Settings (Optional Optimization)

### გახსენით Docker Desktop Settings:

System Tray → Docker Icon → Settings

### Resources (რესურსები):

```
Memory: 4GB (minimum) → 8GB (რეკომენდებული speaker detection-სთვის)
CPUs: 2 → 4 (როცა available)
Disk: 60GB
```

### Docker Engine (Advanced):

```json
{
  "builder": {
    "gc": {
      "enabled": true,
      "defaultKeepStorage": "20GB"
    }
  }
}
```

---

## ✅ შემოწმების Checklist

დარწმუნდით რომ ყველაფერი მუშაობს:

```powershell
# 1. Docker version
docker --version
# ✅ Output: Docker version 24.x.x

# 2. Docker is running
docker ps
# ✅ Output: CONTAINER ID   IMAGE   ...

# 3. Docker Compose
docker-compose --version
# ✅ Output: Docker Compose version v2.x.x

# 4. Test container
docker run hello-world
# ✅ Output: Hello from Docker!

# 5. WSL 2 (if using)
wsl --version
# ✅ Output: WSL version info
```

---

## 🚀 შემდეგი ნაბიჯები

თუ ყველაფერი მუშაობს:

```powershell
# Navigate to project
cd C:\Users\user\voiceover-vo

# Run speaker detection setup
.\setup_speaker_detection.bat
```

ეს script:
1. ✅ Build-ს speaker detection Docker image-ს
2. ✅ Starts container on port 5002
3. ✅ Tests service health
4. ✅ გიჩვენებთ როგორ გამოიყენოთ

---

## 📞 დახმარების საჭიროებისას

თუ რამე არ მუშაობს:

1. **Check Docker Desktop logs:**
   - Docker Desktop → Troubleshoot → View logs

2. **Check Windows Event Viewer:**
   - Windows Key + X → Event Viewer
   - Windows Logs → Application

3. **გამიგეთ და დაგეხმარებით!**

---

## 📚 დამატებითი რესურსები

- **Docker Official Docs:** https://docs.docker.com/desktop/windows/install/
- **WSL 2 Installation:** https://docs.microsoft.com/en-us/windows/wsl/install
- **Docker Desktop Troubleshooting:** https://docs.docker.com/desktop/troubleshoot/overview/

---

**მზად ხართ Docker-ის დასაინსტალირებლად? დავიწყოთ! 🚀**
