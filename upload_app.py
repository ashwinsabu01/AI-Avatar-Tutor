import re
import os
import uuid
from flask import Flask, request, jsonify, render_template, url_for
from flask_cors import CORS
from werkzeug.utils import secure_filename
from gtts import gTTS
from transformers import pipeline
import pdf2image
import pytesseract
import docx
import pptx
import google.generativeai as genai
from dotenv import load_dotenv

app = Flask(__name__)
CORS(app)

# Configure upload folder and audio folder
UPLOAD_FOLDER = 'uploads'
AUDIO_FOLDER = os.path.join('static', 'audio_files')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(AUDIO_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['AUDIO_FOLDER'] = AUDIO_FOLDER

# Load environment variables
load_dotenv()
api_key = <api_key_here>

if not api_key:
    raise ValueError("GOOGLE_API_KEY not found in environment variables")

genai.configure(api_key=api_key)

# Initialize question-answering model 
qa_model = pipeline("question-answering")


def clean_text(text):
    """Remove special characters and extra whitespace from the text."""
    cleaned_text = re.sub(r'\*+|[_~`^]', '', text)
    cleaned_text = re.sub(r'[^\w\s.,!?]', '', cleaned_text)
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
    return cleaned_text


def extract_text_from_pdf(file_path):
    text = ""
    images = pdf2image.convert_from_path(file_path)
    for image in images:
        text += pytesseract.image_to_string(image) + "\n"
    return text


def extract_text_from_docx(file_path):
    doc = docx.Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs])


def extract_text_from_pptx(file_path):
    text = ""
    presentation = pptx.Presentation(file_path)
    for slide in presentation.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                text += shape.text + "\n"
    return text


def extract_text(file_path):
    if file_path.endswith('.pdf'):
        return extract_text_from_pdf(file_path)
    elif file_path.endswith('.docx'):
        return extract_text_from_docx(file_path)
    elif file_path.endswith('.pptx'):
        return extract_text_from_pptx(file_path)
    else:
        raise ValueError("Unsupported file type")


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    # Extract text from the uploaded file
    extracted_text = extract_text(file_path)

    # Use Gemini AI to generate an explanation
    try:
        model = genai.GenerativeModel('gemini-pro')
        explanation = model.generate_content(
            f"Explain this content: {extracted_text}").text
    except Exception as e:
        return jsonify({'error': f"Gemini AI Error: {str(e)}"}), 500

    # Clean the explanation text
    cleaned_explanation = clean_text(explanation)

    # Convert cleaned explanation to speech
    unique_filename = f"{uuid.uuid4().hex}.mp3"
    audio_path = os.path.join(app.config['AUDIO_FOLDER'], unique_filename)
    tts = gTTS(text=cleaned_explanation, lang='en')
    tts.save(audio_path)

    # Generate quiz questions and answers
    try:
        quiz_response = model.generate_content(
            f"""
        Content: {extracted_text}

        Generate a quiz based on the above content in this JSON format:
        [
            {{
                "question": "Question text",
                "option": ["Option1", "Option2", "Option3", "Option4"],
                "answer": "Correct answer text",
                "explanation": "Explanation text for the correct answer"
            }},
            ...
        ]
        The topic of the quiz should directly relate to the content provided above. 
        Each question must be based on the main ideas or facts in the text.
        Ensure to generate a JSON response without any additional text or formatting outside of the JSON structure.
        Explanation should also tell which topic needs to be revised.
        """
        ).text
    except Exception as e:
        return jsonify({'error': f"Gemini AI Error (Quiz): {str(e)}"}), 500

    return jsonify({
        'extracted_text': extracted_text,
        'explanation': cleaned_explanation,
        'audio_file': url_for('static', filename=f'audio_files/{unique_filename}'),
        'quiz': quiz_response
    })


@app.route('/submit_quiz', methods=['POST'])
def submit_quiz():
    data = request.json
    user_answers = data.get('answers', [])
    correct_answers = data.get('correct_answers', [])
    feedback = []

    for i, (user_answer, correct_answer) in enumerate(zip(user_answers, correct_answers)):
        if user_answer == correct_answer:
            feedback.append(f"Question {i + 1}: Correct!")
        else:
            feedback.append(
                f"Question {i + 1}: Incorrect. The correct answer is: {correct_answer}")

    return jsonify({
        'feedback': feedback,
        'score': f"{sum([1 for u, c in zip(user_answers, correct_answers) if u == c])}/{len(correct_answers)}"
    })


if __name__ == '__main__':
    app.run(debug=True)
