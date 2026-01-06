# app.py

# Importing essential libraries and modules
import io
import logging
import os
import pickle
import uuid

import config  # Assuming config.py holds your weather_api_key
import numpy as np
import pandas as pd
import requests
import torch
from flask import Flask, flash, redirect, render_template, request, url_for, session
from flask_migrate import Migrate
from markupsafe import Markup
from PIL import Image
from torchvision import transforms

# --- CHANGE: Import custom modules more cleanly
from utils.disease import disease_dic
from utils.fertilizer import fertilizer_dic
from utils.model import ResNet9
from models import db, CropPrediction, FertilizerPrediction, DiseasePrediction

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

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///farmiq.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)
migrate = Migrate(app, db)

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


def get_or_create_session_id():
    """
    Get or create a unique session ID for the user.
    """
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    return session['user_id']


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

            # Save prediction to database
            try:
                session_id = get_or_create_session_id()
                crop_pred = CropPrediction(
                    user_session=session_id,
                    nitrogen=N,
                    phosphorus=P,
                    potassium=K,
                    temperature=temperature,
                    humidity=humidity,
                    ph=ph,
                    rainfall=rainfall,
                    city=city,
                    predicted_crop=final_prediction
                )
                db.session.add(crop_pred)
                db.session.commit()
                logging.info(f"✅ Crop prediction saved for session {session_id}")
            except Exception as e:
                logging.error(f"❌ Error saving crop prediction: {e}")
                db.session.rollback()

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

        # Save prediction to database
        try:
            session_id = get_or_create_session_id()
            fert_pred = FertilizerPrediction(
                user_session=session_id,
                crop_name=crop_name,
                nitrogen=N,
                phosphorus=P,
                potassium=K,
                recommendation_key=key
            )
            db.session.add(fert_pred)
            db.session.commit()
            logging.info(f"✅ Fertilizer prediction saved for session {session_id}")
        except Exception as e:
            logging.error(f"❌ Error saving fertilizer prediction: {e}")
            db.session.rollback()

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

            # Save prediction to database
            try:
                session_id = get_or_create_session_id()
                disease_pred = DiseasePrediction(
                    user_session=session_id,
                    image_filename=file.filename,
                    predicted_disease=prediction_class,
                    confidence=confidence
                )
                db.session.add(disease_pred)
                db.session.commit()
                logging.info(f"✅ Disease prediction saved for session {session_id}")
            except Exception as e:
                logging.error(f"❌ Error saving disease prediction: {e}")
                db.session.rollback()

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
# ------------------------------------ DASHBOARD & HISTORY ROUTES -------------------------------
# ===============================================================================================


@app.route("/dashboard")
def dashboard():
    """Display user dashboard with prediction history and statistics"""
    title = "FarmIQ - Dashboard"
    session_id = get_or_create_session_id()

    try:
        # Get recent predictions
        crop_predictions = CropPrediction.query.filter_by(
            user_session=session_id
        ).order_by(CropPrediction.timestamp.desc()).limit(10).all()

        fertilizer_predictions = FertilizerPrediction.query.filter_by(
            user_session=session_id
        ).order_by(FertilizerPrediction.timestamp.desc()).limit(10).all()

        disease_predictions = DiseasePrediction.query.filter_by(
            user_session=session_id
        ).order_by(DiseasePrediction.timestamp.desc()).limit(10).all()

        # Calculate statistics
        total_crops = CropPrediction.query.filter_by(user_session=session_id).count()
        total_fertilizers = FertilizerPrediction.query.filter_by(user_session=session_id).count()
        total_diseases = DiseasePrediction.query.filter_by(user_session=session_id).count()

        # Calculate average nutrient levels for crop predictions
        avg_nitrogen = db.session.query(db.func.avg(CropPrediction.nitrogen)).filter_by(
            user_session=session_id
        ).scalar() or 0

        avg_phosphorus = db.session.query(db.func.avg(CropPrediction.phosphorus)).filter_by(
            user_session=session_id
        ).scalar() or 0

        avg_potassium = db.session.query(db.func.avg(CropPrediction.potassium)).filter_by(
            user_session=session_id
        ).scalar() or 0

        # Get most common crop recommendations
        from sqlalchemy import func
        common_crops = db.session.query(
            CropPrediction.predicted_crop,
            func.count(CropPrediction.predicted_crop).label('count')
        ).filter_by(user_session=session_id).group_by(
            CropPrediction.predicted_crop
        ).order_by(func.count(CropPrediction.predicted_crop).desc()).limit(5).all()

        # Get most common diseases
        common_diseases = db.session.query(
            DiseasePrediction.predicted_disease,
            func.count(DiseasePrediction.predicted_disease).label('count')
        ).filter_by(user_session=session_id).group_by(
            DiseasePrediction.predicted_disease
        ).order_by(func.count(DiseasePrediction.predicted_disease).desc()).limit(5).all()

        stats = {
            'total_crops': total_crops,
            'total_fertilizers': total_fertilizers,
            'total_diseases': total_diseases,
            'total_predictions': total_crops + total_fertilizers + total_diseases,
            'avg_nitrogen': round(avg_nitrogen, 2),
            'avg_phosphorus': round(avg_phosphorus, 2),
            'avg_potassium': round(avg_potassium, 2),
            'common_crops': common_crops,
            'common_diseases': common_diseases
        }

        return render_template(
            'dashboard.html',
            title=title,
            crop_predictions=crop_predictions,
            fertilizer_predictions=fertilizer_predictions,
            disease_predictions=disease_predictions,
            stats=stats
        )

    except Exception as e:
        logging.error(f"Error loading dashboard: {e}")
        flash("❌ Error loading dashboard data.")
        return redirect(url_for("home"))


