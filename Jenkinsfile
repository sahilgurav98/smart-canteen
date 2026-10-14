
pipeline {
  agent any

  options {
    timestamps()
    disableConcurrentBuilds()
  }

  environment {
    IMAGE_NAME = "ghcr.io/sahilgurav98/smart-canteen"
    EC2_HOST = "13.204.68.16"
    DOCKER_CONFIG = 'C:\\Users\\gurav\\.docker'
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Install dependencies') {
      steps {
        bat 'python --version'
        bat 'python -m pip install -r requirements.txt'
        bat 'python -m pip install pytest'
      }
    }

    stage('Automated tests') {
      steps {
        bat 'python -m pytest -q'
      }
    }

    stage('Build Docker image') {
      steps {
        bat 'docker build -t %IMAGE_NAME%:%BUILD_NUMBER% -t %IMAGE_NAME%:latest .'
      }
    }

    stage('Container smoke test') {
      steps {
        bat '''
          @echo off
          docker rm -f smart-canteen-ci-test 2>nul

          docker run -d --name smart-canteen-ci-test -p 18080:5000 -e SECRET_KEY=ci-secret -e ADMIN_PASSWORD=ci-password -e DATABASE_PATH=/tmp/canteen.db %IMAGE_NAME%:%BUILD_NUMBER%
          if errorlevel 1 exit /b 1

          powershell -NoProfile -ExecutionPolicy Bypass -Command "$ok=$false; for($i=0;$i -lt 20;$i++){try{$r=Invoke-WebRequest -Uri 'http://127.0.0.1:18080/health' -UseBasicParsing -TimeoutSec 3;if($r.StatusCode -eq 200){$ok=$true;break}}catch{};Start-Sleep -Seconds 2};if(-not $ok){exit 1}"

          set "CHECK_RESULT=%ERRORLEVEL%"
          docker rm -f smart-canteen-ci-test
          exit /b %CHECK_RESULT%
        '''
      }
    }


stage('Push image to GHCR') {
  steps {
    withCredentials([
      usernamePassword(
        credentialsId: 'ghcr-credentials',
        usernameVariable: 'GHCR_USER',
        passwordVariable: 'GHCR_TOKEN'
      )
    ]) {
      bat '''
        @echo off
        powershell -NoProfile -ExecutionPolicy Bypass -Command ^
          "$ErrorActionPreference = 'Stop';" ^
          "$loggedIn = $false;" ^
          "for ($attempt = 1; $attempt -le 5; $attempt++) {" ^
          "  Write-Host ('GHCR login attempt ' + $attempt + ' of 5');" ^
          "  $env:GHCR_TOKEN | docker login ghcr.io -u $env:GHCR_USER --password-stdin;" ^
          "  if ($LASTEXITCODE -eq 0) { $loggedIn = $true; break };" ^
          "  if ($attempt -lt 5) { Start-Sleep -Seconds (10 * $attempt) };" ^
          "};" ^
          "if (-not $loggedIn) { exit 1 };" ^
          "foreach ($tag in @('%BUILD_NUMBER%', 'latest')) {" ^
          "  $success = $false;" ^
          "  for ($attempt = 1; $attempt -le 5; $attempt++) {" ^
          "    Write-Host ('Pushing tag ' + $tag + ', attempt ' + $attempt + ' of 5');" ^
          "    docker push ('%IMAGE_NAME%:' + $tag);" ^
          "    if ($LASTEXITCODE -eq 0) { $success = $true; break };" ^
          "    if ($attempt -lt 5) { Start-Sleep -Seconds (10 * $attempt) };" ^
          "  };" ^
          "  if (-not $success) { exit 1 };" ^
          "};" ^
          "docker logout ghcr.io"

        if errorlevel 1 exit /b 1
      '''
    }
  }
}


    stage('Deploy to EC2') {
      steps {
        withCredentials([
          sshUserPrivateKey(
            credentialsId: 'ec2-ssh-key',
            keyFileVariable: 'SSH_KEY',
            usernameVariable: 'SSH_USER'
          )
        ]) {
          bat '''
            @echo off

            icacls "%SSH_KEY%" /inheritance:r
            if errorlevel 1 exit /b 1

            icacls "%SSH_KEY%" /remove:g "BUILTIN\\Users" "NT AUTHORITY\\Authenticated Users" "Everyone"
            if errorlevel 1 exit /b 1

            icacls "%SSH_KEY%" /grant:r "SYSTEM:R"
            if errorlevel 1 exit /b 1

            ssh -i "%SSH_KEY%" -o StrictHostKeyChecking=accept-new %SSH_USER%@%EC2_HOST% "docker pull %IMAGE_NAME%:latest && (docker rm -f smart-canteen || true) && docker run -d --restart unless-stopped --name smart-canteen -p 127.0.0.1:5000:5000 -e SECRET_KEY='replace-with-a-long-random-secret' -e ADMIN_PASSWORD='replace-with-a-strong-admin-password' -v canteen-data:/app/data %IMAGE_NAME%:latest"

            if errorlevel 1 exit /b 1
          '''
        }
      }
    }
  }

  post {
    success {
      echo 'Smart Canteen CI/CD pipeline completed successfully.'
    }

    failure {
      echo 'Pipeline failed. Review the stage logs before deploying.'
    }

    always {
      echo 'Pipeline run finished.'
    }
  }
}
