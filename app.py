from flask import Flask, jsonify, request, render_template
import threading
import time
import os

from dotenv import load_dotenv
from supabase import create_client, Client

# Linear Regression
import pandas as pd
import numpy as np



# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


if not SUPABASE_URL or not SUPABASE_KEY:

    raise ValueError(
        "SUPABASE_URL or SUPABASE_KEY is missing from .env"
    )


# ============================================================
# SUPABASE CLIENT
# ============================================================

def get_supabase_client():
    return create_client(
        SUPABASE_URL,
        SUPABASE_KEY
    )


# ============================================================
# FLASK
# ============================================================

app = Flask(__name__)


# ============================================================
# CURRENT SENSOR DATA
# ============================================================

sensor_data = {

    "ds18b20_temperature": 0.0,
    "dht22_temperature": 0.0,
    "dht22_humidity": 0.0,
    "bh1750_lux": 0.0,
    "battery_voltage": 0.0,
    "battery_soc": 0.0,
    "system_voltage": 0.0,
    "system_current": 0.0,
    "power_watts": 0.0,
    "measurement_quality": "LEGACY",
    "estimated_fields": [],

    "last_update": None
}


# ============================================================
# THREAD LOCK
# ============================================================

data_lock = threading.Lock()


# ============================================================
# RECEIVE SENSOR DATA FROM READ_ARDUINO.PY
# ============================================================

@app.route(
    "/api/receive-sensor",
    methods=["POST"]
)
def receive_sensor():

    global sensor_data

    try:

        data = request.get_json()

        if not data:

            return jsonify({

                "status": "error",

                "message":
                    "No JSON data received"

            }), 400


        # ====================================================
        # GET VALUES
        # ====================================================

        ds18b20_temperature = float(
            data.get(
                "ds18b20_temperature",
                0
            )
        )

        dht22_temperature = float(
            data.get(
                "dht22_temperature",
                0
            )
        )

        dht22_humidity = float(
            data.get(
                "dht22_humidity",
                0
            )
        )

        bh1750_lux = float(
            data.get(
                "bh1750_lux",
                0
            )
        )

        battery_voltage = float(
            data.get(
                "battery_voltage",
                0
            )
        )

        battery_soc = float(
            data.get(
                "battery_soc",
                0
            )
        )

        system_voltage = float(
            data.get(
                "system_voltage",
                0
            )
        )

        system_current = float(
            data.get(
                "system_current",
                0
            )
        )

        power_watts = float(
            data.get(
                "power_watts",
                0
            )
        )

        measurement_quality = str(
            data.get(
                "quality",
                "MEASURED"
            )
        )

        estimated_fields = [
            item.strip()
            for item in measurement_quality.split(";")
            if "ESTIMATED" in item or "INVALID" in item or "UNAVAILABLE" in item
        ]


        # ====================================================
        # UPDATE CURRENT SENSOR DATA
        # ====================================================

        with data_lock:

            sensor_data[
                "ds18b20_temperature"
            ] = ds18b20_temperature

            sensor_data[
                "dht22_temperature"
            ] = dht22_temperature

            sensor_data[
                "dht22_humidity"
            ] = dht22_humidity

            sensor_data[
                "bh1750_lux"
            ] = bh1750_lux

            sensor_data[
                "battery_voltage"
            ] = battery_voltage

            sensor_data[
                "battery_soc"
            ] = battery_soc

            sensor_data[
                "system_voltage"
            ] = system_voltage

            sensor_data[
                "system_current"
            ] = system_current

            sensor_data[
                "power_watts"
            ] = power_watts

            sensor_data[
                "measurement_quality"
            ] = measurement_quality

            sensor_data[
                "estimated_fields"
            ] = estimated_fields

            sensor_data[
                "last_update"
            ] = time.strftime(
                "%Y-%m-%d %H:%M:%S"
            )


        # ====================================================
        # DISPLAY
        # ====================================================

        print("\n========================================")
        print("NEW SENSOR DATA RECEIVED")
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
            f"Data quality        : {measurement_quality}"
        )

        print("========================================\n")

        try:
            save_current_data_to_supabase()
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Sensor data received, but Supabase insert failed: {e}"
            }), 500


        return jsonify({

            "status": "success",

            "message":
                "Sensor data received",

            "data": sensor_data

        }), 200


    except (ValueError, TypeError) as e:

        return jsonify({

            "status": "error",

            "message":
                f"Invalid sensor data: {e}"

        }), 400


    except Exception as e:

        print("Receive sensor error:")
        print(e)

        return jsonify({

            "status": "error",

            "message": str(e)

        }), 500


