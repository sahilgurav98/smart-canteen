# Smart Canteen Management System — Full-stack Flask + DevOps

Features: student menu, cart, server-side order placement and price calculation, SQLite persistence, order tracking, staff login/dashboard, status management, menu availability toggles, CSV report, health endpoint, pytest tests, Docker and Jenkins pipeline.

## Run locally (Windows PowerShell)
Use Python 3.11+ (3.12 recommended).
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:SECRET_KEY = "local-demo-secret-change-this"
$env:ADMIN_PASSWORD = "change-this-demo-password"
python app.py
```
Open http://127.0.0.1:5000. Staff login: http://127.0.0.1:5000/admin/login. Default demo password: `change-this-demo-password`. Change it before deployment.

## Tests
```powershell
pytest -q
```
Capture a screenshot showing all tests passing.

## Docker
Start Docker Desktop, then:
```powershell
docker compose up --build -d
docker ps
docker images
```
Open http://localhost:5000. The named volume `canteen-data` persists the SQLite database. Capture screenshots of the running container and image list.
```powershell
docker compose logs web
docker compose down
```

## GitHub
Create a repository named `smart-canteen`:
```powershell
git init
git add .
git commit -m "SC-1 Build Flask Smart Canteen application"
git branch -M main
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/smart-canteen.git
git push -u origin main
```
Replace the username. Do not commit secrets, tokens, `.env`, private keys, or database files.

## Jira
Create stories for menu, ordering, tracking, staff management, testing, containerization, and deployment. Connect GitHub using GitHub for Atlassian. Include actual Jira issue keys in commit messages and verify linked development activity.

## Jenkins/GHCR
Jenkinsfile is intended for a Linux agent with Python, Git, Docker, curl and SSH installed. Configure Pipeline script from SCM with the repo URL, branch `*/main`, and script path `Jenkinsfile`. Enable GitHub hook trigger for GITScm polling. For locally hosted Jenkins, use an HTTPS tunnel so GitHub can reach the webhook endpoint. Webhook URL format: `https://YOUR-TUNNEL/github-webhook/`; JSON; push events.
Create Jenkins credential `ghcr-credentials` (username/password, with a GitHub token permitted to publish packages). Replace IMAGE_NAME with `ghcr.io/YOUR_GITHUB_USERNAME/smart-canteen` in lowercase. The pipeline installs dependencies, runs tests, builds an image, smoke-tests `/health`, and pushes to GHCR.

## AWS EC2 (optional, do after CI/GHCR succeeds)
Check current pricing before creating an instance. Use Amazon Linux 2023, install Docker, allow HTTP port 80, and restrict SSH port 22 to your IP. Configure Jenkins SSH credential `ec2-ssh-key`, set EC2_HOST, and ensure EC2 can pull the GHCR package. Replace demo secrets in deployment with securely managed values before any public deployment. Confirm persistent storage/backups. Stop or terminate resources when finished.

## Screenshot checklist
1. Student menu; 2. Cart/order placed; 3. Order tracking; 4. Staff dashboard; 5. CSV report; 6. Pytest passing; 7. Docker container running; 8. Docker image; 9. GitHub repo; 10. Jira backlog; 11. Jira issue linked to commit; 12. Jenkins SCM config; 13. webhook delivery; 14. successful Jenkins stages/GHCR package; 15. EC2 running/status checks; 16. security group with SSH restricted; 17. live deployed website.

## Viva flow
Jira tracks work → Git tracks code changes → GitHub stores source → webhook notifies Jenkins → Jenkins runs tests/builds image → Docker packages Flask/Gunicorn/app → GHCR stores the versioned image → SSH allows deployment to EC2 → EC2 runs the container → Gunicorn serves Flask → Flask APIs validate orders and store data in SQLite → browser displays menu and order status.

## Limitations/security
Educational project, no payment gateway. The demo admin login is basic and needs production-grade hardening before real use. Use strong secrets, keep credentials out of Git, and never expose SSH to everyone. AWS billing alerts do not prevent charges.
