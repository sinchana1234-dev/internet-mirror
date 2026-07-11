from flask import Flask, request, jsonify
from flask_cors import CORS
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import random

app = Flask(__name__)
CORS(app)

analyzer = SentimentIntensityAnalyzer()

# ---- Auto-response templates ----
POSITIVE_RESPONSES = [
    "Thank you so much for the kind words! We're thrilled you had a great experience — hope to see you again soon. 🙌",
    "This made our day! Thanks for taking the time to share your feedback. 😊",
    "We really appreciate you! Glad we could deliver a great experience for you.",
]

NEGATIVE_RESPONSES_BY_CATEGORY = {
    "shipping": [
        "We're sorry your order didn't arrive on time. We're working with our shipping partners to fix this — please reach out with your order number so we can track it down.",
        "Apologies for the delivery delay. This isn't the experience we want for you — let's get this sorted, please DM your order details.",
    ],
    "quality": [
        "We're sorry the product didn't meet your quality expectations. We'd love to make this right — please reach out for a replacement or refund.",
        "Thank you for letting us know about this quality issue. We're looking into it and want to fix this for you directly.",
    ],
    "customer service": [
        "We're sorry our support fell short here. That's on us — please reach out again and we'll prioritize getting this resolved.",
        "Apologies for the frustrating support experience. We'd like a chance to make it right — please contact us directly.",
    ],
    "sizing": [
        "Sorry the fit wasn't right! We're happy to help with an exchange for the correct size — just reach out to our team.",
    ],
    "price": [
        "Thanks for the honest feedback on pricing — we're always evaluating our value proposition and appreciate you sharing this.",
    ],
    "packaging": [
        "Sorry to hear about the packaging issue — we're looking into improving this and appreciate you flagging it.",
    ],
    "general": [
        "We're really sorry to hear this. This isn't the experience we want for you — please reach out to our support team so we can make it right.",
        "Thank you for flagging this, and we apologize for the trouble. We'd love the chance to fix things for you.",
    ],
}

# ---- Complaint category detection ----
COMPLAINT_KEYWORDS = {
    "shipping": ["shipping", "delivery", "late", "arrived", "delayed", "package", "shipment", "tracking"],
    "quality": ["quality", "broke", "broken", "cheap", "flimsy", "defective", "damaged", "poor", "fell apart"],
    "customer service": ["support", "customer service", "refund", "response", "rude", "helpline", "return policy"],
    "sizing": ["size", "fit", "small", "large", "tight", "loose"],
    "price": ["expensive", "overpriced", "price", "cost", "value for money"],
    "packaging": ["packaging", "box", "wrapped", "seal"],
}


def detect_complaints(negative_texts):
    counts = {}
    for text in negative_texts:
        lower = text.lower()
        for category, keywords in COMPLAINT_KEYWORDS.items():
            if any(kw in lower for kw in keywords):
                counts[category] = counts.get(category, 0) + 1

    # sort by frequency, return top 3
    sorted_complaints = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    return [{"category": cat, "count": cnt} for cat, cnt in sorted_complaints[:3]]


def detect_review_category(text):
    lower = text.lower()
    for category, keywords in COMPLAINT_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return category
    return "general"


def generate_response(label, text=""):
    if label == "POSITIVE":
        return random.choice(POSITIVE_RESPONSES)
    else:
        category = detect_review_category(text)
        return random.choice(NEGATIVE_RESPONSES_BY_CATEGORY[category])

def calculate_satisfaction_score(results):
    if not results:
        return 0

    total_weight = 0
    positive_weight = 0

    for r in results:
        # confidence acts as a weight — stronger sentiment counts more
        weight = max(r["score"], 0.1)  # floor so neutral reviews still count a little
        total_weight += weight
        if r["label"] == "POSITIVE":
            positive_weight += weight

    score = (positive_weight / total_weight) * 100
    return round(score)

@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    text = data.get("text", "")

    if not text.strip():
        return jsonify({"error": "No text provided"}), 400

    chunks = [line.strip() for line in text.split("\n") if line.strip()]
    if not chunks:
        chunks = [text]

    results = []
    positive_count = 0
    negative_count = 0
    total_confidence = 0

    for chunk in chunks:
        scores = analyzer.polarity_scores(chunk)
        compound = scores["compound"]

        label = "POSITIVE" if compound >= 0 else "NEGATIVE"
        if label == "POSITIVE":
            positive_count += 1
        else:
            negative_count += 1

        confidence = abs(compound)
        total_confidence += confidence

        results.append({
            "label": label,
            "score": round(confidence, 3),
            "text": chunk,
            "response": generate_response(label, chunk)
        })

    total = len(results)
    joy_score = positive_count / total
    anger_score = negative_count / total
    avg_confidence = total_confidence / total

    personality_vector = {
        "joy": round(joy_score, 2),
        "anger": round(anger_score, 2),
        "confidence": round(avg_confidence, 2),
        "chunks_analyzed": total
    }

    negative_texts = [r["text"] for r in results if r["label"] == "NEGATIVE"]
    top_complaints = detect_complaints(negative_texts)
    satisfaction_score = calculate_satisfaction_score(results)

    personality_vector["satisfaction_score"] = satisfaction_score
    personality_vector["top_complaints"] = top_complaints

    return jsonify({
        "personality_vector": personality_vector,
        "raw_results": results
    })
    
    
@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "ReviewPulse backend is running"})