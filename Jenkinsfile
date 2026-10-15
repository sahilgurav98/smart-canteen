pipeline {
    agent any

    environment {
        REGISTRY = 'ghcr.io'
        IMAGE_NAME = 'smart-canteen'  // Name of your container image
        GITHUB_USER = 'sahilgurav98' // Replace with your actual GitHub username or org name
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
                echo "Validating application files..."
                bat 'if exist app.py (echo app.py exists) else (exit 1)'
            }
        }

        stage('Docker Build') {
            steps {
                script {
                    echo "Building Docker image..."
                    bat "docker build -t ${REGISTRY}/${GITHUB_USER}/${IMAGE_NAME}:latest ."
                }
            }
        }

        stage('Verify Docker Image') {
            steps {
                echo "Verifying local Docker image..."
                bat "docker images ${REGISTRY}/${GITHUB_USER}/${IMAGE_NAME}:latest"
            }
        }

        stage('GHCR Push') {
            steps {
                script {
                    echo "Authenticating and pushing image to GHCR..."
                    withCredentials([usernamePassword(credentialsId: 'ghcr-credentials', usernameVariable: 'GHCR_USER', passwordVariable: 'GHCR_PAT')]) {
                        bat "echo %GHCR_PAT% | docker login %REGISTRY% -u %GHCR_USER% --password-stdin"
                        bat "docker push %REGISTRY%/%GITHUB_USER%/%IMAGE_NAME%:latest"
                    }
                    echo "GHCR push successful!"
                }
            }
        }
    }
}