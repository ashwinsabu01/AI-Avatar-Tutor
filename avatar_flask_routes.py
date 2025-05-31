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

from document_utils import get_document_data

def register_avatar_routes(app):
    UPLOADS_DIR = os.path.join(app.static_folder, 'uploads')
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    
    sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    conversation_history = {}
    
    def transcribe_audio(audio_file_path):
        recognizer = sr.Recognizer()
        
        try:
            print(f"[DEBUG] Processing audio file: {audio_file_path}")
            
            audio = AudioSegment.from_file(audio_file_path)
            
            audio = audio.set_channels(1).set_frame_rate(16000)
            
            audio = audio.normalize()
            
            audio = audio.strip_silence()
            
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
                temp_wav_path = temp_wav.name
                
            audio.export(temp_wav_path, format="wav")
            
            with sr.AudioFile(temp_wav_path) as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                
                audio_data = recognizer.record(source)
                
                try:
                    text = recognizer.recognize_google(audio_data)
                    print(f"[DEBUG] Successfully transcribed: {text}")
                    return text
                    
                except sr.UnknownValueError:
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
                    try:
                        text = recognizer.recognize_sphinx(audio_data)
                        print(f"[DEBUG] Sphinx fallback transcription: {text}")
                        return text
                    except:
                        return "Sorry, there was an issue with the speech recognition service."
            
        except Exception as e:
            print(f"[DEBUG] Audio processing error: {str(e)}")
            
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
            try:
                if 'temp_wav_path' in locals() and os.path.exists(temp_wav_path):
                    os.unlink(temp_wav_path)
            except:
                pass
    
    def init_gemini(api_key):
        genai.configure(api_key=api_key)
        return genai.GenerativeModel('models/gemini-2.0-flash')
    
    def get_gemini_response(prompt, document_content=None, user_id=None):
        try:
            model = init_gemini(app.config['GOOGLE_API_KEY'])
            
            if user_id not in conversation_history:
                conversation_history[user_id] = []
            
            history_context = ""
            if conversation_history[user_id]:
                history_context = "Our recent conversation:\n"
                for i, exchange in enumerate(conversation_history[user_id][-5:]):
                    history_context += f"You: {exchange['user']}\n"
                    history_context += f"Assistant: {exchange['assistant']}\n"
            
            if document_content and document_content.strip():
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
                standard_prompt = f"""
                {history_context}
                
                User says: {prompt}
                
                You are a helpful, friendly AI assistant having a natural conversation.
                Respond in a warm, conversational tone like you're chatting with a friend.
                Use contractions, occasionally ask questions back, and maintain a friendly, casual tone.
                Your replies should be helpful but concise (2-4 sentences at most).
                """
                response = model.generate_content(standard_prompt)
            
            if user_id:
                conversation_history[user_id].append({
                    'user': prompt,
                    'assistant': response.text
                })
                
                if len(conversation_history[user_id]) > 20:
                    conversation_history[user_id] = conversation_history[user_id][-20:]
                
            return response.text
        except Exception as e:
            print(f"Error getting Gemini response: {str(e)}")
            return "I'm sorry, I couldn't process your request right now."

    @app.route('/avatar')
    def avatar_page():
        session['visited_avatar'] = True
        return app.send_static_file('avatar.html')
    
    @app.route('/avatar/context', methods=['GET'])
    def get_avatar_context():
        if 'user_id' not in session or not session.get('has_document', False):
            return jsonify({
                'extracted_content': '',
                'explanation': ''
            })
        
        doc_data = get_document_data(session['user_id'])
        
        return jsonify({
            'extracted_content': doc_data.get('extracted_content', ''),
            'explanation': doc_data.get('explanation', '')
        })
    
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
                
                temp_audio_path = None
                try:
                    file_extension = '.wav'  
                    if audio_file.content_type:
                        if 'mp3' in audio_file.content_type:
                            file_extension = '.mp3'
                        elif 'mp4' in audio_file.content_type:
                            file_extension = '.mp4'
                        elif 'webm' in audio_file.content_type:
                            file_extension = '.webm'
                        elif 'ogg' in audio_file.content_type:
                            file_extension = '.ogg'
                    
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
                    if temp_audio_path and os.path.exists(temp_audio_path):
                        try:
                            os.unlink(temp_audio_path)
                        except:
                            pass

            if not user_input or user_input.strip() == "":
                return jsonify({'error': 'No valid input received'}), 400

            extracted_content = ""
            if 'user_id' in session and session.get('has_document', False):
                doc_data = get_document_data(session['user_id'])
                extracted_content = doc_data.get('extracted_content', '')
            
            print(f"Chat request with input: '{user_input}'")
            print(f"Using document context? {'Yes' if extracted_content else 'No'}")
            
            user_id = session.get('user_id')
            
            response_text = get_gemini_response(user_input, extracted_content, user_id)

            return jsonify({
                'text': response_text
            })

        except Exception as e:
            print(f"Error in avatar chat: {str(e)}")
            return jsonify({'error': f'Server error: {str(e)}'}), 500
