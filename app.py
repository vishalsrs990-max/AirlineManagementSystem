from flask import Flask, render_template, request, redirect, flash
from pymongo import MongoClient

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Replace with any random string

# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client['flights_db']
mongo_collection = db['flights']

# Homepage
@app.route('/')
def home():
    return render_template('index.html')

# Add flight
@app.route('/add_mongo', methods=['GET', 'POST'])
def add_mongo():
    if request.method == 'POST':
        flightID = request.form['flightID']
        origin = request.form['origin']
        destination = request.form['destination']
        date = request.form['date']
        time = request.form['time']

        if not flightID or not origin or not destination or not date or not time:
            flash("❌ All fields are required.")
            return redirect('/add_mongo')

        mongo_collection.insert_one({
            'flightID': flightID,
            'origin': origin,
            'destination': destination,
            'date': date,
            'time': time
        })

        flash("✅ Flight added successfully!")
        return redirect('/flights_mongo')
    return render_template('add_mongo.html')

# View flights
@app.route('/flights_mongo')
def flights_mongo():
    flights = list(mongo_collection.find())
    return render_template('flights_mongo.html', flights=flights)

# Delete flight
@app.route('/delete/<flight_id>')
def delete_flight(flight_id):
    mongo_collection.delete_one({'flightID': flight_id})
    flash(f"🗑️ Flight {flight_id} deleted.")
    return redirect('/flights_mongo')

# Update flight
@app.route('/update/<flight_id>', methods=['GET', 'POST'])
def update_flight(flight_id):
    flight = mongo_collection.find_one({'flightID': flight_id})
    if request.method == 'POST':
        updated_data = {
            'flightID': request.form['flightID'],
            'origin': request.form['origin'],
            'destination': request.form['destination'],
            'date': request.form['date'],
            'time': request.form['time']
        }
        mongo_collection.update_one({'flightID': flight_id}, {'$set': updated_data})
        flash(f"✏️ Flight {flight_id} updated.")
        return redirect('/flights_mongo')
    return render_template('update_mongo.html', flight=flight)

if __name__ == '__main__':
    app.run(debug=True)