# CI/CD Pipeline Setup Complete! 🚀

სრული CI/CD pipeline დამატებულია GitHub Actions-ით.

## 📦 რა შეიქმნა

### **GitHub Actions Workflows** (7 workflows)

```
.github/
├── workflows/
│   ├── ci.yml              # Main CI: tests, linting, security
│   ├── deploy.yml          # CD: deployment to production
│   ├── code-quality.yml    # Code quality analysis
│   ├── pr-checks.yml       # PR validation & automation
│   └── stale.yml           # Auto-close stale issues/PRs
├── dependabot.yml          # Automated dependency updates
└── labeler.yml             # Auto-label PRs based on files
```

---

## 🔄 **Workflow Details**

### 1️⃣ **CI Workflow** (`ci.yml`)

**Triggers:**
- Push to `main` or `develop`
- Pull requests to `main` or `develop`
- Manual trigger

**Jobs:**
1. **Linting & Code Quality**
   - ✅ Black (code formatting)
   - ✅ isort (import sorting)
   - ✅ Flake8 (linting)
   - ✅ Pylint (advanced linting)
   - ✅ MyPy (type checking)

2. **Security Scanning**
   - ✅ Bandit (security vulnerabilities)
   - ✅ Safety (dependency vulnerabilities)

3. **Unit Tests**
   - ✅ Tests on Python 3.9, 3.10, 3.11
   - ✅ Fast, isolated unit tests

4. **Integration Tests**
   - ✅ Tests with Redis service
   - ✅ API endpoint tests

5. **Code Coverage**
   - ✅ Coverage report generation
   - ✅ Upload to Codecov
   - ✅ Minimum 80% threshold

6. **Build Check**
   - ✅ Application startup test
   - ✅ Dependency check

**Status Badge:**
```markdown
![CI Status](https://github.com/speudoname/georgian-voiceover-app/workflows/CI%20-%20Tests%20%26%20Quality%20Checks/badge.svg)
```

---

### 2️⃣ **CD Workflow** (`deploy.yml`)

**Triggers:**
- Push to `main` branch
- Git tags `v*.*.*`
- Manual trigger

**Jobs:**
1. **Pre-deployment Checks**
   - Smoke tests
   - Security scan
   - Secrets detection

2. **Build Docker Image**
   - Build and push to GitHub Container Registry
   - Multi-platform support
   - Cache optimization

3. **Deploy to Railway**
   - Deploy web service
   - Deploy Celery worker
   - Health check verification

4. **Database Migrations**
   - Run Alembic migrations
   - Backup database (optional)

5. **Post-deployment Checks**
   - Health endpoint verification
   - API endpoint smoke tests
   - Production validation

6. **Create GitHub Release**
   - Auto-generate changelog
   - Create release notes
   - Attach artifacts

7. **Notifications**
   - Slack notifications
   - Discord notifications
   - Email alerts (optional)

8. **Rollback on Failure**
   - Automatic rollback trigger
   - Create incident issue

**Required Secrets:**
```bash
RAILWAY_TOKEN          # Railway deployment token
CODECOV_TOKEN          # Codecov upload token (optional)
SLACK_WEBHOOK          # Slack notifications (optional)
DISCORD_WEBHOOK        # Discord notifications (optional)
RENDER_DEPLOY_HOOK     # Render deployment (alternative)
HEROKU_API_KEY         # Heroku deployment (alternative)
```

---

### 3️⃣ **Code Quality Workflow** (`code-quality.yml`)

**Triggers:**
- Pull requests
- Weekly schedule (Monday 9am UTC)
- Manual trigger

**Jobs:**
1. **Quality Analysis**
   - Radon (cyclomatic complexity)
   - Maintainability index

2. **SonarCloud Analysis**
   - Code smells detection
   - Bug detection
   - Security hotspots

3. **Dependency Audit**
   - pip-audit for vulnerabilities
   - License compliance check

4. **Code Duplication**
   - PMD CPD analysis
   - Duplication reporting

