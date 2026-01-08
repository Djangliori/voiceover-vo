# 🔑 API Keys Setup - ნაბიჯ-ნაბიჯ გაიდი

ამ აპლიკაციას სჭირდება 3 **სავალდებულო** API key სრული ფუნქციონალისთვის.

---

## 📋 რა გვჭირდება

| API | დანიშნულება | ღირებულება | სავალდებულოა |
|-----|-------------|-------------|--------------|
| **Voicegain** | აუდიო ტრანსკრიპცია | ფასიანი (~$0.15/10წთ) | ✅ დიახ |
| **OpenAI** | ქართული თარგმანი | ფასიანი (~$0.05/10წთ) | ✅ დიახ |
| **Google Cloud** | ქართული TTS | $300 free credit | ✅ დიახ |
| RapidAPI | YouTube download | უფასო tier | ❌ არა (optional) |

**სულ ღირებულება:** ~$0.35 თითო 10-წუთიან ვიდეოზე

---

# 1️⃣ Voicegain API (ტრანსკრიპცია)

## რას აკეთებს?
აუდიო ფაილს გარდაქმნის ტექსტად timestamps-ებით და speaker diarization-ით.

## ნაბიჯები:

### ✅ ნაბიჯი 1: რეგისტრაცია
1. გადადით: **https://console.voicegain.ai**
2. დააჭირეთ **"Sign Up"** ან **"Get Started"**
3. შეავსეთ:
   - სახელი
   - Email
   - პაროლი
4. დაადასტურეთ email (შეამოწმეთ inbox)

### ✅ ნაბიჯი 2: API Key მიღება
1. შედით console-ში: https://console.voicegain.ai
2. მენიუში იპოვეთ **"API Keys"** ან **"Settings"**
3. დააჭირეთ **"Create API Key"** ან **"Generate JWT Token"**
4. **დააკოპირეთ** JWT Token (დიდი string, რომელიც იწყება `eyJ...`)

### ✅ ნაბიჯი 3: ჩასმა .env ფაილში
1. გახსენით: `C:\Users\user\voiceover-vo\.env`
2. იპოვეთ ხაზი: `VOICEGAIN_API_KEY=your_voicegain_jwt_token_here`
3. შეცვალეთ:
   ```
   VOICEGAIN_API_KEY=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI...
   ```

### 💰 ფასები
- **Free Trial**: შეიძლება იყოს limited credits
- **Pay-as-you-go**: დაახლოებით $0.15 per 10 minutes audio
- შეამოწმეთ: https://www.voicegain.ai/pricing

---

# 2️⃣ OpenAI API (თარგმანი)

## რას აკეთებს?
ინგლისურ ტექსტს თარგმნის ქართულ ენაზე GPT models-ის გამოყენებით.

## ნაბიჯები:

### ✅ ნაბიჯი 1: ექაუნთის შექმნა
1. გადადით: **https://platform.openai.com/**
2. დააჭირეთ **"Sign Up"**
3. შეავსეთ რეგისტრაცია (შეგიძლიათ Google-ით)
4. დაადასტურეთ email

### ✅ ნაბიჯი 2: Payment Method დამატება
⚠️ **მნიშვნელოვანი**: OpenAI API საჭიროებს payment method-ს (თუნდაც free credit-ის გამოსაყენებლად)

1. გადადით: https://platform.openai.com/account/billing
2. დააჭირეთ **"Add payment method"**
3. დაამატეთ credit/debit card
4. ტოპ-აპი: **$5-10** საკმარისია ტესტირებისთვის

### ✅ ნაბიჯი 3: API Key შექმნა
1. გადადით: **https://platform.openai.com/api-keys**
2. დააჭირეთ **"+ Create new secret key"**
3. დაარქვით სახელი: `voiceover-app`
4. **დააკოპირეთ key** (იწყება `sk-proj-` ან `sk-`)

   ⚠️ **გაფრთხილება:** key მხოლოდ ერთხელ გამოჩნდება! დააკოპირეთ ახლავე!

### ✅ ნაბიჯი 4: ჩასმა .env ფაილში
1. გახსენით: `C:\Users\user\voiceover-vo\.env`
2. იპოვეთ: `OPENAI_API_KEY=your_openai_api_key_here`
3. შეცვალეთ:
   ```
   OPENAI_API_KEY=sk-proj-abc123xyz789...
   ```

### 💰 ფასები
- **$5 free credit** (ახალ ექაუნთებზე - შემოწმებული credit card საჭიროა)
- **Pay-as-you-go**: ~$0.002 per 1K tokens (~$0.05 per 10min video)
- ფასები: https://openai.com/pricing

---

# 3️⃣ Google Cloud Text-to-Speech (ქართული ხმოვანი)

