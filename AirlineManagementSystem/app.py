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

# ------------------------------------------------
# Flask setup
# ------------------------------------------------
app = Flask(__name__)
app.config["DEBUG"] = True

# Secret key: read from environment in production.
# No hard-coded secret in source code (fixes Sonar "don't disclose Flask keys").
secret_key = os.environ.get("FLASK_SECRET_KEY")
if not secret_key:
    # Dev-only fallback – generates a random key every time.
    # This is OK for local testing, but in production you MUST set FLASK_SECRET_KEY.
    secret_key = os.urandom(32)
app.secret_key = secret_key

# ------------------------------------------------
# MongoDB connection
# ------------------------------------------------
client = MongoClient("mongodb://localhost:27017/")
db = client["flights_db"]

# Existing collection for flights (DO NOT CHANGE COLLECTION NAME)
mongo_collection = db["flights"]

# New collections
users_collection = db["users"]
bookings_collection = db["bookings"]

# ------------------------------------------------
# Constants for routes (remove duplicated string literals)
# ------------------------------------------------
FLIGHTS_MONGO_ROUTE = "/flights_mongo"

# ------------------------------------------------
# AWS SNS client for booking notifications
# ------------------------------------------------
# Region and credentials come from environment / instance metadata.
# We do NOT hard-code the region string here (fixes Sonar hardcoded region).
sns_client = boto3.client("sns")

# Topic ARN is read from env if available, otherwise falls back to your current topic.
SNS_TOPIC_ARN = os.environ.get(
    "SNS_TOPIC_ARN",
    "arn:aws:sns:us-east-1:533267158126:ams-bookings-topic",
)


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
    except Exception as exc:  # pragma: no cover - log only
        # Don't crash the app if SNS fails – just log it.
        print("SNS publish error:", repr(exc))


# ------------------------------------------------
# Helper: login_required decorator
# ------------------------------------------------
def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login", next=request.url))
        return view_func(*args, **kwargs)

    return wrapper


# ------------------------------------------------
# ROUTES – homepage
# ------------------------------------------------
@app.route("/")
def home():
    # BLUE landing page with plane images + navbar
    return render_template("index.html")


# ------------------------------------------------
# Flights – Admin CRUD
# ------------------------------------------------
@app.route("/add_mongo", methods=["GET", "POST"])
def add_mongo():
    """
    Admin: add a flight into the MongoDB 'flights' collection.
    """
    if request.method == "POST":
        # local variable renamed to snake_case for Sonar rule
        flight_id = request.form["flightID"]
        origin = request.form["origin"]
        destination = request.form["destination"]
        date = request.form["date"]
        time = request.form["time"]

        # Simple validation
        if not flight_id or not origin or not destination or not date or not time:
            flash("❌ All fields are required.")
            return redirect("/add_mongo")

        # Insert into MongoDB – keep DB field name 'flightID' unchanged
        mongo_collection.insert_one(
            {
                "flightID": flight_id,
                "origin": origin,
                "destination": destination,
                "date": date,
                "time": time,
            }
        )

        flash("✅ Flight added successfully!")
        return redirect(FLIGHTS_MONGO_ROUTE)

    return render_template("bookings/add_mongo.html")


@app.route(FLIGHTS_MONGO_ROUTE)
def flights_mongo():
    """
    Admin: list all flights from MongoDB.
    """
    flights = list(mongo_collection.find())
    return render_template("bookings/flights_mongo.html", flights=flights)


@app.route("/delete/<flight_id>")
def delete_flight(flight_id):
    """
    Admin: delete a flight by flightID.
    """
    mongo_collection.delete_one({"flightID": flight_id})
    flash(f"🗑️ Flight {flight_id} deleted.")
    return redirect(FLIGHTS_MONGO_ROUTE)