5. **PR Comments**
   - Auto-comment quality reports
   - Coverage comparison

---

### 4️⃣ **PR Checks Workflow** (`pr-checks.yml`)

**Triggers:**
- Pull request opened/updated

**Jobs:**
1. **PR Validation**
   - Title format check (conventional commits)
   - Description length check

2. **Auto-labeling**
   - Label by changed files
   - Label by PR size (XS, S, M, L, XL)

3. **Breaking Changes Detection**
   - Auto-label breaking changes
   - Warning comments

4. **Coverage Check**
   - Compare coverage with base branch
   - Comment coverage diff

5. **TODO Detection**
   - Find TODOs/FIXMEs
   - Comment with list

6. **File Size Check**
   - Detect large files (>500 lines)
   - Suggest splitting

7. **Auto-assign Reviewers**
   - Assign based on file changes
   - Smart reviewer selection

---

### 5️⃣ **Dependabot** (`dependabot.yml`)

**Automated Updates:**
- **Python dependencies**: Weekly on Monday
- **GitHub Actions**: Weekly on Monday
- **Docker**: Weekly on Monday

**Features:**
- Group minor/patch updates
- Auto-assign reviewers
- Custom commit messages
- Ignore major version updates (stability)

---

### 6️⃣ **Stale Issues/PRs** (`stale.yml`)

**Schedule:** Daily at midnight UTC

**Configuration:**
- Mark issues stale after 30 days
- Mark PRs stale after 14 days
- Close after 7 additional days
- Exempt labels: `keep-open`, `bug`, `security`

---

## 🎯 **როგორ გამოვიყენო**

### **Local Testing**

```bash
# Run same checks as CI locally
make ci

# Or individually:
make lint          # Linting
make test          # All tests
make test-cov      # Coverage
make security      # Security scans
```

### **Creating a Pull Request**

1. **Create branch:**
   ```bash
   git checkout -b feat/my-feature
   ```

2. **Make changes & commit:**
   ```bash
   git add .
   git commit -m "feat: Add new feature"
   ```

3. **Push & create PR:**
   ```bash
   git push origin feat/my-feature
   ```

4. **PR title format** (conventional commits):
   - `feat: Add user authentication`
   - `fix: Resolve video processing bug`
   - `docs: Update README`
   - `test: Add unit tests for validators`
   - `refactor: Improve code structure`
   - `perf: Optimize video encoding`
   - `ci: Update GitHub Actions workflow`

5. **PR checks will run:**
   - ✅ CI tests & linting
   - ✅ Code quality analysis
   - ✅ Coverage comparison
   - ✅ Auto-labeling
   - ✅ Security scans

### **Deploying to Production**

**Option 1: Automatic (on merge to main)**
```bash
git checkout main
git merge develop
git push origin main
# → Automatically triggers deployment
```

**Option 2: Manual Deployment**
1. Go to Actions tab
2. Select "CD - Deploy to Production"
3. Click "Run workflow"
4. Choose environment
5. Click "Run workflow"

**Option 3: Tag Release**
```bash
git tag v1.2.3
git push origin v1.2.3
# → Triggers deployment + GitHub release
```

---

## 📊 **Status Badges**

დაამატე README-ში:

```markdown
# Georgian Voiceover App

![CI Status](https://github.com/speudoname/georgian-voiceover-app/workflows/CI%20-%20Tests%20%26%20Quality%20Checks/badge.svg)
![Deploy Status](https://github.com/speudoname/georgian-voiceover-app/workflows/CD%20-%20Deploy%20to%20Production/badge.svg)
![Code Coverage](https://codecov.io/gh/speudoname/georgian-voiceover-app/branch/main/graph/badge.svg)
![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
```

---

## 🔐 **Required GitHub Secrets**

### **Essential (for deployment):**
```bash
RAILWAY_TOKEN           # Railway deployment token
```

