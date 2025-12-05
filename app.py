"""
Entry point for EC2 / deployment.

We reuse the real Flask application defined in
AirlineManagementSystem/app.py so we avoid code duplication.
"""

from AirlineManagementSystem.app import app  # import the real app object


if __name__ == "__main__":
    # For local testing if you ever run `python app.py`
    app.run(host="0.0.0.0", port=5000, debug=False)
