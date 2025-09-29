from datetime import datetime, timezone
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.wrappers.request import Request
from pydantic import ValidationError
from models import SurveySubmission, StoredSurveyRecord
from storage import append_json_line
import hashlib

app = Flask(__name__)
# Allow cross-origin requests so the static HTML can POST from localhost or file://
CORS(app, resources={r"/v1/*": {"origins": "*"}})

@app.route("/ping", methods=["GET"])
def ping():
    """Simple health check endpoint."""
    return jsonify({
        "status": "ok",
        "message": "API is alive",
        "utc_time": datetime.now(timezone.utc).isoformat()
    })

def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

@app.post("/v1/survey")
def submit_survey():
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "invalid_json", "detail": "Body must be application/json"}), 400

    if not payload.get("submission_id"):
        now = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
        payload["submission_id"] = payload["email"] + now

    try:
        submission = SurveySubmission(**payload)
    except ValidationError as ve:
        return jsonify({"error": "validation_error", "detail": ve.errors()}), 422

    # added code
    record_dict = submission.dict()
    record_dict["email"] = sha256(record_dict["email"])
    record_dict["age"] = sha256(str(record_dict["age"]))

    record = StoredSurveyRecord(
        name=submission.name,
        email=sha256(submission.email),  # Hash the email
        age=sha256(str(submission.age)),  # Hash the age
        consent=submission.consent,
        rating=submission.rating,
        comments=submission.comments,
        user_agent=submission.user_agent,
        submission_id=submission.submission_id,
        source=submission.source,
        received_at=datetime.now(timezone.utc),
        ip=request.headers.get("X-Forwarded-For", request.remote_addr or "")
    )
    
    append_json_line(record.dict())
    return jsonify({"status": "ok"}), 201

if __name__ == "__main__":
    app.run(port=5000, debug=True)
