pipeline {
    agent any

    environment {
        REPORT_DIR   = "reports"
        VENV_DIR     = ".venv"
        PYTHON       = "python3"
        QEMU_IMAGE   = "/workspace/romulus/obmc-phosphor-image-romulus-20250902012112.static.mtd"
        QEMU_PIDFILE = "qemu.pid"
        BMC_URL      = "https://127.0.0.1:2443"
    }

    options {
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timeout(time: 90, unit: 'MINUTES')
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                sh "rm -rf ${REPORT_DIR} && mkdir -p ${REPORT_DIR}"
            }
        }

        stage('Prepare Python env') {
            steps {
                sh """
                    ${PYTHON} -m venv ${VENV_DIR}
                    . ${VENV_DIR}/bin/activate
                    pip install --upgrade pip
                    pip install pytest pytest-html requests selenium locust
                """
            }
        }

        stage('Start QEMU with OpenBMC') {
            steps {
                sh """
                    if pgrep -x qemu-system-arm > /dev/null; then
                        echo "QEMU already running, killing it first"
                        pkill -x qemu-system-arm || true
                        sleep 2
                    fi

                    nohup qemu-system-arm -m 256 -M romulus-bmc -nographic \\
                      -drive file=${QEMU_IMAGE},format=raw,if=mtd \\
                      -net nic \\
                      -net user,hostfwd=:0.0.0.0:2222-:22,hostfwd=:0.0.0.0:2443-:443,hostfwd=udp:0.0.0.0:2623-:623,hostname=qemu \\
                      > ${REPORT_DIR}/qemu.log 2>&1 &
                    echo \$! > ${QEMU_PIDFILE}
                    echo "QEMU started, PID=\$(cat ${QEMU_PIDFILE})" | tee ${REPORT_DIR}/qemu_start.log
                """
            }
            post {
                always {
                    archiveArtifacts artifacts: "${REPORT_DIR}/qemu*.log", allowEmptyArchive: true
                }
            }
        }

        stage('Wait for OpenBMC') {
            steps {
                sh """
                    echo "Waiting for ${BMC_URL} ..." | tee ${REPORT_DIR}/connectivity.log
                    for i in \$(seq 1 120); do
                        if curl -kfsS --max-time 5 ${BMC_URL} -o /dev/null; then
                            echo "OpenBMC ready after \$((i*5))s" | tee -a ${REPORT_DIR}/connectivity.log
                            exit 0
                        fi
                        echo "attempt \$i failed, retry in 5s" | tee -a ${REPORT_DIR}/connectivity.log
                        sleep 5
                    done
                    echo "OpenBMC NOT reachable" | tee -a ${REPORT_DIR}/connectivity.log
                    exit 1
                """
            }
            post {
                always {
                    archiveArtifacts artifacts: "${REPORT_DIR}/connectivity.log", allowEmptyArchive: true
                }
            }
        }

        stage('API tests (PyTest + Redfish)') {
            steps {
                    sh """
                        . ${VENV_DIR}/bin/activate 
                        mkdir -p ${REPORT_DIR}/api-tests
                        pytest test_redfish.py \\
                            --junitxml=${REPORT_DIR}/api-tests/junit.xml \\
                            --html=${REPORT_DIR}/api-tests/report.html --self-contained-html \\
                            -v 2>&1 | tee ${REPORT_DIR}/api-tests/pytest.log || true
                    """
            }
            post {
                always {
                    junit allowEmptyResults: true, skipMarkingBuildUnstable, testResults: "${REPORT_DIR}/api-tests/junit.xml"
                    archiveArtifacts artifacts: "${REPORT_DIR}/api-tests/**", allowEmptyArchive: true
                    publishHTML(target: [
                        allowMissing: true, alwaysLinkToLastBuild: true, keepAll: true,
                        reportDir: "${REPORT_DIR}/api-tests",
                        reportFiles: 'report.html',
                        reportName: 'OpenBMC API (Redfish) Report'
                    ])
                }
            }
        }

        stage('WebUI tests (Selenium)') {
            steps {
                    sh """
                        . ${VENV_DIR}/bin/activate
                        mkdir -p ${REPORT_DIR}/webui-tests
                        xvfb-run -a ${PYTHON} openbmc_auth_tests.py \\
                            2>&1 | tee ${REPORT_DIR}/webui-tests/selenium.log || true
                    """
            }
            post {
                always {
                    archiveArtifacts artifacts: "${REPORT_DIR}/webui-tests/**", allowEmptyArchive: true
                }
            }
        }

        stage('Load tests (Locust)') {
            steps {
                    sh """
                        . ${VENV_DIR}/bin/activate 
                        mkdir -p ${REPORT_DIR}/load-tests
                        locust -f locustfile.py \\
                            --headless -u 20 -r 5 -t 60s \\
                            --csv=${REPORT_DIR}/load-tests/locust \\
                            --html=${REPORT_DIR}/load-tests/report.html \\
                            2>&1 | tee ${REPORT_DIR}/load-tests/locust.log || true
                    """
            }
            post {
                always {
                    archiveArtifacts artifacts: "${REPORT_DIR}/load-tests/**", allowEmptyArchive: true
                    publishHTML(target: [
                        allowMissing: true, alwaysLinkToLastBuild: true, keepAll: true,
                        reportDir: "${REPORT_DIR}/load-tests",
                        reportFiles: 'report.html',
                        reportName: 'OpenBMC Load Test Report'
                    ])
                }
            }
        }
    }

    post {
        always {
            sh """
                if [ -f ${QEMU_PIDFILE} ]; then
                    echo "Stopping QEMU PID=\$(cat ${QEMU_PIDFILE})"
                    kill \$(cat ${QEMU_PIDFILE}) || true
                    rm -f ${QEMU_PIDFILE}
                fi
                pkill -x qemu-system-arm || true
            """
            archiveArtifacts artifacts: "${REPORT_DIR}/**", allowEmptyArchive: true
        }
    }
}
