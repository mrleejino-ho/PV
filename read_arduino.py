import os
import serial
import time
import requests

from dotenv import load_dotenv

load_dotenv()


# ============================================================
# PHOTOVOLTAIC MONITORING PROTOTYPE
#
# Arduino Uno
#      ↓ USB
# read_arduino.py
#      ↓ HTTP POST
# Flask
#      ↓
# Supabase
#
# Arduino reading interval: 20 seconds
# Supabase is written by Flask when each POST is received.
# The Arduino sends a quality/status field so estimated values
# can be kept separate from directly measured research data.
# ============================================================


# ============================================================
# CONFIGURATION
# ============================================================

ARDUINO_PORT = "COM4"

BAUD_RATE = 9600

FLASK_URL = os.getenv(
    "FLASK_URL",
    "https://pvmonitoringsystem.vercel.app/api/receive-sensor"
)

READ_INTERVAL = 20


# ============================================================
# CONNECT TO ARDUINO
# ============================================================

try:

    arduino = serial.Serial(
        ARDUINO_PORT,
        BAUD_RATE,
        timeout=5
    )

    # Arduino usually resets when serial connection opens.
    time.sleep(2)

    print("========================================")
    print("PHOTOVOLTAIC MONITORING PROTOTYPE")
    print("========================================")
    print("Arduino connected!")
    print(f"Port          : {ARDUINO_PORT}")
    print(f"Baud rate     : {BAUD_RATE}")
    print(f"Read interval : {READ_INTERVAL} seconds")
    print("========================================")
    print()


except serial.SerialException as e:

    print("========================================")
    print("ERROR: Could not connect to Arduino.")
    print("========================================")
    print(e)

    exit()


# ============================================================
# MAIN READING LOOP
# ============================================================

while True:

    try:

        print("Waiting for Arduino sensor reading...")


        # ====================================================
        # READ ONE LINE FROM ARDUINO
        # ====================================================

        line = arduino.readline().decode(
            "utf-8",
            errors="ignore"
        ).strip()


        # ====================================================
        # IGNORE EMPTY DATA
        # ====================================================

        if not line:

            print("No data received.")

            continue


        print(f"Arduino: {line}")


        # ====================================================
        # IGNORE DEBUG / TEXT MESSAGES
        # ====================================================

        if not line[0].isdigit() and line[0] != "-":

            print("Arduino message ignored.")

            continue


        # ====================================================
        # SPLIT CSV DATA
        # ====================================================
        #
        # Expected Arduino format:
        #
        # DS18B20,
        # DHT22 Temperature,
        # DHT22 Humidity,
        # BH1750 Lux,
        # Battery Voltage,
        # Battery SOC,
        # System Voltage,
        # System Current,
        # Power
        # Quality/status flags
        #
        # Example:
        #
        # 25.37,26.80,95.20,450.00,12.10,85.00,3.75,0.50,1.88,MEASURED
        #
        # ====================================================

        values = line.split(",")


        # ====================================================
        # CHECK NUMBER OF VALUES
        # ====================================================

        if len(values) != 10:

            print(
                "Unexpected data format."
            )

            print(
                f"Expected 10 values, "
                f"received {len(values)}."
            )

            continue


        try:

            # =================================================
            # CONVERT SENSOR VALUES
            # =================================================

            ds18b20_temperature = float(
                values[0]
            )

            dht22_temperature = float(
                values[1]
            )

            dht22_humidity = float(
                values[2]
            )

            bh1750_lux = float(
                values[3]
            )

            battery_voltage = float(
                values[4]
            )

            battery_soc = float(
                values[5]
            )

            system_voltage = float(
                values[6]
            )

            system_current = float(
                values[7]
            )

            power_watts = float(
                values[8]
            )

            quality = values[9].strip() or "MEASURED"


            # =================================================
            # DISPLAY SENSOR DATA
            # =================================================

            print()
            print("----------------------------------------")
            print("SENSOR DATA")
            print("----------------------------------------")

            print(
                f"DS18B20 Temperature : "
                f"{ds18b20_temperature:.2f} °C"
            )

            print(
                f"DHT22 Temperature   : "
                f"{dht22_temperature:.2f} °C"
            )

            print(
                f"DHT22 Humidity      : "
                f"{dht22_humidity:.2f} %"
            )

            print(
                f"BH1750 Light        : "
                f"{bh1750_lux:.2f} lux"
            )

            print(
                f"Battery Voltage     : "
                f"{battery_voltage:.3f} V"
            )

            print(
                f"Battery SOC         : "
                f"{battery_soc:.2f} %"
            )

            print(
                f"System Voltage      : "
                f"{system_voltage:.2f} V"
            )

            print(
                f"System Current      : "
                f"{system_current:.2f} A"
            )

            print(
                f"Power               : "
                f"{power_watts:.2f} W"
            )

            print(
                f"Data quality        : {quality}"
            )

            print("----------------------------------------")


            # =================================================
            # CREATE JSON
            # =================================================
            #
            # IMPORTANT:
            #
            # These names match the fields expected by Flask
            # and correspond directly to your Supabase columns.
            #
            # =================================================

            data = {

                "ds18b20_temperature":
                    ds18b20_temperature,

                "dht22_temperature":
                    dht22_temperature,

                "dht22_humidity":
                    dht22_humidity,

                "bh1750_lux":
                    bh1750_lux,

                "battery_voltage":
                    battery_voltage,

                "battery_soc":
                    battery_soc,

                "system_voltage":
                    system_voltage,

                "system_current":
                    system_current,

                "power_watts":
                    power_watts,

                "quality":
                    quality

            }


            # =================================================
            # SEND DATA TO FLASK
            # =================================================

            print()
            print("Sending data to Flask...")


            try:

                response = requests.post(

                    FLASK_URL,

                    json=data,

                    timeout=5

                )


                # =============================================
                # FLASK SUCCESS
                # =============================================

                if response.status_code == 200:

                    print(
                        "✓ Successfully sent "
                        "sensor data to Flask."
                    )

                    print(
                        "✓ Flask received the data."
                    )


                # =============================================
                # FLASK ERROR
                # =============================================

                else:

                    print(
                        "✗ Flask returned an error."
                    )

                    print(
                        f"Status code: "
                        f"{response.status_code}"
                    )

                    print(
                        f"Response: "
                        f"{response.text}"
                    )


            except requests.RequestException as e:

                print()
                print(
                    "✗ Could not connect to Flask."
                )

                print(e)


        # ====================================================
        # INVALID NUMERIC DATA
        # ====================================================

        except ValueError:

            print()
            print(
                "✗ Invalid numeric sensor data."
            )

            print(
                f"Received: {line}"
            )


        # ====================================================
        # WAIT BEFORE NEXT READING
        # ====================================================

        print()
        print(
            "========================================"
        )

        print(
            f"Next Arduino reading in "
            f"{READ_INTERVAL} seconds..."
        )

        print(
            "========================================"
        )

        print()

        time.sleep(READ_INTERVAL)


    # ========================================================
    # STOP PROGRAM
    # ========================================================

    except KeyboardInterrupt:

        print()
        print("========================================")
        print("Stopping Arduino reader...")
        print("========================================")

        arduino.close()

        print("Arduino connection closed.")

        break


    # ========================================================
    # UNEXPECTED ERROR
    # ========================================================

    except Exception as e:

        print()
        print("========================================")
        print("Unexpected error:")
        print("========================================")

        print(e)

        print()
        print("Retrying in 5 seconds...")

        time.sleep(5)