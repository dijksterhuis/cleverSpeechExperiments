#!/usr/bin/env groovy

pipeline {
    agent { label "gpu" }
    environment {
        IMAGE_NAME = "dijksterhuis/cleverspeech"
        TAG = "latest"
        GITHUB_BRANCH = "master"
        EXP_DIR = "./experiments/Confidence/AlignmentEdgeCases/"
        CLEVERSPEECH_HOME = "/home/cleverspeech/cleverSpeech"
    }
    stages {
        stage("Prep work.") {
            steps {
                script {
                    withDockerRegistry([ credentialsId: "dhub-mr", url: "" ]) {
                        sh "docker container prune -f"
                        sh "docker pull ${IMAGE_NAME}:${TAG}"
                    }
                }
            }
        }

        stage("Run dense experiment."){
            steps {
                script {

                    sh """
                    docker run \
                        --gpus device=${GPU_N} \
                        -t \
                        --rm \
                        --name ${EXP_ARG} \
                        -v \$(pwd)/results/:${CLEVERSPEECH_HOME}/adv/ \
                        -e LOCAL_UID=\$(id -u ${USER}) \
                        -e LOCAL_GID=\$(id -g ${USER}) \
                        ${IMAGE_NAME}:${TAG} \
                        python3 \
                        ${EXP_DIR}/attacks.py \
                        dense \
                        --max_spawns 5
                    """
                }
            }
        }
        stage("Run sparse experiment."){
            steps {
                script {

                    sh """
                    docker run \
                        --gpus device=${GPU_N} \
                        -t \
                        --rm \
                        --name ${EXP_ARG} \
                        -v \$(pwd)/results/:${CLEVERSPEECH_HOME}/adv/ \
                        -e LOCAL_UID=\$(id -u ${USER}) \
                        -e LOCAL_GID=\$(id -g ${USER}) \
                        ${IMAGE_NAME}:${TAG} \
                        python3 \
                        ${EXP_DIR}/attacks.py \
                        sparse \
                        --max_spawns 5
                    """
                }
            }
        }
        stage("Run dense extreme experiment."){
            steps {
                script {

                    sh """
                    docker run \
                        --gpus device=${GPU_N} \
                        -t \
                        --rm \
                        --name ${EXP_ARG} \
                        -v \$(pwd)/results/:${CLEVERSPEECH_HOME}/adv/ \
                        -e LOCAL_UID=\$(id -u ${USER}) \
                        -e LOCAL_GID=\$(id -g ${USER}) \
                        ${IMAGE_NAME}:${TAG} \
                        python3 \
                        ${EXP_DIR}/attacks.py \
                        dense-extreme \
                        --max_spawns 5
                    """
                }
            }
        }
        }
        stage("Run sparse extreme experiment."){
            steps {
                script {

                    sh """
                    docker run \
                        --gpus device=${GPU_N} \
                        -t \
                        --rm \
                        --name ${EXP_ARG} \
                        -v \$(pwd)/results/:${CLEVERSPEECH_HOME}/adv/ \
                        -e LOCAL_UID=\$(id -u ${USER}) \
                        -e LOCAL_GID=\$(id -g ${USER}) \
                        ${IMAGE_NAME}:${TAG} \
                        python3 \
                        ${EXP_DIR}/attacks.py \
                        sparse-extreme \
                        --max_spawns 5
                    """
                }
            }
        }
    }
    post  {
        always {
            sh "docker image prune -f"
            sh "docker container prune -f"
            sh "docker image rm ${IMAGE_NAME}:${TAG}"
        }
    }
}