# ============================================================
# CURRENT SENSOR DATA API
# ============================================================

@app.route("/api/sensor-data")
def get_sensor_data():

    with data_lock:

        return jsonify(sensor_data)


# ============================================================
# SAVE CURRENT DATA TO SUPABASE
# ============================================================

def save_current_data_to_supabase():

    try:

        # ====================================================
        # GET CURRENT DATA
        # ====================================================

        with data_lock:

            current_data = sensor_data.copy()


        # ====================================================
        # CHECK IF REAL DATA HAS BEEN RECEIVED
        # ====================================================

        if current_data["last_update"] is None:

            print(
                "No Arduino data received yet."
            )

            print(
                "Skipping Supabase save."
            )

            return


        # ====================================================
        # DATA FOR SUPABASE
        # ====================================================

        data = {

            "ds18b20_temperature":
                current_data[
                    "ds18b20_temperature"
                ],

            "dht22_temperature":
                current_data[
                    "dht22_temperature"
                ],

            "dht22_humidity":
                current_data[
                    "dht22_humidity"
                ],

            "bh1750_lux":
                current_data[
                    "bh1750_lux"
                ],

            "battery_voltage":
                current_data[
                    "battery_voltage"
                ],

            "battery_soc":
                current_data[
                    "battery_soc"
                ],

            "system_voltage":
                current_data[
                    "system_voltage"
                ],

            "system_current":
                current_data[
                    "system_current"
                ],

            "measurement_quality":
                current_data[
                    "measurement_quality"
                ],

            "estimated_fields":
                current_data[
                    "estimated_fields"
                ]

        }


        # ====================================================
        # INSERT INTO SUPABASE
        # ====================================================

        # ============================================================
        # INSERT INTO SUPABASE WITH RETRY
        # ============================================================

        max_retries = 3
        response = None

        for attempt in range(1, max_retries + 1):

            try:

                print(
                    f"Supabase insert attempt "
                    f"{attempt}/{max_retries}..."
                )

                db = get_supabase_client()

                response = (
                    db
                    .table("sensor_data")
                    .insert(data)
                    .execute()
                )

                print("✓ Supabase insert successful.")
                break

            except Exception as e:

                print(
                    f"✗ Supabase attempt "
                    f"{attempt} failed: {e}"
                )

                if attempt < max_retries:

                    print("Retrying in 3 seconds...")
                    time.sleep(3)

                else:

                    print(
                        "✗ Supabase insert failed "
                        "after all retries."
                    )
                    raise


        print("\n****************************************")
        print("DATA SAVED TO SUPABASE")
        print("----------------------------------------")

        print(
            f"DS18B20 : "
            f"{data['ds18b20_temperature']:.2f} °C"
        )

        print(
            f"DHT22   : "
            f"{data['dht22_temperature']:.2f} °C"
        )

        print(
            f"Humidity: "
            f"{data['dht22_humidity']:.2f} %"
        )

        print(
            f"Light   : "
            f"{data['bh1750_lux']:.2f} lux"
        )

        print(
            f"Voltage : "
            f"{data['system_voltage']:.2f} V"
        )

        print(
            f"Current : "
            f"{data['system_current']:.2f} A"
        )

        # Power is generated by Supabase
        if response.data:
            saved_power = response.data[0].get("power_watts")
        else:
            saved_power = None

        print(
            f"Power   : "
            f"{float(saved_power or 0):.2f} W"
        )

        print("****************************************\n")


    except Exception as e:

        print("\n========================================")
        print("SUPABASE ERROR")
        print("========================================")
        print("Error type:", type(e).__name__)
        print("Error:", repr(e))
        print("========================================\n")
        raise


# ============================================================
# DATABASE API
# ============================================================

@app.route("/api/database")
def get_database_data():

    try:

        db = get_supabase_client()

        response = (
            db
            .table("sensor_data")
            .select("*")
            .order(
                "created_at",
                desc=True
            )
            .limit(60)
            .execute()
        )

        return jsonify(response.data)


    except Exception as e:

        return jsonify({

            "status": "error",

            "message": str(e)

        }), 500


# ============================================================
# LINEAR REGRESSION API
# ============================================================

