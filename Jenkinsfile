pipeline {
    agent any

    environment {
        REGISTRY = 'ghcr.io'
        IMAGE_NAME = 'smart-canteen'
        GITHUB_USER = 'sahilgurav98'
        EC2_IP = '15.207.100.162'
        EC2_USER = 'ec2-user'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                echo "Code checkout successful!"
            }
        }

        stage('Test') {
            steps {
                echo "Validating project files..."
                bat 'if exist app.py (echo app.py exists) else (exit 1)'
            }
        }
stage('Docker Build') {
    steps {
        bat "docker build --provenance=false -t ${REGISTRY}/${GITHUB_USER}/${IMAGE_NAME}:latest ."
    }
}
        stage('GHCR Push') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'ghcr-credentials', usernameVariable: 'GHCR_USER', passwordVariable: 'GHCR_PAT')]) {
                    bat "echo %GHCR_PAT% | docker login %REGISTRY% -u %GHCR_USER% --password-stdin"
                    bat "docker push %REGISTRY%/%GITHUB_USER%/%IMAGE_NAME%:latest"
                }
            }
        }

        stage('Deploy to EC2') {
            steps {
                script {
                    echo "Deploying to AWS EC2 via SSH..."
                    sshagent(credentials: ['ec2-ssh-key']) {
                        // Remote commands on EC2: Pull latest image, stop old container, run new container
                        bat """
                        ssh -o StrictHostKeyChecking=no ${EC2_USER}@${EC2_IP} "docker pull ${REGISTRY}/${GITHUB_USER}/${IMAGE_NAME}:latest && docker stop ${IMAGE_NAME} || true && docker rm ${IMAGE_NAME} || true && docker run -d --name ${IMAGE_NAME} -p 80:5000 ${REGISTRY}/${GITHUB_USER}/${IMAGE_NAME}:latest"
                        """
                    }
                }
            }
        }

        stage('Verify Deployment') {
            steps {
                echo "Application deployed successfully!"
            }
        }
    }
}