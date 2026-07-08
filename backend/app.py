from flask import Flask, request, jsonify
from flask_cors import CORS
import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import os

app = Flask(__name__)
CORS(app)

# Global variables for model and tokenizer - initially None
model = None
tokenizer = None
model_name = "vennify/t5-base-grammar-correction"  # ✅ Working model

def load_model():
    """Load model and tokenizer only when first needed"""
    global model, tokenizer
    if model is None:
        print("Loading model... (This may take a moment)")
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        print("Model loaded successfully!")
    return model, tokenizer

@app.route('/correct', methods=['POST'])
def correct_grammar():
    try:
        data = request.get_json()
        text = data.get('text', '')
        if not text:
            return jsonify({'error': 'No text provided'}), 400

        # Load model lazily
        model, tokenizer = load_model()

        # Process text (adjust based on your model's requirements)
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        outputs = model.generate(**inputs, max_length=512)
        corrected = tokenizer.decode(outputs[0], skip_special_tokens=True)

        return jsonify({'corrected_text': corrected})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))