#!/usr/bin/env groovy

pipeline {
    agent { label "build" }
    options { skipDefaultCheckout() }
    parameters {
            string(name: 'MAX_SPAWNS', defaultValue: '2', description: '')
            string(name: 'N_STEPS', defaultValue: '10', description: '')
            string(name: 'DECODE_STEP', defaultValue: '2', description: '')
            string(name: 'BATCH_SIZE', defaultValue: '2', description: '')
            string(name: 'MAX_EXAMPLES', defaultValue: '4', description: '')
    }
    environment {
        IMAGE = "dijksterhuis/cleverspeech:latest"
        EXP_DIR = "./experiments/CTCBaselines/"
        CLEVERSPEECH_HOME = "/home/cleverspeech/cleverSpeech"
    }
    stages {
        stage("Run experiments in parallel."){
            failFast false
            matrix {
                agent { label "gpu" }
                axes {
                    axis {
                        name 'experiment'
                        values 'ctc', 'ctc_v2'
                    }
                }
                stages {
                    stage("Locked SCM checkout") {
                        steps {
                            lock("dummy") {
                                sleep 5
                                checkout scm
                            }
                        }
                    }
                    stage("Image pull") {
                        steps {
                            script {
                                sh "docker pull ${IMAGE}"
                            }
                        }
                    }
                    stage("Run experiment") {
                        steps {
                            script {
                                echo "+=+=+=+=+=====> Running experiment: ${experiment}"
                                def exp = "${experiment}"
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
                                        python3 ${EXP_DIR}/attacks.py ${exp} \
                                            --max_spawns "${params.MAX_SPAWNS}" \
                                            --batch_size "${params.BATCH_SIZE}" \
                                            --decode_step "${params.DECODE_STEP}" \
                                            --nsteps "${params.N_STEPS}" \
                                            --max_examples "${params.MAX_EXAMPLES}"
                                """
                            }
                        }
                    }
                }
                /* post {
                    always {
                        sh "docker image prune -f"
                        sh "docker container prune -f"
                        sh "docker image rm ${IMAGE}"
                    }
                } */
            }
        }
    }
}
