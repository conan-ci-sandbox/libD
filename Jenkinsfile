def organization = "conan-ci-cd-training"
def user_channel = "mycompany/stable"
def config_url = "https://github.com/conan-ci-cd-training/settings.git"
def conan_develop_repo = "conan-develop"
def conan_tmp_repo = "conan-tmp"
def artifactory_metadata_repo = "conan-metadata"

def artifactory_url = (env.ARTIFACTORY_URL != null) ? "${env.ARTIFACTORY_URL}" : "jfrog.local"

String reference_revision = null

def profiles = [
  "conanio-gcc8": "conanio/gcc8",	
  "conanio-gcc7": "conanio/gcc7"	
]

def build_result = [:]

def get_stages(profile, docker_image, user_channel, config_url, conan_develop_repo, conan_tmp_repo, artifactory_metadata_repo, artifactory_url) {
    return {
        stage(profile) {
            node {
                docker.image(docker_image).inside("--net=host") {
                    def scmVars = checkout scm
                    def repository = scmVars.GIT_URL.tokenize('/')[3].split("\\.")[0]
                    echo("${scmVars}")
                    sh "printenv"
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
                            stage("Start build info: ${env.JOB_NAME} ${env.BUILD_NUMBER}") { 
                                sh "conan_build_info --v2 start \"${env.JOB_NAME}\" \"${env.BUILD_NUMBER}\""
                            }
                            stage("Create package") {                                
                                sh "conan graph lock . --profile ${profile} --lockfile=${lockfile} -r ${conan_develop_repo}"
                                sh "cat ${lockfile}"
                                sh "conan create . ${user_channel} --profile ${profile} --lockfile=${lockfile} -r ${conan_develop_repo} --ignore-dirty"
                                sh "cat ${lockfile}"
                                name = sh (script: "conan inspect . --raw name", returnStdout: true).trim()
                                version = sh (script: "conan inspect . --raw version", returnStdout: true).trim()                                
                                // this is some kind of workaround, we have just created the package in the local cache
                                // and search for the package using --revisions to get the revision of the package
                                // write the search to a json file and stash the file to get it after all the builds
                                // have finished to pass it to the products projects pipeline
                                if (profile=="conanio-gcc8") { //FIX THIS: get just for one of the profiles the revision is the same for all
                                    def search_output = "search_output.json"
                                    sh "conan search ${name}/${version}@${user_channel} --revisions --raw --json=${search_output}"
                                    sh "cat ${search_output}"
                                    stash name: 'full_reference', includes: 'search_output.json'
                                }
                            }
                            stage("Test things") {
                                echo("tests OK!")
                            }
                            if (branch_name =~ ".*PR.*" || env.BRANCH_NAME == "develop") {                     
                                stage("Upload package") {
                                    // we upload the package in case it's a PR or a commit to develop to pass the new package
                                    // to the prduct's pipeline           
                                        sh "conan upload '*' --all -r ${conan_tmp_repo} --confirm  --force"
                                        // NOTE: This step probably should be done in the products pipeline
                                        //       if we find that the package does not depend on any product
                                        // if (env.BRANCH_NAME=="develop") { //FIXME: should be done in the end promoting or when all configs are built
                                        //     sh "conan upload '*' --all -r ${conan_develop_repo} --confirm  --force"
                                        // }
                                }
                                stage("Create build info") {
                                    withCredentials([usernamePassword(credentialsId: 'artifactory-credentials', usernameVariable: 'ARTIFACTORY_USER', passwordVariable: 'ARTIFACTORY_PASSWORD')]) {
                                        sh "conan_build_info --v2 create --lockfile ${lockfile} --user \"\${ARTIFACTORY_USER}\" --password \"\${ARTIFACTORY_PASSWORD}\" ${buildInfoFilename}"
                                        buildInfo = readJSON(file: buildInfoFilename)
                                    }
                                }
                            } 
                            stage("Upload lockfile") {
                                if (env.BRANCH_NAME == "develop") {
                                    def lockfile_url = "http://${artifactory_url}:8081/artifactory/${artifactory_metadata_repo}/${name}/${version}@${user_channel}/${profile}/conan.lock"
                                    def lockfile_sha1 = sha1(file: lockfile)
                                    withCredentials([usernamePassword(credentialsId: 'artifactory-credentials', usernameVariable: 'ARTIFACTORY_USER', passwordVariable: 'ARTIFACTORY_PASSWORD')]) {
                                        sh "curl --user \"\${ARTIFACTORY_USER}\":\"\${ARTIFACTORY_PASSWORD}\" --header 'X-Checksum-Sha1:'${lockfile_sha1} --header 'Content-Type: application/json' ${lockfile_url} --upload-file ${lockfile}"
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
                            ["${profile}": get_stages(profile, docker_image, user_channel, config_url, conan_develop_repo, conan_tmp_repo, artifactory_metadata_repo, artifactory_url)]
                        }
                    }
                }
            }
        }

        // maybe just doing publishes an uploads if we are releasing something
        // or doing a commit to develop?
        // maybe if a new tag was created with the name release?
        stage("Merge and publish build infos") {
            steps {
                script {
                if (branch_name =~ ".*PR.*" || env.BRANCH_NAME == "develop") {
                    docker.image("conanio/gcc8").inside("--net=host") {
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

        stage("Trigger products build") {
            agent any
            steps {
                script {
                    if (branch_name =~ ".*PR.*" || env.BRANCH_NAME == "develop") {
                        unstash 'full_reference'
                        def props = readJSON file: "search_output.json"
                        reference_revision = props[0]['revision']
                        assert reference_revision != null
                        def reference = "${name}/${version}@${user_channel}#${reference_revision}"
                        def scmVars = checkout scm
                        build(job: "../products/master", propagate: true, parameters: [
                            [$class: 'StringParameterValue', name: 'reference', value: reference],
                            [$class: 'StringParameterValue', name: 'organization', value: organization],
                            [$class: 'StringParameterValue', name: 'build_name', value: env.JOB_NAME],
                            [$class: 'StringParameterValue', name: 'build_number', value: env.BUILD_NUMBER],
                            [$class: 'StringParameterValue', name: 'commit_number', value: scmVars.GIT_COMMIT],
                            [$class: 'StringParameterValue', name: 'library_branch', value: env.BRANCH_NAME],
                        ]) 
                    }
                }
            }
        }
    }
}