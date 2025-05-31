import os
import pickle

SESSION_DIR = 'session_data'
os.makedirs(SESSION_DIR, exist_ok=True)

def store_document_data(user_id, data):
    """
    Store document data to file system instead of session
    """
    filename = os.path.join(SESSION_DIR, f"doc_{user_id}.pkl")
    
    with open(filename, 'wb') as f:
        pickle.dump(data, f)
    
    return filename

def get_document_data(user_id):
    """
    Retrieve document data from file system
    """
    filename = os.path.join(SESSION_DIR, f"doc_{user_id}.pkl")
    
    if not os.path.exists(filename):
        return {"extracted_content": "", "explanation": ""}
    
    with open(filename, 'rb') as f:
        return pickle.load(f)

def clear_document_data(user_id):
    """
    Remove document data file if it exists
    """
    filename = os.path.join(SESSION_DIR, f"doc_{user_id}.pkl")
    if os.path.exists(filename):
        os.remove(filename)