@app.route("/history/crops")
def crop_history():
    """Display crop prediction history with pagination"""
    title = "FarmIQ - Crop History"
    session_id = get_or_create_session_id()
    page = request.args.get('page', 1, type=int)
    per_page = 10

    try:
        pagination = CropPrediction.query.filter_by(
            user_session=session_id
        ).order_by(CropPrediction.timestamp.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return render_template(
            'crop_history.html',
            title=title,
            predictions=pagination.items,
            pagination=pagination
        )
    except Exception as e:
        logging.error(f"Error loading crop history: {e}")
        flash("❌ Error loading crop history.")
        return redirect(url_for("dashboard"))


@app.route("/history/fertilizers")
def fertilizer_history():
    """Display fertilizer prediction history with pagination"""
    title = "FarmIQ - Fertilizer History"
    session_id = get_or_create_session_id()
    page = request.args.get('page', 1, type=int)
    per_page = 10

    try:
        pagination = FertilizerPrediction.query.filter_by(
            user_session=session_id
        ).order_by(FertilizerPrediction.timestamp.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return render_template(
            'fertilizer_history.html',
            title=title,
            predictions=pagination.items,
            pagination=pagination
        )
    except Exception as e:
        logging.error(f"Error loading fertilizer history: {e}")
        flash("❌ Error loading fertilizer history.")
        return redirect(url_for("dashboard"))


@app.route("/history/diseases")
def disease_history():
    """Display disease prediction history with pagination"""
    title = "FarmIQ - Disease History"
    session_id = get_or_create_session_id()
    page = request.args.get('page', 1, type=int)
    per_page = 10

    try:
        pagination = DiseasePrediction.query.filter_by(
            user_session=session_id
        ).order_by(DiseasePrediction.timestamp.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return render_template(
            'disease_history.html',
            title=title,
            predictions=pagination.items,
            pagination=pagination
        )
    except Exception as e:
        logging.error(f"Error loading disease history: {e}")
        flash("❌ Error loading disease history.")
        return redirect(url_for("dashboard"))


@app.route("/export/csv")
def export_csv():
    """Export all prediction history as CSV"""
    from flask import make_response
    import csv
    from io import StringIO

    session_id = get_or_create_session_id()

    try:
        # Create CSV in memory
        si = StringIO()
        writer = csv.writer(si)

        # Write crop predictions
        writer.writerow(['=== CROP PREDICTIONS ==='])
        writer.writerow(['ID', 'Timestamp', 'Nitrogen', 'Phosphorus', 'Potassium', 'Temperature', 'Humidity', 'pH', 'Rainfall', 'City', 'Predicted Crop'])
        crop_preds = CropPrediction.query.filter_by(user_session=session_id).order_by(CropPrediction.timestamp.desc()).all()
        for pred in crop_preds:
            writer.writerow([
                pred.id, pred.timestamp, pred.nitrogen, pred.phosphorus, pred.potassium,
                pred.temperature, pred.humidity, pred.ph, pred.rainfall, pred.city, pred.predicted_crop
            ])

        writer.writerow([])  # Empty row
        
        # Write fertilizer predictions
        writer.writerow(['=== FERTILIZER PREDICTIONS ==='])
        writer.writerow(['ID', 'Timestamp', 'Crop Name', 'Nitrogen', 'Phosphorus', 'Potassium', 'Recommendation'])
        fert_preds = FertilizerPrediction.query.filter_by(user_session=session_id).order_by(FertilizerPrediction.timestamp.desc()).all()
        for pred in fert_preds:
            writer.writerow([
                pred.id, pred.timestamp, pred.crop_name, pred.nitrogen, pred.phosphorus, pred.potassium, pred.recommendation_key
            ])

        writer.writerow([])  # Empty row
        
        # Write disease predictions
        writer.writerow(['=== DISEASE PREDICTIONS ==='])
        writer.writerow(['ID', 'Timestamp', 'Image Filename', 'Predicted Disease', 'Confidence (%)'])
        disease_preds = DiseasePrediction.query.filter_by(user_session=session_id).order_by(DiseasePrediction.timestamp.desc()).all()
        for pred in disease_preds:
            writer.writerow([
                pred.id, pred.timestamp, pred.image_filename, pred.predicted_disease, pred.confidence
            ])

        # Create response
        output = make_response(si.getvalue())
        output.headers["Content-Disposition"] = "attachment; filename=farmiq_predictions.csv"
        output.headers["Content-type"] = "text/csv"
        return output

    except Exception as e:
        logging.error(f"Error exporting CSV: {e}")
        flash("❌ Error exporting data to CSV.")
        return redirect(url_for("dashboard"))


@app.route("/export/pdf")
def export_pdf():
    """Export prediction history as PDF report"""
    from flask import make_response
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from io import BytesIO
    from datetime import datetime

    session_id = get_or_create_session_id()

    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()

        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2E7D32'),
            spaceAfter=30,
            alignment=1  # Center
        )
        elements.append(Paragraph("FarmIQ Prediction Report", title_style))
        elements.append(Spacer(1, 0.2*inch))

        # Report info
        elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        elements.append(Paragraph(f"Session ID: {session_id[:8]}...", styles['Normal']))
        elements.append(Spacer(1, 0.3*inch))

        # Statistics
        total_crops = CropPrediction.query.filter_by(user_session=session_id).count()
        total_fertilizers = FertilizerPrediction.query.filter_by(user_session=session_id).count()
        total_diseases = DiseasePrediction.query.filter_by(user_session=session_id).count()

        elements.append(Paragraph("Summary Statistics", styles['Heading2']))
        stats_data = [
            ['Total Predictions', str(total_crops + total_fertilizers + total_diseases)],
            ['Crop Recommendations', str(total_crops)],
            ['Fertilizer Suggestions', str(total_fertilizers)],
            ['Disease Detections', str(total_diseases)]
        ]
        stats_table = Table(stats_data, colWidths=[3*inch, 2*inch])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(stats_table)
        elements.append(Spacer(1, 0.5*inch))

        # Recent Crop Predictions
        if total_crops > 0:
            elements.append(Paragraph("Recent Crop Recommendations", styles['Heading2']))
            crop_preds = CropPrediction.query.filter_by(user_session=session_id).order_by(
                CropPrediction.timestamp.desc()
            ).limit(5).all()
            crop_data = [['Date', 'Crop', 'N-P-K', 'City']]
            for pred in crop_preds:
                crop_data.append([
                    pred.timestamp.strftime('%Y-%m-%d'),
                    pred.predicted_crop,
                    f"{pred.nitrogen}-{pred.phosphorus}-{pred.potassium}",
                    pred.city or 'N/A'
                ])
            crop_table = Table(crop_data, colWidths=[1.5*inch, 2*inch, 1.5*inch, 1.5*inch])
            crop_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(crop_table)
            elements.append(Spacer(1, 0.3*inch))

        # Recent Disease Predictions
        if total_diseases > 0:
            elements.append(Paragraph("Recent Disease Detections", styles['Heading2']))
            disease_preds = DiseasePrediction.query.filter_by(user_session=session_id).order_by(
                DiseasePrediction.timestamp.desc()
            ).limit(5).all()
            disease_data = [['Date', 'Disease', 'Confidence']]
            for pred in disease_preds:
                disease_data.append([
                    pred.timestamp.strftime('%Y-%m-%d'),
                    pred.predicted_disease[:30],
                    f"{pred.confidence:.1f}%"
                ])
            disease_table = Table(disease_data, colWidths=[1.5*inch, 3.5*inch, 1.5*inch])
            disease_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(disease_table)

        # Build PDF
        doc.build(elements)
        pdf_data = buffer.getvalue()
        buffer.close()

        response = make_response(pdf_data)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'attachment; filename=farmiq_report.pdf'
        return response

    except Exception as e:
        logging.error(f"Error generating PDF: {e}")
        flash("❌ Error generating PDF report.")
        return redirect(url_for("dashboard"))


# ===============================================================================================
if __name__ == "__main__":
    # Create database tables if they don't exist
    with app.app_context():
        db.create_all()
        logging.info("✅ Database tables created/verified.")
    
    # Use debug mode only if the environment variable DEBUG is set to '1' or 'true'
    debug_mode = os.environ.get("DEBUG", "False").lower() in ("1", "true", "yes")
    app.run(debug=debug_mode)
