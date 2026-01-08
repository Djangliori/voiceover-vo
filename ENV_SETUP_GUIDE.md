# 🔐 Environment Variables Setup Guide

## როგორ მუშაობს .env ფაილები?

### **არსებული სტრუქტურა:**

```
voiceover-vo/
├── .env                  ❌ GIT-ზე არ აიტვირთება (sensitive data)
├── .env.example          ✅ GIT-ზე აიტვირთება (template)
├── .env.backup          ❌ Local backup only
└── .gitignore           ✅ Contains: .env, .env.local, .env.backup
```

---

## 🔒 რა არის .gitignore-ში?

```bash
# .gitignore
.env
.env.local
.env.backup
*.key
google-credentials.json
```

**მნიშვნელობა:**
- ✅ `.env` და sensitive ფაილები **არასდროს** აიტვირთება Git-ზე
- ✅ `.env.example` **კი** აიტვირთება (template უსაფრთხო მნიშვნელობებით)

---

## 📁 .env vs .env.example

### **.env** (თქვენი ფაილი - პირადი)
```bash
GEMINI_API_KEY=AIzaSyAsrBm3t4sxqdoOv3QTKlGJVO-POhHQruM  # ნამდვილი key
RAPIDAPI_KEY=a5f2e863d0msh65bb2858c77899dp1117a7jsn51e5b3952799
SECRET_KEY=b6dbb54632f91425d2d981de13aeb9b28267a6e5a77cfa959f47ddb196018833
```

### **.env.example** (Template - Git-ზე)
```bash
GEMINI_API_KEY=your_gemini_api_key_here  # placeholder
RAPIDAPI_KEY=your_rapidapi_key_here
SECRET_KEY=your_secret_key_here_generate_with_secrets_token_hex
```

---

## 💾 როგორ ინახება თქვენი API Keys?

### **Option 1: Local Backup (რეკომენდებული)**

```bash
# Backup-ის შექმნა
cp .env .env.backup

# კიდევ უფრო უსაფრთხო - დაშიფრული backup
# TODO: დავამატებ script-ს
```

### **Option 2: Password Manager** (ყველაზე უსაფრთხო)

API Keys შეინახეთ:
- **1Password**
- **Bitwarden**
- **LastPass**

**სტრუქტურა:**
```
Entry: "VoYouTube API Keys"
├── GEMINI_API_KEY: AIzaSy...
├── RAPIDAPI_KEY: a5f2e8...
├── SECRET_KEY: b6dbb5...
└── Notes: .env file content (backup)
```

### **Option 3: Encrypted File** (Advanced)

```bash
# Encrypt .env file
# TODO: დავამატებ encryption script-ს
```

---

## 🔄 როგორ მუშაობს სისტემა?

### **Scenario 1: პირველი Setup (ახალი კომპიუტერი)**

```bash
# 1. Clone repository
git clone https://github.com/yourusername/voiceover-vo.git
cd voiceover-vo

# 2. Copy template
cp .env.example .env

# 3. Edit .env with your actual API keys
notepad .env

# ან
code .env  # VS Code
```

### **Scenario 2: Git Commit**

```bash
# თქვენი .env არასდროს აიტვირთება
git add .
git commit -m "Add new feature"
git push

# რა აიტვირთება:
# ✅ .env.example (template)
# ❌ .env (თქვენი ფაილი)
```

### **Scenario 3: კიდევ ერთი კომპიუტერი/სერვერი**

```bash
# 1. Pull latest code
git pull

# 2. .env არ არსებობს (არ აიტვირთა)
# 3. Copy template
cp .env.example .env

# 4. შეიყვანეთ API keys (ხელით ან password manager-დან)
```

---

## 🛠️ .env Setup Script (ავტომატური)

შევქმენი script რომელიც დაგეხმარებათ:

### **setup_env.bat** (Windows)

```batch
@echo off
echo ====================================
echo   .env Setup Helper
echo ====================================
echo.

REM Check if .env already exists
if exist .env (
    echo [WARNING] .env already exists!
    echo.
    choice /C YN /M "Do you want to backup current .env"
    if errorlevel 2 goto skip_backup
    copy .env .env.backup.%date:~-4,4%%date:~-10,2%%date:~-7,2%
    echo [OK] Backup created: .env.backup.%date:~-4,4%%date:~-10,2%%date:~-7,2%
    :skip_backup
    echo.
    choice /C YN /M "Do you want to overwrite .env from template"
    if errorlevel 2 goto end
)

REM Create .env from template
copy .env.example .env
echo [OK] Created .env from template

echo.
echo ====================================
echo   Next Steps:
echo ====================================
echo 1. Edit .env file with your API keys
echo 2. Required keys:
echo    - GEMINI_API_KEY
echo    - RAPIDAPI_KEY
echo    - SECRET_KEY (generate new)
echo.
echo To generate SECRET_KEY:
echo   python -c "import secrets; print(secrets.token_hex(32))"
echo.
echo To edit .env:
echo   notepad .env
echo.
:end
pause
```

---

## 📋 API Keys Inventory (რა გჭირდება?)

