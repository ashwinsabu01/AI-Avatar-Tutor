# document_utils.py - Common utilities for document handling
import os
import pickle

# Create a directory for storing session files
SESSION_DIR = 'session_data'
os.makedirs(SESSION_DIR, exist_ok=True)

def store_document_data(user_id, data):
    """
    Store document data to file system instead of session
    """
    # Create a unique filename based on user_id
    filename = os.path.join(SESSION_DIR, f"doc_{user_id}.pkl")
    
    # Store the data
    with open(filename, 'wb') as f:
        pickle.dump(data, f)
    
    return filename

def get_document_data(user_id):
    """
    Retrieve document data from file system
    """
    filename = os.path.join(SESSION_DIR, f"doc_{user_id}.pkl")
    
    # Check if file exists
    if not os.path.exists(filename):
        return {"extracted_content": "", "explanation": ""}
    
    # Load the data
    with open(filename, 'rb') as f:
        return pickle.load(f)

def clear_document_data(user_id):
    """
    Remove document data file if it exists
    """
    filename = os.path.join(SESSION_DIR, f"doc_{user_id}.pkl")
    if os.path.exists(filename):
        os.remove(filename)