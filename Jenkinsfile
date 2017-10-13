pipeline {
    agent any
    stages {
        stage("Checkout") {
            steps {
                checkout scm
                sh "echo 'COMPOSE_PROJECT_NAME=${env.JOB_NAME}-${env.BUILD_ID}' > .env"
            }
        }
        stage("Build") {
            steps {
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
