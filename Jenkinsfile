#!/usr/bin/env groovy


def python_version = params.getOrDefault("python_version", "3.9")
def python_image = "python:${python_version}"
def python_container_cmd = ''' \
  -u root
  -v ${WORKSPACE}@tmp:/workspace \
  -v ${WORKSPACE}:/sources \
  -e WASP_ENABLE_CHECKS \
  -e COVERALLS_REPO_TOKEN \
  -e BUILD_NUMBER \
  -e GIT_BRANCH \
  -e CI_PULL_REQUEST \
  -e PYTHONPATH=.. \
  '''


def telegram_notification(message) {
  withCredentials([
    string(credentialsId: 'telegramBotToken', variable: 'BOT_TOKEN'),
    string(credentialsId: 'telegramChatId', variable: 'CHAT_ID')
  ]) {
    def telegram_url = "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage"

    sh "curl -X POST ${telegram_url} -d chat_id=${CHAT_ID} -d parse_mode=HTML -d text='${message}'"
  }
}


pipeline {

  agent { label 'linux_x64' }

  parameters {
    string(
      name: 'python_version',
      defaultValue: '3.9'
    )
  }

  environment {
    WASP_ENABLE_CHECKS="*"
  }

  stages {
    stage('Prepare'){
      steps {
        script {
            docker.image(python_image).inside(python_container_cmd){
                sh "python -m venv /workspace/venv"
            }
        }
      }
    }

    stage('Install'){
      steps {
        script {
          docker.image(python_image).inside(python_container_cmd){
            sh "cd /sources && /workspace/venv/bin/pip install -r requirements.txt"
            sh "cd /sources && /workspace/venv/bin/pip install -v '.[all,test]'"  // test should be
            // set explicitly for the Python:3.6 (check!)
          }
        }
      }
    }

    stage('Test'){
      steps {
        script {
          withCredentials([
            string(credentialsId: 'coverallsToken', variable: 'COVERALLS_REPO_TOKEN'),
          ]){
            docker.image(python_image).inside(python_container_cmd){
              sh "cd /sources/tests && /workspace/venv/bin/py.test -c pytest-cov.ini"
              sh "cd /sources/tests && /workspace/venv/bin/coveralls --service=jenkins --basedir=/sources"
            }
          }
        }
      }
    }

    stage('PEP8 check'){
      steps {
        script {
          docker.image(python_image).inside(python_container_cmd){
            sh "cd /sources && /workspace/venv/bin/py.test -c tests/pytest-pep8.ini"
          }
        }
      }
    }
  }  // stages

  post {

    always {
      script{
        docker.image(python_image).inside(python_container_cmd){
          sh "rm -rf /workspace/venv/"
        }
      }
    }

    fixed { 
      script {
        message = "☘ The job <b>'${env.JOB_NAME}'</b> fixed. Details: ${env.BUILD_URL}"
        telegram_notification(message)
      }
    }
        
    aborted {
      script {        
        message = "🧯 The job <b>'${env.JOB_NAME}'</b> aborted. Details: ${env.BUILD_URL}"
        telegram_notification(message)
      }
    }
    
    failure {
      script {
        message = "🧯 The job <b>'${env.JOB_NAME}'</b> failed. Details: ${env.BUILD_URL}"
        telegram_notification(message)
      }
    }
    
    success {
      script {
        message = "☘ The job <b>'${env.JOB_NAME}'</b> completed successfully. Details: ${env.BUILD_URL}"
        telegram_notification(message) 
      }
    }    
        
  }  // post
    
}
