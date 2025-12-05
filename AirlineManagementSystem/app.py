import os
import boto3

from flask import (
    Flask, render_template, request, redirect,
    flash, session, url_for
)
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, timezone

app = Flask(__name__)
app.config["DEBUG"] = True

# -------------------------------------------------------------------
# Secret key – never hard-code real secrets in source control
# -------------------------------------------------------------------
SECRET_KEY = os.environ.get("FLASK_SECRET_KEY")
if not SECRET_KEY:
    # Dev-only fallback so the app still runs on your laptop / EC2.
    # In production set FLASK_SECRET_KEY in the environment.
    SECRET_KEY = "dev-only-secret"
app.secret_key = SECRET_KEY

# -----------------------------
# MongoDB connection
# -----------------------------
client = MongoClient("mongodb://localhost:27017/")
db = client["flights_db"]

# Existing collection for flights (DO NOT CHANGE)
mongo_collection = db["flights"]

# New collections
users_collection = db["users"]
bookings_collection = db["bookings"]

# ------------------------------------------------
# AWS SNS client for booking notifications
# ------------------------------------------------
# Use environment variables instead of hard-coded region / topic ARN
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
SNS_TOPIC_ARN = os.environ.get(
    "SNS_TOPIC_ARN",
    "arn:aws:sns:us-east-1:533267158126:ams-bookings-topic",
)

sns_client = boto3.client("sns", region_name=AWS_REGION)


def notify_new_booking(booking: dict, flight: dict) -> None:
    """
    Publish a 'new booking' notification to SNS.
    All email subscribers to the topic will receive it.
    """
    subject = f"New booking for flight {flight['flightID']}"

    message_lines = [
        "A new booking has been created in Airline Management System.",
        "",
        f"Flight: {flight['flightID']}",
        f"Route: {flight['origin']} -> {flight['destination']}",
        f"Date: {flight['date']} at {flight['time']}",
        "",
        f"Passenger name: {booking['passenger']['full_name']}",
        f"Passenger email: {booking['passenger']['email']}",
        f"Phone: {booking['passenger']['phone']}",
        "",
        f"Passengers: {booking['num_passengers']}",
        f"Class: {booking['cabin_class']}",
        f"Status: {booking['status']}",
        "",
        "AMS – DevOps project notification via Amazon SNS.",
    ]
    message_text = "\n".join(message_lines)

    try:
        response = sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=subject,
            Message=message_text,
        )
        print("SNS publish OK, message ID:", response.get("MessageId"))
    except Exception as exc:  # noqa: BLE001
        # Do not crash the app if SNS fails – just log it.
        print("SNS publish error:", repr(exc))


# -----------------------------
# Helper: login_required decorator
# -----------------------------
def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login", next=request.url))
        return view_func(*args, **kwargs)

    return wrapper


# -----------------------------
# ROUTES
# -----------------------------
@app.route("/")
def home():
    """Blue landing page with plane images + navbar."""
    return render_template("index.html")


# Add flight (MongoDB)
@app.route("/add_mongo", methods=["GET", "POST"])
def add_mongo():
    if request.method == "POST":
        flightID = request.form["flightID"]
        origin = request.form["origin"]
        destination = request.form["destination"]
        date = request.form["date"]
        time = request.form["time"]

        # Simple validation
        if not all([flightID, origin, destination, date, time]):
            flash("❌ All fields are required.")
            return redirect(url_for("add_mongo"))

        # Insert into MongoDB
        mongo_collection.insert_one(
            {
                "flightID": flightID,
                "origin": origin,
                "destination": destination,
                "date": date,
                "time": time,
            }
        )

        flash("✅ Flight added successfully!")
        # use url_for instead of repeated "/flights_mongo" literal
        return redirect(url_for("flights_mongo"))

    return render_template("bookings/add_mongo.html")


# View all flights from MongoDB (admin list)
@app.route("/flights_mongo")
def flights_mongo():
    flights = list(mongo_collection.find())
    return render_template("bookings/flights_mongo.html", flights=flights)


# Delete a flight
@app.route("/delete/<flight_id>")
def delete_flight(flight_id):
    mongo_collection.delete_one({"flightID": flight_id})
    flash(f"🗑️ Flight {flight_id} deleted.")
    return redirect(url_for("flights_mongo"))


# Update a flight
@app.route("/update/<flight_id>", methods=["GET", "POST"])
def update_flight(flight_id):
    flight = mongo_collection.find_one({"flightID": flight_id})

    if request.method == "POST":
        updated_data = {
            "flightID": request.form["flightID"],
            "origin": request.form["origin"],
            "destination": request.form["destination"],
            "date": request.form["date"],
            "time": request.form["time"],
        }
        mongo_collection.update_one({"flightID": flight_id}, {"$set": updated_data})
        flash(f"✏️ Flight {flight_id} updated.")
        return redirect(url_for("flights_mongo"))

    return render_template("bookings/update_mongo.html", flight=flight)


