user_channel = "mycompany/stable"
config_url = "https://github.com/conan-ci-cd-training/settings.git"
conan_develop_repo = "conan-develop"
conan_tmp_repo = "conan-tmp"
artifactory_metadata_repo = "conan-metadata"

artifactory_url = (env.ARTIFACTORY_URL != null) ? "${env.ARTIFACTORY_URL}" : "jfrog.local"

reference_revision = null

def profiles = [
  "debug-gcc6": "conanio/gcc6",	
  "release-gcc6": "conanio/gcc6"	
]

create_build_info = false

def build_result = [:]

def get_stages(profile, docker_image) {
    return {
        stage(profile) {
            node {
                docker.image(docker_image).inside("--net=host") {
                    def scmVars = checkout scm
                    withEnv(["CONAN_USER_HOME=${env.WORKSPACE}/conan_cache"]) {
                        def lockfile = "${profile}.lock"
                        def buildInfoFilename = "${profile}.json"
                        def buildInfo = null
                        try {
                            stage("Configure Conan") {
                                sh "conan --version"
                                sh "conan config install ${config_url}"
                                sh "conan remote add ${conan_develop_repo} http://${artifactory_url}:8081/artifactory/api/conan/${conan_develop_repo}" // the namme of the repo is the same that the arttifactory key
                                sh "conan remote add ${conan_tmp_repo} http://${artifactory_url}:8081/artifactory/api/conan/${conan_tmp_repo}" // the namme of the repo is the same that the arttifactory key
                                withCredentials([usernamePassword(credentialsId: 'artifactory-credentials', usernameVariable: 'ARTIFACTORY_USER', passwordVariable: 'ARTIFACTORY_PASSWORD')]) {
                                    sh "conan user -p ${ARTIFACTORY_PASSWORD} -r ${conan_develop_repo} ${ARTIFACTORY_USER}"
                                    sh "conan user -p ${ARTIFACTORY_PASSWORD} -r ${conan_tmp_repo} ${ARTIFACTORY_USER}"
                                }
                            }
                            if (create_build_info) {
                                stage("Start build info: ${env.JOB_NAME} ${env.BUILD_NUMBER}") { 
                                    sh "conan_build_info --v2 start \"${env.JOB_NAME}\" \"${env.BUILD_NUMBER}\""
                                }
                            }
                            stage("Create package") {                                
                                sh "conan graph lock . --profile ${profile} --lockfile=${lockfile} -r ${conan_develop_repo}"
                                sh "cat ${lockfile}"
                                sh "conan create . ${user_channel} --profile ${profile} --lockfile=${lockfile} -r ${conan_develop_repo} --ignore-dirty"
                                sh "cat ${lockfile}"
                            }

                            if (branch_name =~ ".*PR.*" || env.BRANCH_NAME == "develop") {                                      

                                stage("Get created package info") {       
                                    if (reference_revision == null) {               
                                        name = sh (script: "conan inspect . --raw name", returnStdout: true).trim()
                                        version = sh (script: "conan inspect . --raw version", returnStdout: true).trim()                                
                                        search_out = sh (script: "conan search ${name}/${version}@${user_channel} --revisions --raw", returnStdout: true).trim()    
                                        reference_revision = search_out.split(" ")[0]
                                        echo "${reference_revision}"
                                    }
                                }

                                stage("Upload package: ${name}/${version}#${reference_revision} to conan-tmp") {
                                    sh "conan upload '${name}/${version}' --all -r ${conan_tmp_repo} --confirm"
                                }

                                if (create_build_info) {
                                    stage("Create build info") {
                                        withCredentials([usernamePassword(credentialsId: 'artifactory-credentials', usernameVariable: 'ARTIFACTORY_USER', passwordVariable: 'ARTIFACTORY_PASSWORD')]) {
                                            sh "conan_build_info --v2 create --lockfile ${lockfile} --user \"\${ARTIFACTORY_USER}\" --password \"\${ARTIFACTORY_PASSWORD}\" ${buildInfoFilename}"
                                            buildInfo = readJSON(file: buildInfoFilename)
                                        }
                                    }
                                }
                            } 

                            stage("Upload lockfile") {
                                if (env.BRANCH_NAME == "develop") {
                                    def lockfile_url = "http://${artifactory_url}:8081/artifactory/${artifactory_metadata_repo}/${env.JOB_NAME}/${env.BUILD_NUMBER}/${name}/${version}@${user_channel}/${profile}/conan.lock"
                                    withCredentials([usernamePassword(credentialsId: 'artifactory-credentials', usernameVariable: 'ARTIFACTORY_USER', passwordVariable: 'ARTIFACTORY_PASSWORD')]) {
                                        sh "curl --user \"\${ARTIFACTORY_USER}\":\"\${ARTIFACTORY_PASSWORD}\" -X PUT ${lockfile_url} -T ${lockfile}"
                                    }                                
                                }
                            }
                            return buildInfo
                        }
                        finally {
                            deleteDir()
                        }
                    }
                }
            }
        }
    }
}

pipeline {
    agent none
    stages {

        stage('Build') {
            steps {
                script {
                    echo("${currentBuild.fullProjectName.tokenize('/')[0]}")
                    build_result = withEnv(["CONAN_HOOK_ERROR_LEVEL=40"]) {
                        parallel profiles.collectEntries { profile, docker_image ->
                            ["${profile}": get_stages(profile, docker_image)]
                        }
                    }

                    if (create_build_info) {
                        if (branch_name =~ ".*PR.*" || env.BRANCH_NAME == "develop") {
                            docker.image("conanio/gcc6").inside("--net=host") {
                                def last_info = ""
                                build_result.each { profile, buildInfo ->
                                    writeJSON file: "${profile}.json", json: buildInfo
                                    if (last_info != "") {
                                        sh "conan_build_info --v2 update ${profile}.json ${last_info} --output-file mergedbuildinfo.json"
                                    }
                                    last_info = "${profile}.json"
                                }                    
                                sh "cat mergedbuildinfo.json"
                                withCredentials([usernamePassword(credentialsId: 'artifactory-credentials', usernameVariable: 'ARTIFACTORY_USER', passwordVariable: 'ARTIFACTORY_PASSWORD')]) {
                                    sh "conan_build_info --v2 publish --url http://${artifactory_url}:8081/artifactory --user \"\${ARTIFACTORY_USER}\" --password \"\${ARTIFACTORY_PASSWORD}\" mergedbuildinfo.json"
                                }
                            }
                        }
                    }                    
                }
            }
        }

        // maybe just doing publishes an uploads if we are releasing something
        // or doing a commit to develop?
        // maybe if a new tag was created with the name release?
        stage("Trigger products pipeline") {
            agent any
            when {expression { return (branch_name =~ ".*PR.*" || env.BRANCH_NAME == "develop") }}
            steps {
                script {
                    assert reference_revision != null
                    def reference = "${name}/${version}@${user_channel}#${reference_revision}"
                    def scmVars = checkout scm
                    build(job: "../products/master", propagate: true, parameters: [
                        [$class: 'StringParameterValue', name: 'reference', value: reference],
                        [$class: 'StringParameterValue', name: 'library_branch', value: env.BRANCH_NAME],
                    ]) 
                }
            }
        }
    }
}