### **მინიმალური (Local Development):**

```bash
✅ GEMINI_API_KEY         # Translation (FREE)
✅ RAPIDAPI_KEY           # Video download
✅ SECRET_KEY             # Flask security
✅ ADMIN_EMAIL            # Admin login
✅ ADMIN_PASSWORD         # Admin login
```

### **Optional (Enhanced Features):**

```bash
⭐ GOOGLE_APPLICATION_CREDENTIALS  # Gemini TTS (if using)
⭐ VOICEGAIN_API_KEY              # Advanced transcription
⭐ HUGGING_FACE_TOKEN             # Better speaker detection
⭐ OPENAI_API_KEY                 # Alternative translation
```

### **Production Only:**

```bash
🚀 DATABASE_URL           # PostgreSQL
🚀 REDIS_URL              # Cache & queue
🚀 R2_ACCESS_KEY_ID       # Cloud storage
🚀 R2_SECRET_ACCESS_KEY   # Cloud storage
```

---

## 🔐 უსაფრთხოება (Security Best Practices)

### ✅ DO:

1. **არასდროს commit-ოთ .env**
   ```bash
   # .gitignore უკვე შეიცავს .env-ს
   git status  # არ უნდა ჩანდეს .env
   ```

2. **Generate secure SECRET_KEY**
   ```python
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

3. **Backup .env რეგულარულად**
   ```bash
   cp .env .env.backup
   # Store backup in password manager
   ```

4. **Use environment-specific files**
   ```bash
   .env.development   # Local
   .env.production    # Production
   .env.test          # Testing
   ```

### ❌ DON'T:

1. **არასდროს share .env Slack/Discord/Email-ში**
2. **არასდროს commit-ოთ API keys**
3. **არასდროს paste-ოთ .env public-ად**
4. **არასდროს screenshot-ოთ .env**

---

## 🔄 Restore Process (როცა API Keys დაკარგავთ)

### **Option 1: Local Backup**

```bash
# Restore from backup
cp .env.backup .env
```

### **Option 2: Password Manager**

1. გახსენით Password Manager
2. იპოვეთ "VoYouTube API Keys"
3. Copy-paste თითოეული key .env-ში

### **Option 3: Re-generate Keys**

თუ backup არ გაქვთ:

1. **GEMINI_API_KEY**: https://makersuite.google.com/app/apikey
2. **RAPIDAPI_KEY**: https://rapidapi.com/hub (Account → Apps)
3. **SECRET_KEY**: `python -c "import secrets; print(secrets.token_hex(32))"`
4. **VOICEGAIN_API_KEY**: https://console.voicegain.ai

---

## 📝 Migration Script (Old → New)

თუ .env სტრუქტურა შეიცვალა:

```bash
# მიგრაცია ძველი .env-დან ახალში
python migrate_env.py
```

**ეს script:**
1. ✅ წაიკითხავს ძველ .env-ს
2. ✅ დააკოპირებს ყველა key-ს ახალ template-ში
3. ✅ დაამატებს ახალ variables-ს default მნიშვნელობებით
4. ✅ შექმნის backup-ს

---

## 🎯 Quick Reference

| File | Purpose | In Git? | Contains Secrets? |
|------|---------|---------|-------------------|
| `.env` | Your actual config | ❌ No | ✅ Yes |
| `.env.example` | Template | ✅ Yes | ❌ No |
| `.env.backup` | Local backup | ❌ No | ✅ Yes |
| `.gitignore` | Git exclusions | ✅ Yes | ❌ No |

---

## ❓ FAQ

### **Q: .env-ს შეცვლის შემდეგ რა უნდა გავაკეთო?**
A: Restart Flask app (Ctrl+C → `python app.py`)

### **Q: როგორ შევამოწმო რომელი keys არის configured?**
A: გაუშვით: `python check_setup.py`

### **Q: .env-ი Git-ზე რომ არ აიტვირთოს როგორ დავრწმუნდე?**
A: `git status` - არ უნდა ჩანდეს `.env`

### **Q: თუ შემთხვევით .env commit-დ გავაკეთე?**
A:
```bash
# Remove from git (but keep locally)
git rm --cached .env
git commit -m "Remove .env from git"
git push

# IMPORTANT: Regenerate ALL API keys (compromised!)
```

### **Q: Production-ში როგორ ვამატებ environment variables?**
A:
- **Railway**: Dashboard → Variables tab
- **Render**: Dashboard → Environment
- **Heroku**: `heroku config:set KEY=value`

---

## 🚀 Summary

**რას აკეთებს სისტემა:**
1. ✅ `.env` - თქვენი secrets (local only, Git-ზე არა)
2. ✅ `.env.example` - template (Git-ზე კი, secrets-ის გარეშე)
3. ✅ `.gitignore` - იცავს `.env`-ს Git commit-ისგან

**რა უნდა გააკეთოთ თქვენ:**
1. ✅ შეინახეთ `.env` backup password manager-ში
2. ✅ არასდროს commit-ოთ `.env`
3. ✅ გამოიყენეთ `.env.example` როგორც template

**ყველაფერი უსაფრთხოა! 🔐**
