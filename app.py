from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from transformers import MarianMTModel, MarianTokenizer

app = Flask(__name__)
socketio = SocketIO(app)

# Load the translation models
tokenizer_en_to_romance = MarianTokenizer.from_pretrained('Helsinki-NLP/opus-mt-en-ROMANCE')
model_en_to_romance = MarianMTModel.from_pretrained('Helsinki-NLP/opus-mt-en-ROMANCE')

tokenizer_romance_to_en = MarianTokenizer.from_pretrained('Helsinki-NLP/opus-mt-ROMANCE-en')
model_romance_to_en = MarianMTModel.from_pretrained('Helsinki-NLP/opus-mt-ROMANCE-en')

users = {}  # Store users' socket ids and details

def translate_to_english(sentence):
    inputs = tokenizer_romance_to_en(sentence, return_tensors="pt", padding=True, truncation=True)
    translated_tokens = model_romance_to_en.generate(**inputs)
    return tokenizer_romance_to_en.decode(translated_tokens[0], skip_special_tokens=True)

def translate_to_romance(sentence):
    inputs = tokenizer_en_to_romance(sentence, return_tensors="pt", padding=True, truncation=True)
    translated_tokens = model_en_to_romance.generate(**inputs)
    return tokenizer_en_to_romance.decode(translated_tokens[0], skip_special_tokens=True)

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('join')
def handle_join(data):
    username = data['username']
    lang = data['lang']
    users[request.sid] = {'username': username, 'lang': lang}
    emit('user_joined', {'username': username}, broadcast=True)
    emit('user_list', {'users': [{'username': u['username']} for u in users.values()]}, broadcast=True)

@socketio.on('private_message')
def handle_private_message(data):
    recipient = data['recipient']
    message = data['message']
    lang = data['lang']
    sender_username = users[request.sid]['username']

    # Find recipient's socket ID
    recipient_sid = None
    for sid, user in users.items():
        if user['username'] == recipient:
            recipient_sid = sid
            break

    if recipient_sid:
        # Translate the message for the recipient
        if lang == 'en':
            translated_message = translate_to_romance(message)
        else:
            translated_message = translate_to_english(message)
        
        emit('private_response', {
            'message': translated_message, 
            'original': message, 
            'sender': sender_username, 
            'recipient': recipient, 
            'lang': lang
        }, room=recipient_sid)

if __name__ == '__main__':
    socketio.run(app, debug=True)