## რას აკეთებს?
ქართულ ტექსტს გარდაქმნის ნატურალურ ხმოვან აუდიოდ.

## ნაბიჯები:

### ✅ ნაბიჯი 1: Google Cloud ექაუნთი
1. გადადით: **https://console.cloud.google.com/**
2. შედით Google ექაუნთით
3. თუ პირველად იყენებთ, დაეთანხმეთ Terms of Service

### ✅ ნაბიჯი 2: Free Credit აქტივაცია
1. მენიუში დააჭირეთ **"Billing"**
2. დააჭირეთ **"Activate"** ან **"Start Free Trial"**
3. დაამატეთ credit/debit card (არ მოგიჭრით თანხა)
4. მიიღებთ **$300 free credit** 90 დღით!

### ✅ ნაბიჯი 3: ახალი პროექტის შექმნა
1. ზემოთ (toolbar-ში) დააჭირეთ project dropdown
2. **"New Project"**
3. სახელი: `voiceover-app`
4. დააჭირეთ **"Create"**
5. დარწმუნდით რომ ახალი project არჩეულია

### ✅ ნაბიჯი 4: Text-to-Speech API ჩართვა
1. გადადით: **https://console.cloud.google.com/apis/library**
2. მოძებნეთ: **"Cloud Text-to-Speech API"**
3. დააჭირეთ API-ზე
4. დააჭირეთ **"Enable"** ღილაკს
5. დაელოდეთ (30 წამი - 1 წუთი)

### ✅ ნაბიჯი 5: Service Account შექმნა
1. გადადით: **https://console.cloud.google.com/iam-admin/serviceaccounts**
2. დააჭირეთ **"+ Create Service Account"**
3. შეავსეთ:
   - **Service account name**: `voiceover-tts`
   - **Description**: `For Georgian voiceover app`
4. დააჭირეთ **"Create and Continue"**

### ✅ ნაბიჯი 6: როლის მინიჭება
1. **Select a role** dropdown-ში:
2. მოძებნეთ და აირჩიეთ: **"Cloud Text-to-Speech User"**
3. დააჭირეთ **"Continue"**
4. დააჭირეთ **"Done"**

### ✅ ნაბიჯი 7: JSON Key-ის გენერაცია
1. Service Accounts სიაში იპოვეთ თქვენი ახალი account
2. დააჭირეთ email-ზე (voiceover-tts@...)
3. გადადით **"Keys"** ტაბზე
4. დააჭირეთ **"Add Key"** → **"Create new key"**
5. აირჩიეთ **"JSON"**
6. დააჭირეთ **"Create"**
7. **JSON ფაილი ჩამოიტვირთება** (მაგ: `voiceover-app-abc123.json`)

### ✅ ნაბიჯი 8: JSON ფაილის გადატანა
1. **იპოვეთ** ჩამოტვირთული JSON ფაილი (Downloads-ში)
2. **გადაარქვით**: `google-credentials.json`
3. **გადაიტანეთ** `C:\Users\user\voiceover-vo\` საქაღალდეში

### ✅ ნაბიჯი 9: .env ფაილის განახლება
1. გახსენით: `C:\Users\user\voiceover-vo\.env`
2. იპოვეთ: `GOOGLE_APPLICATION_CREDENTIALS=/path/to/google-credentials.json`
3. შეცვალეთ:
   ```
   GOOGLE_APPLICATION_CREDENTIALS=C:/Users/user/voiceover-vo/google-credentials.json
   ```
   ან Windows-style path:
   ```
   GOOGLE_APPLICATION_CREDENTIALS=C:\Users\user\voiceover-vo\google-credentials.json
   ```

### 💰 ფასები
- **$300 Free Credit** (90 days) - ახალ ექაუნთებზე
- **Pay-as-you-go**: $16 per 1M characters (~$0.15 per 10min video)
- **Free tier**: 0-4M characters/month უფასო
- ფასები: https://cloud.google.com/text-to-speech/pricing

---

# 4️⃣ RapidAPI (Optional - YouTube Download)

## რას აკეთებს?
YouTube ვიდეოების ჩამოტვირთვა (Fallback: yt-dlp).

## ნაბიჯები:

### ✅ ნაბიჯი 1: რეგისტრაცია
1. გადადით: **https://rapidapi.com/**
2. დააჭირეთ **"Sign Up"**
3. რეგისტრაცია Google/GitHub-ით

### ✅ ნაბიჯი 2: YouTube API-ს პოვნა
1. მოძებნეთ: **"YouTube Video Downloader"** ან **"YouTube Data"**
2. რეკომენდებული: **"YouTube Video Downloader"** by h0p3rwe
3. დააჭირეთ API-ზე

### ✅ ნაბიჯი 3: Subscribe
1. დააჭირეთ **"Subscribe to Test"**
2. აირჩიეთ **"Basic"** plan (Free)
3. დაადასტურეთ

### ✅ ნაბიჯი 4: API Key კოპირება
1. API-ს გვერდზე, მარჯვნივ იხილავთ **"X-RapidAPI-Key"**
2. **დააკოპირეთ** key

### ✅ ნაბიჯი 5: ჩასმა .env ფაილში
1. გახსენით: `C:\Users\user\voiceover-vo\.env`
2. იპოვეთ: `RAPIDAPI_KEY=your_rapidapi_key_here`
3. შეცვალეთ:
   ```
   RAPIDAPI_KEY=abc123xyz789...
   ```

### 💰 ფასები
- **Free tier**: 100-500 requests/month
- თუ არ კონფიგურირებთ, აპი გამოიყენებს **yt-dlp** fallback-ს

---

# ✅ დასრულების შემდეგ

## შეამოწმეთ .env ფაილი

თქვენი `.env` ფაილი უნდა გამოიყურებოდეს ასე:

```env
# Voicegain API for transcription
VOICEGAIN_API_KEY=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI...

