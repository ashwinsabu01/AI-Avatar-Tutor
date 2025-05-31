# avatar_flask_routes.py - Flask routes for the avatar integration
import os
import uuid
import tempfile
from flask import request, jsonify, url_for, session, redirect
import speech_recognition as sr
import google.generativeai as genai
from sentence_transformers import SentenceTransformer, util
import numpy as np
from pydub import AudioSegment
from pydub.silence import split_on_silence

# Import functions from the shared utilities file
from document_utils import get_document_data

def register_avatar_routes(app):
    # Ensure directories exist
    UPLOADS_DIR = os.path.join(app.static_folder, 'uploads')
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    
    # Initialize sentence transformer model for semantic similarity
    sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Store conversation history
    conversation_history = {}
    
    # Enhanced helper function for speech recognition with audio format conversion
    def transcribe_audio(audio_file_path):
        recognizer = sr.Recognizer()
        
        try:
            # First, try to convert the audio to WAV format using pydub
            print(f"[DEBUG] Processing audio file: {audio_file_path}")
            
            # Load audio file with pydub (supports many formats)
            audio = AudioSegment.from_file(audio_file_path)
            
            # Convert to mono and set sample rate to 16kHz (optimal for speech recognition)
            audio = audio.set_channels(1).set_frame_rate(16000)
            
            # Normalize audio levels
            audio = audio.normalize()
            
            # Remove silence from beginning and end
            audio = audio.strip_silence()
            
            # Create a temporary WAV file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
                temp_wav_path = temp_wav.name
                
            # Export as WAV
            audio.export(temp_wav_path, format="wav")
            
            # Now use speech recognition on the converted file
            with sr.AudioFile(temp_wav_path) as source:
                # Adjust for ambient noise
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                
                # Record the audio
                audio_data = recognizer.record(source)
                
                try:
                    # Try Google Speech Recognition first
                    text = recognizer.recognize_google(audio_data)
                    print(f"[DEBUG] Successfully transcribed: {text}")
                    return text
                    
                except sr.UnknownValueError:
                    # If Google fails, try with Sphinx (offline)
                    try:
                        text = recognizer.recognize_sphinx(audio_data)
                        print(f"[DEBUG] Sphinx transcription: {text}")
                        return text
                    except sr.UnknownValueError:
                        return "Sorry, I couldn't understand your audio. Please try speaking more clearly."
                    except sr.RequestError:
                        return "Sorry, I couldn't understand your audio. Please try speaking more clearly."
                        
                except sr.RequestError as e:
                    print(f"[DEBUG] Google Speech Recognition error: {e}")
                    # Fallback to Sphinx
                    try:
                        text = recognizer.recognize_sphinx(audio_data)
                        print(f"[DEBUG] Sphinx fallback transcription: {text}")
                        return text
                    except:
                        return "Sorry, there was an issue with the speech recognition service."
            
        except Exception as e:
            print(f"[DEBUG] Audio processing error: {str(e)}")
            
            # Fallback: try direct speech recognition without conversion
            try:
                with sr.AudioFile(audio_file_path) as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    audio_data = recognizer.record(source)
                    
                    try:
                        return recognizer.recognize_google(audio_data)
                    except sr.UnknownValueError:
                        try:
                            return recognizer.recognize_sphinx(audio_data)
                        except:
                            return "Sorry, I couldn't understand your audio."
                    except sr.RequestError:
                        return "Sorry, there was an issue with the speech recognition service."
                        
            except Exception as fallback_error:
                print(f"[DEBUG] Fallback audio processing error: {str(fallback_error)}")
                return f"Sorry, I couldn't process your audio file. Please ensure it's a valid audio format."
        
        finally:
            # Clean up temporary files
            try:
                if 'temp_wav_path' in locals() and os.path.exists(temp_wav_path):
                    os.unlink(temp_wav_path)
            except:
                pass
    
    # Initialize Gemini model with more conversational prompting
    def init_gemini(api_key):
        genai.configure(api_key=api_key)
        return genai.GenerativeModel('models/gemini-2.0-flash')
    
    # Get response from Gemini AI with document context and conversation history
    def get_gemini_response(prompt, document_content=None, user_id=None):
        try:
            model = init_gemini(app.config['GOOGLE_API_KEY'])
            
            # Get or initialize conversation history for this user
            if user_id not in conversation_history:
                conversation_history[user_id] = []
            
            # Create history context from past exchanges (limit to last 5)
            history_context = ""
            if conversation_history[user_id]:
                history_context = "Our recent conversation:\n"
                for i, exchange in enumerate(conversation_history[user_id][-5:]):
                    history_context += f"You: {exchange['user']}\n"
                    history_context += f"Assistant: {exchange['assistant']}\n"
            
            if document_content and document_content.strip():
                # Create a context-aware system prompt for the model with conversational tone
                context_prompt = f"""
                Document Content: {document_content}
                
                {history_context}
                
                User says: {prompt}
                
                You are a helpful, friendly AI assistant having a natural conversation. 
                Respond to the user in a warm, conversational tone like you're chatting with a friend.
                Use contractions, occasionally ask questions back, and maintain a friendly, casual tone.
                Your replies should be helpful but concise (2-4 sentences at most).
                
                If the question relates to the document content, base your answer on that information.
                If the question isn't about the document, you can answer generally.
                """
                response = model.generate_content(context_prompt)
            else:
                # Fallback with conversational tone if no document content
                standard_prompt = f"""
                {history_context}
                
                User says: {prompt}
                
                You are a helpful, friendly AI assistant having a natural conversation.
                Respond in a warm, conversational tone like you're chatting with a friend.
                Use contractions, occasionally ask questions back, and maintain a friendly, casual tone.
                Your replies should be helpful but concise (2-4 sentences at most).
                """
                response = model.generate_content(standard_prompt)
            
            # Store this exchange in history
            if user_id:
                conversation_history[user_id].append({
                    'user': prompt,
                    'assistant': response.text
                })
                
                # Keep history at reasonable size
                if len(conversation_history[user_id]) > 20:
                    conversation_history[user_id] = conversation_history[user_id][-20:]
                
            return response.text
        except Exception as e:
            print(f"Error getting Gemini response: {str(e)}")
            return "I'm sorry, I couldn't process your request right now."

    # Route to serve the avatar page
    @app.route('/avatar')
    def avatar_page():
        # Store a flag indicating that we're going to the avatar page
        session['visited_avatar'] = True
        return app.send_static_file('avatar.html')
    
    # Route to get document context for avatar
    @app.route('/avatar/context', methods=['GET'])
    def get_avatar_context():
        # Check if user has a user_id and document
        if 'user_id' not in session or not session.get('has_document', False):
            return jsonify({
                'extracted_content': '',
                'explanation': ''
            })
        
        # Get document data from file storage using the imported function
        doc_data = get_document_data(session['user_id'])
        
        return jsonify({
            'extracted_content': doc_data.get('extracted_content', ''),
            'explanation': doc_data.get('explanation', '')
        })
    
    # Route to handle avatar chat interactions
    @app.route('/avatar/chat', methods=['POST'])
    def avatar_chat():
        try:
            input_type = request.form.get('type', 'text')
            user_input = ""

            if input_type == 'text':
                user_input = request.form.get('input', '')
            elif input_type == 'audio':
                if 'audio' not in request.files:
                    return jsonify({'error': 'No audio file provided'}), 400

                audio_file = request.files['audio']
                
                # Create a more robust temporary file handling
                temp_audio_path = None
                try:
                    # Create temporary file with proper extension based on content type
                    file_extension = '.wav'  # default
                    if audio_file.content_type:
                        if 'mp3' in audio_file.content_type:
                            file_extension = '.mp3'
                        elif 'mp4' in audio_file.content_type:
                            file_extension = '.mp4'
                        elif 'webm' in audio_file.content_type:
                            file_extension = '.webm'
                        elif 'ogg' in audio_file.content_type:
                            file_extension = '.ogg'
                    
                    # Create temp file
                    with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as temp_audio:
                        audio_file.save(temp_audio.name)
                        temp_audio_path = temp_audio.name
                    
                    print(f"[DEBUG] Saved audio file to: {temp_audio_path}")
                    print(f"[DEBUG] Audio file size: {os.path.getsize(temp_audio_path)} bytes")
                    
                    user_input = transcribe_audio(temp_audio_path)
                    print(f"[DEBUG] Transcription result: {user_input}")
                    
                except Exception as audio_error:
                    print(f"[DEBUG] Audio processing error: {str(audio_error)}")
                    return jsonify({'error': f'Audio processing failed: {str(audio_error)}'}), 400
                    
                finally:
                    # Clean up temp file
                    if temp_audio_path and os.path.exists(temp_audio_path):
                        try:
                            os.unlink(temp_audio_path)
                        except:
                            pass

            # Validate that we got some input
            if not user_input or user_input.strip() == "":
                return jsonify({'error': 'No valid input received'}), 400

            # Get document content from file storage if available
            extracted_content = ""
            if 'user_id' in session and session.get('has_document', False):
                doc_data = get_document_data(session['user_id'])
                extracted_content = doc_data.get('extracted_content', '')
            
            # Log the context being used for debugging
            print(f"Chat request with input: '{user_input}'")
            print(f"Using document context? {'Yes' if extracted_content else 'No'}")
            
            # Get user ID for conversation history
            user_id = session.get('user_id')
            
            # Get Gemini response with document context and conversation history
            response_text = get_gemini_response(user_input, extracted_content, user_id)

            return jsonify({
                'text': response_text
            })

        except Exception as e:
            print(f"Error in avatar chat: {str(e)}")
            return jsonify({'error': f'Server error: {str(e)}'}), 500