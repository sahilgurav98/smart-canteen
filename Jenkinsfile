pipeline {
  agent any
  options { timestamps(); disableConcurrentBuilds() }
  environment {
    IMAGE_NAME = "ghcr.io/YOUR_GITHUB_USERNAME/smart-canteen"
    EC2_HOST = "YOUR_EC2_PUBLIC_IP"
  }
  stages {
    stage('Checkout') { steps { checkout scm } }
    stage('Install dependencies') {
      steps { sh 'python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt' }
    }
    stage('Automated tests') {
      steps { sh '. .venv/bin/activate && pytest -q' }
    }
    stage('Build Docker image') {
      steps { sh 'docker build -t $IMAGE_NAME:$BUILD_NUMBER -t $IMAGE_NAME:latest .' }
    }
    stage('Container smoke test') {
      steps {
        sh '''
          set -eu
          docker rm -f smart-canteen-ci-test >/dev/null 2>&1 || true
          docker run -d --name smart-canteen-ci-test -p 18080:5000 -e SECRET_KEY=ci-secret -e ADMIN_PASSWORD=ci-password -e DATABASE_PATH=/tmp/canteen.db "$IMAGE_NAME:$BUILD_NUMBER"
          trap 'docker rm -f smart-canteen-ci-test >/dev/null 2>&1 || true' EXIT
          for i in $(seq 1 20); do
            if curl -fsS http://127.0.0.1:18080/health; then exit 0; fi
            sleep 2
          done
          echo "Container health check failed"
          exit 1
        '''
      }
    }
    stage('Push image to GHCR') {
      steps {
        withCredentials([usernamePassword(credentialsId: 'ghcr-credentials', usernameVariable: 'GHCR_USER', passwordVariable: 'GHCR_TOKEN')]) {
          sh '''
            set +x
            echo "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USER" --password-stdin
            docker push "$IMAGE_NAME:$BUILD_NUMBER"
            docker push "$IMAGE_NAME:latest"
            docker logout ghcr.io
          '''
        }
      }
    }
    stage('Deploy to EC2') {
      when { expression { return env.EC2_HOST != 'YOUR_EC2_PUBLIC_IP' && env.EC2_HOST?.trim() } }
      steps {
        withCredentials([sshUserPrivateKey(credentialsId: 'ec2-ssh-key', keyFileVariable: 'SSH_KEY', usernameVariable: 'SSH_USER')]) {
          sh '''
            set -eu
            ssh -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new "$SSH_USER@$EC2_HOST" "docker pull $IMAGE_NAME:latest && (docker rm -f smart-canteen || true) && docker run -d --restart unless-stopped --name smart-canteen -p 80:5000 -e SECRET_KEY='replace-this' -e ADMIN_PASSWORD='change-this' -v canteen-data:/app/data $IMAGE_NAME:latest"
          '''
        }
      }
    }
  }
  post {
    success { echo 'Smart Canteen CI/CD pipeline completed successfully.' }
    failure { echo 'Pipeline failed. Review the stage logs before deploying.' }
    always { echo 'Pipeline run finished.' }
  }
}