@app.route("/update/<flight_id>", methods=["GET", "POST"])
def update_flight(flight_id):
    """
    Admin: update a flight document.
    """
    flight = mongo_collection.find_one({"flightID": flight_id})

    if request.method == "POST":
        updated_data = {
            # again, local variable is not named flightID – only the DB field is
            "flightID": request.form["flightID"],
            "origin": request.form["origin"],
            "destination": request.form["destination"],
            "date": request.form["date"],
            "time": request.form["time"],
        }
        mongo_collection.update_one({"flightID": flight_id}, {"$set": updated_data})
        flash(f"✏️ Flight {flight_id} updated.")
        return redirect(FLIGHTS_MONGO_ROUTE)

    return render_template("bookings/update_mongo.html", flight=flight)


# ------------------------------------------------
# USER AUTHENTICATION
# ------------------------------------------------
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


def _is_safe_next_url(next_url: str) -> bool:
    """
    Very small helper to ensure we don't open redirect vulnerabilities.
    Only allow relative URLs inside this app.
    """
    if not next_url:
        return False
    return next_url.startswith("/") and not next_url.startswith("//")


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
            if _is_safe_next_url(next_url):
                return redirect(next_url)
            return redirect(url_for("home"))

        flash("Invalid email or password.", "danger")

    return render_template("bookings/login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))


# ------------------------------------------------
# USER VIEW OF FLIGHTS
# ------------------------------------------------
@app.route("/user/flights")
@login_required
def user_flights():
    """Flights list for normal users with Book button."""
    flights = list(mongo_collection.find())
    return render_template("bookings/flights_user.html", flights=flights)


# ------------------------------------------------
# BOOKINGS (CRUD)
# ------------------------------------------------
@app.route("/book/<flight_id>", methods=["GET", "POST"])
@login_required
def book_flight(flight_id):
    """
    Create a booking for the given flight.
    """
    flight = mongo_collection.find_one({"flightID": flight_id})
    if not flight:
        flash("Flight not found.", "danger")
        return redirect(url_for("user_flights"))

    if request.method == "POST":
        full_name = request.form["full_name"].strip()
        email = request.form["email"].strip()
        phone = request.form["phone"].strip()
        num_passengers = int(request.form["num_passengers"])
        cabin_class = request.form["cabin_class"]  # Economy / Premium / Business

        # Use the flight's date as travel_date (no separate input)
        travel_date = flight.get("date")

        booking_doc = {
            "user_id": ObjectId(session["user_id"]),
            "flightID": flight["flightID"],  # keep same key as in flights
            "travel_date": travel_date,
            "num_passengers": num_passengers,
            "cabin_class": cabin_class,
            "passenger": {
                "full_name": full_name,
                "email": email,
                "phone": phone,
            },
            "status": "CONFIRMED",
            # use timezone-aware datetime instead of datetime.utcnow()
            # (fixes Sonar datetime pitfall rule)
            "created_at": datetime.now(timezone.utc),
        }

        # Insert into MongoDB
        result = bookings_collection.insert_one(booking_doc)
        booking_doc["_id"] = result.inserted_id  # convenience only

        # 🔔 Send SNS notification
        notify_new_booking(booking_doc, flight)

        flash("Booking created successfully! Notification sent via SNS.", "success")
        return redirect(url_for("my_bookings"))

    return render_template("bookings/book_form.html", flight=flight)


@app.route("/my-bookings")
@login_required
def my_bookings():
    """
    Show bookings for the logged-in user.
    """
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
    """
    Edit an existing booking.
    """
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
    """
    Delete booking document completely.
    """
    bookings_collection.delete_one(
        {"_id": ObjectId(booking_id), "user_id": ObjectId(session["user_id"])}
    )
    flash("Booking deleted.", "info")
    return redirect(url_for("my_bookings"))


# ------------------------------------------------
# MAIN
# ------------------------------------------------
if __name__ == "__main__":
    # For local dev only – on EC2 / gunicorn you won't use this.
    app.run(host="0.0.0.0", port=5000, debug=True)
