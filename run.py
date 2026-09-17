import subprocess
import sys
import time
import os
import webbrowser
time.sleep(3)
webbrowser.open("http://127.0.0.1:5000")


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

APP_FILE = os.path.join(BASE_DIR, "app.py")
ARDUINO_FILE = os.path.join(BASE_DIR, "read_arduino.py")


# ============================================================
# START
# ============================================================

print("========================================")
print(" PHOTOVOLTAIC MONITORING PROTOTYPE")
print("========================================")
print()
print("Starting Flask and Arduino reader...")
print()


# ============================================================
# START FLASK
# ============================================================

flask_process = subprocess.Popen(
    [sys.executable, APP_FILE]
)

print("Flask server starting...")
print("Dashboard: http://127.0.0.1:5000")
print()


# Give Flask time to start
time.sleep(3)


# ============================================================
# START ARDUINO READER
# ============================================================

arduino_process = subprocess.Popen(
    [sys.executable, ARDUINO_FILE]
)

print("Arduino reader starting...")
print()


# ============================================================
# KEEP BOTH PROGRAMS RUNNING
# ============================================================

try:

    while True:

        # Check whether Flask stopped
        if flask_process.poll() is not None:

            print("Flask stopped.")

            break


        # Check whether Arduino reader stopped
        if arduino_process.poll() is not None:

            print("Arduino reader stopped.")

            break


        time.sleep(1)


except KeyboardInterrupt:

    print()
    print("Stopping Photovoltaic Monitoring Prototype...")


finally:

    # ========================================================
    # STOP ARDUINO READER
    # ========================================================

    if arduino_process.poll() is None:

        print("Stopping Arduino reader...")

        arduino_process.terminate()

        try:

            arduino_process.wait(timeout=5)

        except subprocess.TimeoutExpired:

            arduino_process.kill()


    # ========================================================
    # STOP FLASK
    # ========================================================

    if flask_process.poll() is None:

        print("Stopping Flask server...")

        flask_process.terminate()

        try:

            flask_process.wait(timeout=5)

        except subprocess.TimeoutExpired:

            flask_process.kill()


    print()
    print("========================================")
    print(" SYSTEM STOPPED")
    print("========================================")