@app.route("/api/regression")
def regression():

    try:

        print("\n========================================")
        print("RUNNING MULTIPLE LINEAR REGRESSION")
        print("========================================")


        # ====================================================
        # GET HISTORICAL DATA FROM SUPABASE
        # ====================================================

        db = get_supabase_client()

        response = (
            db
            .table("sensor_data")
            .select(
                "created_at,"
                "ds18b20_temperature,"
                "dht22_temperature,"
                "dht22_humidity,"
                "bh1750_lux,"
                "power_watts,"
                "measurement_quality,"
                "estimated_fields"
            )
            .order(
                "created_at",
                desc=False
            )
            .execute()
        )


        data = response.data


        print(
            f"Records retrieved: {len(data)}"
        )
        print("Regression will use directly measured records only.")


        # ====================================================
        # CHECK DATA COUNT
        # ====================================================

        if len(data) < 10:

            return jsonify({

                "status": "error",

                "message":
                    "Not enough data for regression.",

                "required_records": 10,

                "available_records":
                    len(data)

            }), 400


        # ====================================================
        # CONVERT SUPABASE DATA TO NUMPY
        # ====================================================

        clean_data = []


        for row in data:

            try:

                ds18b20 = float(
                    row["ds18b20_temperature"]
                )

                dht22 = float(
                    row["dht22_temperature"]
                )

                humidity = float(
                    row["dht22_humidity"]
                )

                lux = float(
                    row["bh1750_lux"]
                )

                power = float(
                    row["power_watts"]
                )


                # --------------------------------------------
                # CHECK FOR FINITE VALUES
                # --------------------------------------------

                measurement_quality = str(
                    row.get("measurement_quality", "LEGACY")
                )

                estimated_fields = row.get("estimated_fields") or []

                # Regression must use directly measured records only.
                # Estimated/imputed values remain useful for monitoring,
                # but including them would make the statistical result
                # look more certain than the physical measurements justify.
                is_measured = (
                    measurement_quality == "MEASURED"
                    and len(estimated_fields) == 0
                )

                values = [
                    ds18b20,
                    dht22,
                    humidity,
                    lux,
                    power
                ]


                if (
                    is_measured
                    and all(
                        np.isfinite(value)
                        for value in values
                    )
                ):

                    clean_data.append(values)


            except (
                ValueError,
                TypeError,
                KeyError
            ):

                continue


        # ====================================================
        # CHECK CLEAN DATA
        # ====================================================

        if len(clean_data) < 10:

            return jsonify({

                "status": "error",

                "message":
                    "Not enough complete numeric "
                    "records after cleaning.",

                "available_records":
                    len(clean_data)

            }), 400


        # ====================================================
        # CONVERT TO NUMPY ARRAY
        # ====================================================

        dataset = np.array(
            clean_data,
            dtype=float
        )


        # ====================================================
        # INPUT VARIABLES
        # ====================================================
        #
        # X1 = DS18B20 temperature
        # X2 = DHT22 temperature
        # X3 = DHT22 humidity
        # X4 = BH1750 light
        #
        # ====================================================

        X = dataset[:, 0:4]


        # ====================================================
        # TARGET VARIABLE
        # ====================================================
        #
        # Y = Power
        #
        # ====================================================

        y = dataset[:, 4]


        # ====================================================
        # TRAIN / TEST SPLIT
        # ====================================================
        #
        # 80% training
        # 20% testing
        #
        # We use a fixed seed so the result is reproducible.
        #
        # ====================================================

        np.random.seed(42)


        indices = np.arange(
            len(X)
        )


        np.random.shuffle(
            indices
        )


        split_index = int(
            len(indices) * 0.80
        )


        train_indices = indices[
            :split_index
        ]

        test_indices = indices[
            split_index:
        ]


        X_train = X[
            train_indices
        ]

        y_train = y[
            train_indices
        ]


        X_test = X[
            test_indices
        ]

        y_test = y[
            test_indices
        ]


        # ====================================================
        # ADD INTERCEPT COLUMN
        # ====================================================
        #
        # Regression equation:
        #
        # Y = b0 + b1X1 + b2X2 + b3X3 + b4X4
        #
        # ====================================================

        X_train_with_intercept = np.column_stack(

            (
                np.ones(
                    len(X_train)
                ),

                X_train
            )

        )


        # ====================================================
        # TRAIN LINEAR REGRESSION
        # ====================================================
        #
        # NumPy least-squares solution:
        #
        # coefficients =
        #     (XᵀX)^-1 XᵀY
        #
        # np.linalg.lstsq is numerically safer.
        #
        # ====================================================

        coefficients = np.linalg.lstsq(

            X_train_with_intercept,

            y_train,

            rcond=None

        )[0]


        # ====================================================
        # EXTRACT COEFFICIENTS
        # ====================================================

        intercept = coefficients[0]

        b1 = coefficients[1]

        b2 = coefficients[2]

        b3 = coefficients[3]

        b4 = coefficients[4]


        # ====================================================
        # TEST DATA WITH INTERCEPT
        # ====================================================

        X_test_with_intercept = np.column_stack(

            (
                np.ones(
                    len(X_test)
                ),

                X_test
            )

        )


        # ====================================================
        # PREDICT POWER
        # ====================================================

        y_pred = (
            X_test_with_intercept
            @ coefficients
        )


        # ====================================================
        # R² SCORE
        # ====================================================

        ss_res = np.sum(
            (y_test - y_pred) ** 2
        )


        ss_tot = np.sum(
            (y_test - np.mean(y_test)) ** 2
        )


        if ss_tot == 0:

            r2 = 0.0

        else:

            r2 = 1 - (
                ss_res / ss_tot
            )


        # ====================================================
        # MAE
        # ====================================================

        mae = np.mean(
            np.abs(
                y_test - y_pred
            )
        )


        # ====================================================
        # RMSE
        # ====================================================

        rmse = np.sqrt(

            np.mean(
                (y_test - y_pred) ** 2
            )

        )


        # ====================================================
        # PREDICT LATEST POWER
        # ====================================================

        latest = dataset[-1]


        latest_input = np.array([

            1.0,

            latest[0],

            latest[1],

            latest[2],

            latest[3]

        ])


        predicted_power = (

            latest_input
            @ coefficients

        )


        actual_power = latest[4]


        # ====================================================
        # REGRESSION EQUATION
        # ====================================================

        equation = (

            f"Power = "

            f"{intercept:.6f} "

            f"+ ({b1:.6f} × DS18B20) "

            f"+ ({b2:.6f} × DHT22) "

            f"+ ({b3:.6f} × Humidity) "

            f"+ ({b4:.6f} × Light)"

        )


        # ====================================================
        # PRINT RESULTS
        # ====================================================

        print()
        print("----------------------------------------")
        print("LINEAR REGRESSION RESULTS")
        print("----------------------------------------")

        print(
            f"Data points : {len(dataset)}"
        )

        print(
            f"Training    : {len(X_train)}"
        )

        print(
            f"Testing     : {len(X_test)}"
        )

        print()

        print(
            f"R²          : {r2:.4f}"
        )

        print(
            f"MAE         : {mae:.4f} W"
        )

        print(
            f"RMSE        : {rmse:.4f} W"
        )

        print()

        print(
            f"Actual Power    : "
            f"{actual_power:.4f} W"
        )

        print(
            f"Predicted Power : "
            f"{predicted_power:.4f} W"
        )

        print()

        print(
            "Regression Equation:"
        )

        print(
            equation
        )

        print("----------------------------------------")


        # ====================================================
        # RETURN JSON
        # ====================================================

        return jsonify({

            "status": "success",

            "model":
                "Multiple Linear Regression",

            "target":
                "power_watts",

            "features": [

                "ds18b20_temperature",

                "dht22_temperature",

                "dht22_humidity",

                "bh1750_lux"

            ],

            "data_points":
                int(len(dataset)),

            "training_points":
                int(len(X_train)),

            "testing_points":
                int(len(X_test)),

            "r2":
                round(
                    float(r2),
                    4
                ),

            "mae":
                round(
                    float(mae),
                    4
                ),

            "rmse":
                round(
                    float(rmse),
                    4
                ),

            "intercept":
                round(
                    float(intercept),
                    6
                ),

            "coefficients": {

                "ds18b20_temperature":
                    round(
                        float(b1),
                        6
                    ),

                "dht22_temperature":
                    round(
                        float(b2),
                        6
                    ),

                "dht22_humidity":
                    round(
                        float(b3),
                        6
                    ),

                "bh1750_lux":
                    round(
                        float(b4),
                        6
                    )

            },

            "actual_power":
                round(
                    float(actual_power),
                    4
                ),

            "predicted_power":
                round(
                    float(predicted_power),
                    4
                ),

            "equation":
                equation

        })


    except Exception as e:

        print()
        print("========================================")
        print("REGRESSION ERROR")
        print("========================================")
        print(e)


        return jsonify({

            "status": "error",

            "message":
                str(e)

        }), 500


# ============================================================
# HOME PAGE
# ============================================================

@app.route("/")
def home():

    return render_template("dashboard.html")


# ============================================================
# START APPLICATION
# ============================================================

if __name__ == "__main__":

    # ========================================================
    # START FLASK
    # ========================================================

    app.run(

        host="0.0.0.0",

        port=5000,

        debug=False

    )