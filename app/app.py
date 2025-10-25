# app.py

# Importing essential libraries and modules
import io
import logging
import os
import pickle

import config  # Assuming config.py holds your weather_api_key
import numpy as np
import pandas as pd
import requests
import torch
from flask import Flask, flash, redirect, render_template, request, url_for
from markupsafe import Markup
from PIL import Image
from torchvision import transforms

# --- CHANGE: Import custom modules more cleanly
from utils.disease import disease_dic
from utils.fertilizer import fertilizer_dic
from utils.model import ResNet9

# ==============================================================================================
# --- CHANGE: Set up basic logging to see errors in the console
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
# ==============================================================================================

app = Flask(__name__)
# --- CHANGE: Add a secret key for flash messages to work.
# It's better to set this as an environment variable in production.
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24))

# ==============================================================================================
# -------------------------LOADING THE TRAINED MODELS & DATA -----------------------------------
# ==============================================================================================

# Loading plant disease classification model
disease_classes = [
    "Apple___Apple_scab",
    "Apple___Black_rot",
    "Apple___Cedar_apple_rust",
    "Apple___healthy",
    "Blueberry___healthy",
    "Cherry_(including_sour)___Powdery_mildew",
    "Cherry_(including_sour)___healthy",
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot",
    "Corn_(maize)___Common_rust_",
    "Corn_(maize)___Northern_Leaf_Blight",
    "Corn_(maize)___healthy",
    "Grape___Black_rot",
    "Grape___Esca_(Black_Measles)",
    "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)",
    "Grape___healthy",
    "Orange___Haunglongbing_(Citrus_greening)",
    "Peach___Bacterial_spot",
    "Peach___healthy",
    "Pepper,_bell___Bacterial_spot",
    "Pepper,_bell___healthy",
    "Potato___Early_blight",
    "Potato___Late_blight",
    "Potato___healthy",
    "Raspberry___healthy",
    "Soybean___healthy",
    "Squash___Powdery_mildew",
    "Strawberry___Leaf_scorch",
    "Strawberry___healthy",
    "Tomato___Bacterial_spot",
    "Tomato___Early_blight",
    "Tomato___Late_blight",
    "Tomato___Leaf_Mold",
    "Tomato___Septoria_leaf_spot",
    "Tomato___Spider_mites Two-spotted_spider_mite",
    "Tomato___Target_Spot",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus",
    "Tomato___Tomato_mosaic_virus",
    "Tomato___healthy",
]

try:
    disease_model_path = "models/plant_disease_model.pth"
    disease_model = ResNet9(3, len(disease_classes))
    disease_model.load_state_dict(
        torch.load(disease_model_path, map_location=torch.device("cpu"))
    )
    disease_model.eval()
    logging.info("✅ Disease detection model loaded successfully.")
except Exception as e:
    logging.error(f"❌ Error loading disease model: {e}")
    disease_model = None

# Loading crop recommendation model
try:
    crop_recommendation_model_path = "models/RandomForest.pkl"
    crop_recommendation_model = pickle.load(open(crop_recommendation_model_path, "rb"))
    logging.info("✅ Crop recommendation model loaded successfully.")
except Exception as e:
    logging.error(f"❌ Error loading crop recommendation model: {e}")
    crop_recommendation_model = None

# --- CHANGE: Load fertilizer data ONCE at startup, not on every request.
try:
    fertilizer_csv_path = os.path.join(
        os.path.dirname(__file__), "Data", "fertilizer.csv"
    )
    fertilizer_df = pd.read_csv(fertilizer_csv_path)
    logging.info("✅ Fertilizer data loaded successfully.")
except Exception as e:
    logging.error(f"❌ Error loading fertilizer.csv: {e}")
    fertilizer_df = None


# =========================================================================================
# ----------------- CUSTOM FUNCTIONS FOR PREDICTIONS AND API CALLS ------------------------
# =========================================================================================


def weather_fetch(city_name):
    """
    Fetch temperature and humidity using WeatherAPI.
    --- CHANGE: Added robust error handling.
    """
    base_url = "http://api.weatherapi.com/v1/current.json"
    params = {"key": config.weather_api_key, "q": city_name}

    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()  # Will raise an exception for HTTP error codes
        data = response.json()

        if "error" in data:
            logging.error(
                f"Weather API error for city '{city_name}': {data['error']['message']}"
            )
            return None, None

        temperature = data["current"]["temp_c"]
        humidity = data["current"]["humidity"]
        return temperature, humidity

    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Network error fetching weather for '{city_name}': {e}")
        return None, None
    except KeyError as e:
        logging.error(
            f"❌ Unexpected API response format for '{city_name}': Missing key {e}"
        )
        return None, None


def predict_image(img_bytes, model=disease_model):
    """
    Transforms image to tensor and predicts disease label with confidence score.
    """
    if model is None:
        raise RuntimeError("Disease model is not loaded.")

    transform = transforms.Compose(
        [
            transforms.Resize(256),
            transforms.ToTensor(),
        ]
    )

    image = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    img_t = transform(image)
    img_u = torch.unsqueeze(img_t, 0)

    with torch.no_grad():
        yb = model(img_u)
        probs = torch.nn.functional.softmax(yb, dim=1)
        top_prob, preds = torch.max(probs, dim=1)

    prediction_index = preds[0].item()
    confidence = top_prob[0].item() * 100
    return disease_classes[prediction_index], round(confidence, 2)


# ===============================================================================================
# ------------------------------------ FLASK APP ROUTES -----------------------------------------
# ===============================================================================================


@app.route("/")
def home():
    title = "FarmIQ - Home"
    return render_template("index.html", title=title)


