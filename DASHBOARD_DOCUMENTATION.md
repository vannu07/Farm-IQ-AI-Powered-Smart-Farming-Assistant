# User Dashboard Feature Documentation

## Overview

The FarmIQ User Dashboard feature transforms the application from a stateless prediction tool into an intelligent farming companion that tracks prediction history, provides analytics, and helps farmers make better long-term agricultural decisions.

## Features Implemented

### 1. Database Integration ✅

- **SQLAlchemy & SQLite** for data persistence
- **Three Database Models:**
  - `CropPrediction`: Stores crop recommendations with N-P-K values, weather data, timestamps
  - `FertilizerPrediction`: Logs soil nutrient levels, crop types, and recommendations
  - `DiseasePrediction`: Stores disease detection results with confidence scores

### 2. Session Management ✅

- UUID-based session tracking for users
- Automatic session ID generation stored in browser cookies
- No authentication required - lightweight session tracking

### 3. Interactive Dashboard ✅

**Route:** `/dashboard`

**Features:**
- Summary statistics cards showing:
  - Total predictions across all categories
  - Crop recommendations count
  - Fertilizer suggestions count
  - Disease detections count
- Visual charts using Chart.js:
  - Bar chart: Average soil nutrient levels (N, P, K)
  - Pie chart: Distribution of most recommended crops
  - Horizontal bar chart: Disease detection frequency
- Recent predictions display (last 5 from each category)
- Export buttons for CSV and PDF reports

### 4. Prediction History Pages ✅

**Routes:**
- `/history/crops` - Crop recommendation history
- `/history/fertilizers` - Fertilizer suggestion history
- `/history/diseases` - Disease detection history

**Features:**
- Paginated lists (10 items per page)
- Detailed view of past predictions with all parameters
- Timestamps and organized data display
- "Back to Dashboard" navigation
- Empty state messages with call-to-action buttons

### 5. Export & Download Features ✅

**CSV Export** (`/export/csv`)
- Downloads complete prediction history as CSV
- Organized by prediction type
- Includes all data fields with proper headers

**PDF Report** (`/export/pdf`)
- Generates formatted PDF reports using ReportLab
- Includes:
  - Summary statistics
  - Recent predictions in tables
  - Professional formatting with colors
  - Date and session information

### 6. Enhanced UI/UX ✅

- Dashboard link in navigation bar
- "View History" buttons on all result pages
- Responsive card-based layouts
- Gradient colored statistic cards
- Smooth animations and hover effects
- Consistent design following existing patterns

## Technical Implementation

### Database Schema

```python
# Crop Predictions Table
- id (Integer, Primary Key)
- user_session (String, Indexed)
- timestamp (DateTime)
- nitrogen, phosphorus, potassium (Integer)
- temperature, humidity, ph, rainfall (Float)
- city (String)
- predicted_crop (String)

# Fertilizer Predictions Table
- id (Integer, Primary Key)
- user_session (String, Indexed)
- timestamp (DateTime)
- crop_name (String)
- nitrogen, phosphorus, potassium (Integer)
- recommendation_key (String)

# Disease Predictions Table
- id (Integer, Primary Key)
- user_session (String, Indexed)
- timestamp (DateTime)
- image_filename (String)
- predicted_disease (String)
- confidence (Float)
```

### Key Functions

```python
# Session Management
get_or_create_session_id() - Creates or retrieves user session ID

# Dashboard Route
@app.route("/dashboard") - Main dashboard with stats and charts

# History Routes
@app.route("/history/crops") - Paginated crop history
@app.route("/history/fertilizers") - Paginated fertilizer history
@app.route("/history/diseases") - Paginated disease history

# Export Routes
@app.route("/export/csv") - CSV export of all predictions
@app.route("/export/pdf") - PDF report generation
```

## Installation & Setup

### 1. Install Dependencies

```bash
pip install flask-sqlalchemy flask-migrate plotly reportlab python-dotenv
```

Or install from requirements.txt:

