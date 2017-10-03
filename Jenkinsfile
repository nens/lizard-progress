pipeline {
    environment {
        COMPOSE_PROJECT_NAME = "${env.JOB_NAME}-${env.BUILD_ID}"
    }
    stages {
        stage("Checkout") {
            steps {
                echo "Krijg nou het rasborakoudumakulatavirus"
                checkout scm
            }
        }
        stage("Build") {
            steps {
                sh "echo 'COMPOSE_PROJECT_NAME=${env.JOB_NAME}-${env.BUILD_ID}' > .env"
                sh "cat .env"
                sh "docker-compose down -v"
                sh "docker-compose build"
                sh "docker-compose run web buildout"
            }
        }
        stage("Test") {
            steps {
                sh "docker-compose run web bin/test"
                step $class: 'JUnitResultArchiver', testResults: 'nosetests.xml'
                publishHTML target: [reportDir: 'htmlcov', reportFiles: 'index.html', reportName: 'Coverage report']
                step([$class: 'CoberturaPublisher', coberturaReportFile: 'coverage.xml'])
            }
        }
    }
    post {
        always {
            sh "docker-compose down -v"
        }
    }
}
