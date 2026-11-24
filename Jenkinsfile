pipeline {
    agent any

    environment {
        // Replace 'anikethakre' with your actual Docker Hub username on your VM
        DOCKER_USER = "anikethakre007"
        IMAGE_NAME  = "aceest-fitness"
        APP_VERSION = "v1.0.${BUILD_NUMBER}"
    }

    triggers {
        // Poll GitHub every 2 minutes for new commits (Task 4)
        pollSCM('H/2 * * * *')
    }

    stages {
        stage('1. Checkout Code') {
            steps {
                checkout scm
            }
        }

        stage('2. Build Docker Image') {
            steps {
                sh """
                docker build --build-arg APP_VERSION=${APP_VERSION} -t ${DOCKER_USER}/${IMAGE_NAME}:${APP_VERSION} .
                docker tag ${DOCKER_USER}/${IMAGE_NAME}:${APP_VERSION} ${DOCKER_USER}/${IMAGE_NAME}:latest
                """
            }
        }

        stage('3. Run Pytest Inside Container') {
            steps {
                // Task 7: Execute Pytest inside the containerized environment
                sh "docker run --rm ${DOCKER_USER}/${IMAGE_NAME}:${APP_VERSION} pytest -v"
            }
        }

        stage('4. SonarQube Code Quality Scan') {
            steps {
                withSonarQubeEnv('SonarQube') {
                    sh "sonar-scanner"
                }
            }
        }

        stage('5. Quality Gate') {
            steps {
                timeout(time: 3, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        stage('6. Push Image to Docker Hub') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub-creds', usernameVariable: 'USER', passwordVariable: 'PASS')]) {
                    sh """
                    echo \$PASS | docker login -u \$USER --password-stdin
                    docker push ${DOCKER_USER}/${IMAGE_NAME}:${APP_VERSION}
                    docker push ${DOCKER_USER}/${IMAGE_NAME}:latest
                    """
                }
            }
        }

        stage('7. Deploy to Kubernetes') {
            steps {
                sh """
                kubectl apply -f k8s/
                kubectl set image deployment/aceest-rolling aceest-app=${DOCKER_USER}/${IMAGE_NAME}:${APP_VERSION}
                kubectl rollout status deployment/aceest-rolling
                """
            }
        }
    }

    post {
        success {
            echo "Pipeline succeeded for version ${APP_VERSION}!"
        }
        failure {
            echo "Pipeline failed! Triggering Kubernetes rollback if applicable..."
            sh "kubectl rollout undo deployment/aceest-rolling || true"
        }
    }
}
