#!/usr/bin/env groovy

pipeline {
    agent { label "gpu" }
    environment {
        IMAGE = "dijksterhuis/cleverspeech:latest"
        EXP_DIR = "./experiments/Confidence/MaxDiffAdaptiveKappaConf/"
        CLEVERSPEECH_HOME = "/home/cleverspeech/cleverSpeech"
    }
    stages {
        stage("Prep work.") {
            steps {
                script {
                    withDockerRegistry([ credentialsId: "dhub-mr", url: "" ]) {
                        sh "docker container prune -f"
                        sh "docker pull ${IMAGE}"
                    }
                }
            }
        }
        stage("Run Dense Align experiments."){
            steps {
                script {
                    def experiments = ['dense', 'dense_rctc', 'dense_ctc']
                    for (int i = 0; i < experiments.size(); ++i) {
                        echo "Running ${experiments[i]}"
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
                                ${experiments[i]} \
                                --max_spawns 5
                        """
                    }

                }
            }
        }
        stage("Run Sparse Align experiments."){
            steps {
                script {
                    def experiments = ['sparse', 'sparse_rctc', 'sparse_ctc']
                    for (int i = 0; i < experiments.size(); ++i) {
                        echo "Running ${experiments[i]}"
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
                                ${experiments[i]} \
                                --max_spawns 5
                        """
                    }

                }
            }
        }
        stage("Run CTC Align experiments."){
            steps {
                script {
                    def experiments = ['ctcalign', 'ctcalign_rctc', 'ctcalign_ctc']
                    for (int i = 0; i < experiments.size(); ++i) {
                        echo "Running ${experiments[i]}"
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
                                ${experiments[i]} \
                                --max_spawns 5
                        """
                    }

                }
            }
        }
    }
    post  {
        always {
            sh "docker image prune -f"
            sh "docker container prune -f"
            sh "docker image rm ${IMAGE}"
        }
    }
}