### **Optional (for features):**
```bash
CODECOV_TOKEN          # Code coverage reporting
SLACK_WEBHOOK          # Slack notifications
DISCORD_WEBHOOK        # Discord notifications
SONAR_TOKEN            # SonarCloud analysis
RENDER_DEPLOY_HOOK     # Render.com deployment
HEROKU_API_KEY         # Heroku deployment
```

### **როგორ დავამატო Secrets:**

1. GitHub repository → Settings
2. Secrets and variables → Actions
3. New repository secret
4. Name: `RAILWAY_TOKEN`
5. Value: `your_token_here`

---

## 🛠️ **Workflow Customization**

### **Modify Python Versions**

`ci.yml`:
```yaml
strategy:
  matrix:
    python-version: ['3.9', '3.10', '3.11']  # შეცვალე როგორც გსურს
```

### **Change Coverage Threshold**

`ci.yml`:
```yaml
- name: Check coverage threshold
  run: |
    coverage report --fail-under=80  # შეცვალე 80 სხვა რიცხვზე
```

### **Modify Deploy Target**

`deploy.yml`:
```yaml
- name: Deploy to Railway
  run: |
    railway up --service web
    railway up --service worker
```

---

## 📈 **Monitoring & Alerts**

### **Email Notifications**

GitHub-ი ავტომატურად გამოგიგზავნის email-ს თუ:
- Workflow fails on your push
- Workflow fails on your PR
- You're assigned as reviewer

### **Slack Integration**

1. Create Slack incoming webhook
2. Add to GitHub Secrets as `SLACK_WEBHOOK`
3. Notifications will be sent on:
   - ✅ Successful deployments
   - ❌ Failed deployments
   - 🚀 New releases

### **Discord Integration**

1. Create Discord webhook in channel settings
2. Add to GitHub Secrets as `DISCORD_WEBHOOK`
3. Same notifications as Slack

---

## 🐛 **Troubleshooting**

### **CI Failing - Linting Errors**

```bash
# Fix locally before pushing
make format  # Auto-format with black + isort
make lint    # Check for remaining issues
```

### **CI Failing - Tests**

```bash
# Run tests locally
make test

# Run specific tests
pytest tests/unit/test_validators.py -v

# Check coverage
make test-cov
```

### **Deployment Failing**

1. Check Railway logs
2. Verify environment variables
3. Check health endpoint: `https://voyoutube.com/health`
4. Review deployment workflow logs

### **Dependabot PRs Failing**

1. Review the dependency update
2. Check if breaking changes
3. Update code if needed
4. Merge or close PR

---

## 📚 **Best Practices**

### **Branch Strategy**

```
main (production)
  ↑
develop (staging)
  ↑
feature/my-feature
fix/bug-name
```

### **Commit Messages**

```bash
# Good
git commit -m "feat: Add user authentication"
git commit -m "fix: Resolve video encoding timeout"
git commit -m "docs: Update API documentation"

# Bad
git commit -m "update"
git commit -m "fix bug"
git commit -m "changes"
```

### **PR Best Practices**

- ✅ Keep PRs small (<500 lines)
- ✅ Write descriptive titles
- ✅ Add meaningful description
- ✅ Link related issues
- ✅ Request reviews
- ✅ Respond to feedback
- ✅ Ensure CI passes before merge

---

## 🎓 **Learning Resources**

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Railway Documentation](https://docs.railway.app/)
- [Codecov Documentation](https://docs.codecov.com/)

---

## ✅ **Status**

**CI/CD Pipeline**: ✅ სრულად კონფიგურირებული!

**Next Steps:**
1. ✅ Push to GitHub repository
2. ✅ Add required secrets (RAILWAY_TOKEN, etc.)
3. ✅ Create first PR to test workflows
4. ✅ Merge to main to trigger deployment
5. ✅ Monitor deployment in Railway dashboard

---

**გაქვს კითხვები?** შეამოწმე workflow ფაილები `.github/workflows/` დირექტორიაში!