```bash
pip install -r requirements.txt
```

### 2. Initialize Database

The database is automatically initialized when you first run the application:

```bash
cd app
python app.py
```

Alternatively, use the initialization script:

```bash
python init_db.py
```

### 3. Database Configuration

By default, the application uses SQLite with the database file located at:
```
app/farmiq.db
```

You can customize the database location by setting the `DATABASE_URL` environment variable:

```bash
export DATABASE_URL="sqlite:///path/to/your/database.db"
```

For production, you can use PostgreSQL or MySQL:

```bash
export DATABASE_URL="postgresql://user:password@localhost/farmiq"
```

## Usage

### Accessing the Dashboard

1. Navigate to any FarmIQ page
2. Click on "Dashboard" in the navigation bar
3. View your prediction statistics and history

### Making Predictions

1. Use any of the three prediction services:
   - Crop Recommendation
   - Fertilizer Suggestion
   - Disease Detection
2. Predictions are automatically saved to your session
3. View results and access history from result pages

### Viewing History

From the dashboard:
- Click "View All" on any prediction category
- Or use the navigation buttons on result pages

### Exporting Data

From the dashboard:
- Click "Export to CSV" for spreadsheet format
- Click "Generate PDF Report" for formatted report

## Screenshots

### Dashboard (Empty State)
![Dashboard Empty](https://github.com/user-attachments/assets/93d56599-1732-43c1-9143-2f8048704c26)

### Crop History Page
![Crop History](https://github.com/user-attachments/assets/b1bf2857-a6e7-4036-8529-f12057f88dca)

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/dashboard` | GET | Main dashboard with statistics |
| `/history/crops` | GET | Paginated crop prediction history |
| `/history/fertilizers` | GET | Paginated fertilizer prediction history |
| `/history/diseases` | GET | Paginated disease prediction history |
| `/export/csv` | GET | Download predictions as CSV |
| `/export/pdf` | GET | Generate PDF report |

## Database Management

### Viewing Database Content

```python
from app import app, db
from models import CropPrediction, FertilizerPrediction, DiseasePrediction

with app.app_context():
    # Get all crop predictions
    crops = CropPrediction.query.all()
    for crop in crops:
        print(crop.predicted_crop)
    
    # Get predictions for specific session
    session_crops = CropPrediction.query.filter_by(
        user_session='your-session-id'
    ).all()
```

### Clearing History

To clear all prediction history:

```python
with app.app_context():
    db.drop_all()
    db.create_all()
```

## Security Considerations

1. **Session IDs**: Currently stored in cookies without authentication
2. **Data Privacy**: Each session only sees their own data
3. **Input Validation**: All form inputs are validated before database storage
4. **Error Handling**: Database errors are logged and gracefully handled

## Future Enhancements

Potential improvements for future versions:

1. User authentication with login/signup
2. Email notifications for predictions
3. Weather-based alerts and reminders
4. Seasonal planting recommendations
5. Data visualization improvements
6. Comparison between different predictions
7. Export to more formats (Excel, JSON)
8. Mobile app integration
9. Multi-language support
10. Advanced filtering and search in history

## Troubleshooting

### Database Issues

**Problem:** Database file not found
```bash
# Solution: Run initialization script
python init_db.py
```

**Problem:** Database locked
```bash
# Solution: Close all connections and restart the app
kill <flask_pid>
python app.py
```

### Import Errors

**Problem:** Module not found
```bash
# Solution: Install missing dependencies
pip install -r requirements.txt
```

## Contributing

When contributing to the dashboard feature:

1. Test all database operations
2. Ensure backward compatibility
3. Update this documentation
4. Add appropriate error handling
5. Follow existing code style
6. Test with different data volumes

## License

This feature is part of FarmIQ and follows the same license as the main project.

## Support

For issues or questions:
- Open an issue on GitHub
- Check existing documentation
- Review the code comments

---

**Version:** 1.0.0  
**Last Updated:** January 2026  
**Author:** FarmIQ Development Team
