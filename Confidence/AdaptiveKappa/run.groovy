#!/usr/bin/env groovy

pipeline {
    agent { label "build" }
    environment {
        IMAGE = "dijksterhuis/cleverspeech:latest"
        EXP_DIR = "./experiments/Confidence/AdaptiveKappa/"
        CLEVERSPEECH_HOME = "/home/cleverspeech/cleverSpeech"
    }
    stages {
        stage("Run experiments in parallel."){
            failFast false
            matrix {
                agent { label "gpu" }
                axes {
                    axis {
                        name 'alignment_type'
                        values 'dense', 'sparse', 'ctcalign'
                    }
                    axis {
                        name 'loss_type'
                        values '', '-rctc', '-ctc'
                    }
                }
                stages {
                    stage("Run experiment") {
                        steps {
                            script {
                                echo "+=+=+=+=+=====> Running experiment: ${alignment_type}${loss_type}"
                                def exp = "${alignment_type}${loss_type}"
                                sh """
                                    docker run \
                                        --gpus device=${GPU_N} \
                                        -t \
                                        --rm \
                                        --name ${exp} \
                                        -v \$(pwd)/results/:${CLEVERSPEECH_HOME}/adv/ \
                                        -e LOCAL_UID=\$(id -u ${USER}) \
                                        -e LOCAL_GID=\$(id -g ${USER}) \
                                        ${IMAGE} \
                                        python3 ${EXP_DIR}/attacks.py ${exp} --max_spawns 5
                                """
                            }
                        }
                    }
                }
            }
        }
    }
}

