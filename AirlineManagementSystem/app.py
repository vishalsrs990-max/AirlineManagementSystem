from flask import Flask, render_template, request, redirect, flash
from flask_pymongo import PyMongo

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Required for flashing messages

# MongoDB connection (local)
app.config["MONGO_URI"] = "mongodb://localhost:27017/airline_db"
mongo = PyMongo(app)

# Home route (optional)
@app.route('/')
def home():
    return redirect('/add')

# Route to display form and SQLite flights
@app.route('/add')
def add():
    # Dummy SQLite data for display (replace with actual DB query if needed)
    flights = [
        {"flightID": "AI101", "Origin": "London", "Destination": "Delhi", "Date": "2025-11-01", "Time": "10:00"},
        {"flightID": "AI102", "Origin": "Paris", "Destination": "Mumbai", "Date": "2025-11-02", "Time": "12:00"}
    ]
    return render_template('add_flight.html', flights=flights)

# Route to handle MongoDB flight submission
@app.route('/add_flight', methods=['POST'])
def add_flight():
    flight_id = request.form.get('flight_id')
    origin = request.form.get('origin')
    destination = request.form.get('destination')
    date = request.form.get('date')
    time = request.form.get('time')

    print("Form Data:", request.form)  # Debug log

    if not all([flight_id, origin, destination, date, time]):
        flash("❌ All fields are required.")
        return redirect('/add')

    flight = {
        "flight_id": flight_id,
        "origin": origin,
        "destination": destination,
        "date": date,
        "time": time
    }

    try:
        mongo.db.flights.insert_one(flight)
        flash("✅ Flight added successfully to MongoDB!")
    except Exception as e:
        print("MongoDB Error:", e)
        flash("❌ Failed to add flight. Check MongoDB connection.")

    return redirect('/add')

# Optional route to view MongoDB flights
@app.route('/flights')
def view_flights():
    flights = list(mongo.db.flights.find())
    return render_template('mongo_flights.html', flights=flights)

if __name__ == '__main__':
    app.run(debug=True)