# --- Render form pages ---
@app.route("/crop-recommend")
def crop_recommend():
    title = "FarmIQ - Crop Recommendation"
    return render_template("crop.html", title=title)


@app.route("/fertilizer")
def fertilizer_recommendation():
    title = "FarmIQ - Fertilizer Suggestion"
    return render_template("fertilizer.html", title=title)


# --- CHANGE: Added a GET route for the disease prediction page
@app.route("/disease")
def disease_page():
    title = "FarmIQ - Disease Detection"
    return render_template("disease.html", title=title)


# ===============================================================================================
# --------------------------------- RENDER PREDICTION PAGES -----------------------------------
# ===============================================================================================


@app.route("/crop-predict", methods=["POST"])
def crop_prediction():
    title = "FarmIQ - Crop Recommendation"

    if request.method == "POST":
        # --- CHANGE: Added input validation with try-except block
        try:
            N = int(request.form["nitrogen"])
            P = int(request.form["phosphorous"])
            K = int(request.form["pottasium"])
            ph = float(request.form["ph"])
            rainfall = float(request.form["rainfall"])
        except (ValueError, KeyError):
            flash("❌ Invalid input. Please enter numeric values for all fields.")
            return redirect(url_for("crop_recommend"))

        city = request.form.get("city")
        if not city:
            flash("❌ Please enter a city name.")
            return redirect(url_for("crop_recommend"))

        weather_data = weather_fetch(city)

        if weather_data and weather_data[0] is not None:
            temperature, humidity = weather_data
            data = np.array([[N, P, K, temperature, humidity, ph, rainfall]])
            if crop_recommendation_model is None:
                flash(
                    "❌ Crop recommendation model is unavailable. Please try again later."
                )
                return redirect(url_for("crop_recommend"))
            my_prediction = crop_recommendation_model.predict(data)
            final_prediction = my_prediction[0]

            return render_template(
                "crop-result.html", prediction=final_prediction, title=title
            )
        else:
            flash(
                f"❌ Could not fetch weather data for '{city}'. Please check the city name and try again."
            )
            return redirect(url_for("crop_recommend"))

    return redirect(url_for("crop_recommend"))


@app.route("/fertilizer-predict", methods=["POST"])
def fert_recommend():
    title = "FarmIQ - Fertilizer Suggestion"

    if request.method == "POST":
        try:
            crop_name = str(request.form["cropname"])
            N = int(request.form["nitrogen"])
            P = int(request.form["phosphorous"])
            K = int(request.form["pottasium"])
        except (ValueError, KeyError):
            flash("❌ Invalid input. Please fill all fields with appropriate values.")
            return redirect(url_for("fertilizer_recommendation"))

        # --- CHANGE: Use the pre-loaded DataFrame
        if fertilizer_df is None:
            flash("❌ Server error: Fertilizer data is not available.")
            return redirect(url_for("fertilizer_recommendation"))

        try:
            # Get required nutrients from the DataFrame
            crop_row = fertilizer_df[fertilizer_df["Crop"] == crop_name]
            if crop_row.empty:
                flash(f"❌ Fertilizer information for '{crop_name}' is not available.")
                return redirect(url_for("fertilizer_recommendation"))

            nr = crop_row["N"].iloc[0]
            pr = crop_row["P"].iloc[0]
            kr = crop_row["K"].iloc[0]
        except Exception as e:
            logging.error(f"Error processing fertilizer data for '{crop_name}': {e}")
            flash("❌ An error occurred while processing fertilizer data.")
            return redirect(url_for("fertilizer_recommendation"))

        # Calculate nutrient difference
        n = nr - N
        p = pr - P
        k = kr - K

        # Determine which nutrient is most deficient/excessive
        temp = {abs(n): "N", abs(p): "P", abs(k): "K"}
        max_value_key = max(temp.keys())
        max_value_nutrient = temp[max_value_key]

        if max_value_nutrient == "N":
            key = "NHigh" if n < 0 else "Nlow"
        elif max_value_nutrient == "P":
            key = "PHigh" if p < 0 else "Plow"
        else:
            key = "KHigh" if k < 0 else "Klow"

        response = Markup(str(fertilizer_dic.get(key, "No recommendation available.")))

        return render_template(
            "fertilizer-result.html", recommendation=response, title=title
        )

    return redirect(url_for("fertilizer_recommendation"))


@app.route("/disease-predict", methods=["POST"])
def disease_prediction():
    title = "FarmIQ - Disease Detection"

    if request.method == "POST":
        if "file" not in request.files:
            flash("❌ No file part")
            return redirect(url_for("disease_page"))

        file = request.files.get("file")
        if not file or file.filename == "":
            flash("❌ No selected file")
            return redirect(url_for("disease_page"))

        # --- CHANGE: Use a proper try-except block
        try:
            img_bytes = file.read()
            prediction_class, confidence = predict_image(img_bytes)
            remedy = Markup(
                str(
                    disease_dic.get(
                        prediction_class, "No remedy information available."
                    )
                )
            )
            return render_template(
                "disease-result.html",
                prediction=remedy,
                confidence=confidence,
                prediction_class=prediction_class,
                title=title,
            )

        except Exception as e:
            logging.error(f"Error during disease prediction: {e}")
            flash(
                f"An error occurred during prediction: {e}. Please try again with a valid image file."
            )
            return redirect(url_for("disease_page"))

    return redirect(url_for("disease_page"))


# ===============================================================================================
if __name__ == "__main__":
    # Use debug mode only if the environment variable DEBUG is set to '1' or 'true'
    debug_mode = os.environ.get("DEBUG", "False").lower() in ("1", "true", "yes")
    app.run(debug=debug_mode)