# OpenAI API for Georgian translation
OPENAI_API_KEY=sk-proj-abc123xyz789...

# Google Cloud TTS
GOOGLE_APPLICATION_CREDENTIALS=C:/Users/user/voiceover-vo/google-credentials.json

# RapidAPI (optional)
RAPIDAPI_KEY=abc123xyz789...

# Flask Configuration
SECRET_KEY=b6dbb54632f91425d2d981de13aeb9b28267a6e5a77cfa959f47ddb196018833
FLASK_PORT=5001
FLASK_ENV=development

# Database
DATABASE_URL=sqlite:///voiceover.db

# Audio Settings
ORIGINAL_AUDIO_VOLUME=0.05
VOICEOVER_VOLUME=1.0
```

## ფაილების სტრუქტურა

```
C:\Users\user\voiceover-vo\
├── .env                            ← API keys აქ არის
├── google-credentials.json         ← Google Cloud JSON აქ უნდა იყოს
├── app.py
└── ...
```

---

# 🚀 ტესტირება

## 1. გადაამოწმეთ ფაილები არსებობენ:

```bash
# Git Bash-ში
cd /c/Users/user/voiceover-vo
ls .env
ls google-credentials.json
```

## 2. გადატვირთეთ აპლიკაცია:

თუ უკვე გაშვებულია, **CTRL+C** და ხელახლა:

```bash
PYTHONIOENCODING=utf-8 python app.py
```

## 3. შეამოწმეთ ლოგები:

უნდა დაინახოთ:
- ✅ **არა**: "API key missing" errors
- ✅ **არა**: "Google credentials not found"
- ✅ **კი**: "Server starting successfully"

---

# 🆘 Troubleshooting

## "Voicegain API error"
- შეამოწმეთ key სწორად არის დაკოპირებული
- დარწმუნდით რომ ექაუნთზე გაქვთ credit
- ტესტი: https://console.voicegain.ai

## "OpenAI authentication failed"
- დარწმუნდით key იწყება `sk-` ან `sk-proj-`
- შეამოწმეთ billing page-ზე არის თუ არა payment method
- ტესტი: https://platform.openai.com/account/api-keys

## "Google credentials error"
- შეამოწმეთ JSON ფაილი არსებობს სწორ path-ზე
- შეამოწმეთ .env-ში path სწორია (forward slashes: `/`)
- გახსენით JSON და დარწმუნდით რომ valid JSON არის

## "RapidAPI rate limit"
- არ არის პრობლემა - გამოიყენებს yt-dlp fallback-ს
- ან Subscribe უფასო tier-ზე

---

# 💵 ბიუჯეტის კალკულაცია

## 10-წუთიანი ვიდეო:
- Voicegain: ~$0.15
- OpenAI: ~$0.05
- Google TTS: ~$0.15
- **სულ: ~$0.35 per video**

## $50-ით:
- შეგიძლიათ დაამუშავოთ: **~140 videos** (10 წთ თითო)
- $300 Google credit-ით: **~850 videos** (თუ მხოლოდ TTS-ის ფასებს ვითვლით)

---

# ✅ შემდეგი ნაბიჯები

როცა ყველა API key კონფიგურირებულია:

1. ✅ დარწმუნდით **ffmpeg** დაინსტალირებული
2. ✅ გადატვირთეთ **აპლიკაცია**
3. ✅ გახსენით **http://localhost:5001**
4. ✅ ატვირთეთ **სატესტო YouTube URL**
5. 🎉 **ისიამოვნეთ ქართული voiceover-ით!**

---

გისურვებთ წარმატებას! 🇬🇪

თუ პრობლემები გაქვთ, შეგიძლიათ დამიკავშირდეთ!