# -----------------------------
# USER AUTHENTICATION
# -----------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        if users_collection.find_one({"email": email}):
            flash("Email already registered. Please log in.", "danger")
            return redirect(url_for("login"))

        user_doc = {
            "name": name,
            "email": email,
            "password_hash": generate_password_hash(password),
            "role": "user",
        }
        result = users_collection.insert_one(user_doc)

        session["user_id"] = str(result.inserted_id)
        session["user_name"] = name
        session["user_role"] = "user"

        flash("Registration successful!", "success")
        return redirect(url_for("home"))

    return render_template("bookings/register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        user = users_collection.find_one({"email": email})
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = str(user["_id"])
            session["user_name"] = user["name"]
            session["user_role"] = user.get("role", "user")

            flash("Logged in successfully.", "success")
            next_url = request.args.get("next")

            # 🔒 Validate "next" to avoid open redirects
            if not next_url or not next_url.startswith("/"):
                next_url = url_for("home")

            return redirect(next_url)
        flash("Invalid email or password.", "danger")

    return render_template("bookings/login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))


# -----------------------------
# USER VIEW OF FLIGHTS
# -----------------------------
@app.route("/user/flights")
@login_required
def user_flights():
    """Flights list for normal users with Book button."""
    flights = list(mongo_collection.find())
    return render_template("bookings/flights_user.html", flights=flights)


# -----------------------------
# BOOKINGS (CRUD)
# -----------------------------
@app.route("/book/<flight_id>", methods=["GET", "POST"])
@login_required
def book_flight(flight_id):
    """Create a booking for the current user."""
    flight = mongo_collection.find_one({"flightID": flight_id})
    if not flight:
        flash("Flight not found.", "danger")
        return redirect(url_for("user_flights"))

    if request.method == "POST":
        full_name = request.form["full_name"].strip()
        email = request.form["email"].strip()
        phone = request.form["phone"].strip()
        num_passengers = int(request.form["num_passengers"])
        cabin_class = request.form["cabin_class"]

        travel_date = flight.get("date")

        booking_doc = {
            "user_id": ObjectId(session["user_id"]),
            "flightID": flight["flightID"],
            "travel_date": travel_date,
            "num_passengers": num_passengers,
            "cabin_class": cabin_class,
            "passenger": {
                "full_name": full_name,
                "email": email,
                "phone": phone,
            },
            "status": "CONFIRMED",
            # Use timezone-aware timestamp instead of datetime.utcnow()
            "created_at": datetime.now(timezone.utc),
        }

        result = bookings_collection.insert_one(booking_doc)
        booking_doc["_id"] = result.inserted_id

        notify_new_booking(booking_doc, flight)

        flash("Booking created successfully! Notification sent via SNS.", "success")
        return redirect(url_for("my_bookings"))

    return render_template("bookings/book_form.html", flight=flight)


@app.route("/my-bookings")
@login_required
def my_bookings():
    """List bookings for the logged-in user."""
    user_id = ObjectId(session["user_id"])
    bookings = list(bookings_collection.find({"user_id": user_id}))

    booking_details = []
    for booking in bookings:
        flight = mongo_collection.find_one({"flightID": booking["flightID"]})
        booking_details.append({"booking": booking, "flight": flight})

    return render_template("bookings/list.html", booking_details=booking_details)


@app.route("/booking/<booking_id>/edit", methods=["GET", "POST"])
@login_required
def edit_booking(booking_id):
    """Edit an existing booking."""
    booking = bookings_collection.find_one(
        {"_id": ObjectId(booking_id), "user_id": ObjectId(session["user_id"])}
    )
    if not booking:
        flash("Booking not found.", "danger")
        return redirect(url_for("my_bookings"))

    if request.method == "POST":
        num_passengers = int(request.form["num_passengers"])
        travel_date = request.form["travel_date"]
        cabin_class = request.form["cabin_class"]

        bookings_collection.update_one(
            {"_id": booking["_id"]},
            {
                "$set": {
                    "num_passengers": num_passengers,
                    "travel_date": travel_date,
                    "cabin_class": cabin_class,
                }
            },
        )
        flash("Booking updated.", "success")
        return redirect(url_for("my_bookings"))

    return render_template("bookings/edit.html", booking=booking)


@app.route("/booking/<booking_id>/cancel", methods=["POST"])
@login_required
def cancel_booking(booking_id):
    """Delete a booking document completely."""
    bookings_collection.delete_one(
        {"_id": ObjectId(booking_id), "user_id": ObjectId(session["user_id"])}
    )
    flash("Booking deleted.", "info")
    return redirect(url_for("my_bookings"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
