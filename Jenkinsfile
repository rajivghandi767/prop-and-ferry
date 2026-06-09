@Library('homelab-library') _

pipeline {
    agent any

    environment {
        APP_NAME         = "Prop & Ferry"
        PROJECT_NAME     = "prop-ferry" 
        REGISTRY         = "ghcr.io"
        REGISTRY_CRED_ID = "github-packages-pat"
        VAULT_CRED_ID    = "vault-${PROJECT_NAME}-approle"

        IMAGE_BACKEND  = "rajivghandi767/${PROJECT_NAME}-backend"
        IMAGE_FRONTEND = "rajivghandi767/${PROJECT_NAME}-frontend"
        IMAGE_NGINX    = "rajivghandi767/${PROJECT_NAME}-nginx"
    }

    stages {
        stage('🔍 Vault Status & Unseal') {
            steps {
                script {
                    unsealVault()
                }
            }
        }

        stage('Checkout') {
            steps { checkout scm }
        }

        stage('Test Suite') {
            parallel {
                stage('Test Backend (Python)') {
                    steps {
                        sh '''
                            docker build -t prop-ferry-backend:test -f backend/Dockerfile ./backend
                            docker run --rm prop-ferry-backend:test python manage.py test
                        '''
                    }
                }
                stage('Test Frontend (React)') {
                    steps {
                        sh '''
                            docker build -t prop-ferry-frontend:test -f frontend/Dockerfile ./frontend
                            docker run --rm prop-ferry-frontend:test npm run test
                        '''
                    }
                }
            }
        }

        stage('Build & Push Images') {
            steps {
                withVault(configuration: [vaultUrl: "http://vault:8200", vaultCredentialId: "${VAULT_CRED_ID}", engineVersion: 2], 
                vaultSecrets: [[path: "secret/${PROJECT_NAME}-prod", secretValues: [
                    [envVar: 'VITE_API_URL', vaultKey: 'VITE_API_URL']
                ]]]) {
                    script {
                        def gitCommit = sh(returnStdout: true, script: 'git rev-parse --short HEAD').trim()

                        docker.withRegistry("https://${REGISTRY}", REGISTRY_CRED_ID) {
                            parallel(
                                "Backend": {
                                    def img = docker.build("${REGISTRY}/${IMAGE_BACKEND}:${BUILD_NUMBER}", "--label git-commit=${gitCommit} -f backend/Dockerfile.prod ./backend")
                                    img.push(); img.push("latest")
                                },
                                "Frontend": {
                                    def img = docker.build("${REGISTRY}/${IMAGE_FRONTEND}:${BUILD_NUMBER}", "--label git-commit=${gitCommit} -f frontend/Dockerfile.prod --build-arg VITE_API_URL=${VITE_API_URL} ./frontend")
                                    img.push(); img.push("latest")
                                },
                                "Nginx": {
                                    def img = docker.build("${REGISTRY}/${IMAGE_NGINX}:${BUILD_NUMBER}", "--label git-commit=${gitCommit} ./nginx")
                                    img.push(); img.push("latest")
                                }
                            )
                        }
                    }
                }
            }
        }
    }

    post {
        success {
            script {
                def msg = "Build **#${env.BUILD_NUMBER}** completed successfully.\n[View Jenkins Logs](${env.BUILD_URL})"
                notifyDiscord("✅ ${env.APP_NAME} Build Success", msg, 3066993)
            }
        }
        failure {
            script {
                def msg = "Check Jenkins logs for build **#${BUILD_NUMBER}**.\n[View Jenkins Logs](${env.BUILD_URL})"
                notifyDiscord("🚨 ${env.APP_NAME} Build Failed", msg, 15158332)
            }
        }
    }
}