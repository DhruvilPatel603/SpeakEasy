from flask import Flask, render_template, jsonify, request, session, redirect
from flask_cors import CORS
import openai
import os
from dotenv import load_dotenv
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
import pywhatkit  
import socket  

load_dotenv()

openai_api_key = os.getenv('OPENAI_API_KEY')

# Set up the ChatOpenAI instance
llm = ChatOpenAI(model="gpt-3.5-turbo", openai_api_key=openai_api_key)
memory = ConversationBufferMemory(llm=llm, max_token_limit=100)
app = Flask(__name__)
app.secret_key = 'Hello'  # Change this to a random secret key
CORS(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data', methods=['POST'])
def get_data():
    data = request.get_json()
    text = data.get('data')
    user_input = text
    
    # Retrieve chat history from session
    chat_history = session.get('chat_history', [])
    # Append new user message to chat history
    chat_history.append({"type": "user", "message": user_input})
    # Save updated chat history to session
    session['chat_history'] = chat_history
    
    try:
        conversation = ConversationChain(llm=llm, memory=memory)
        output = conversation.predict(input=user_input)
        memory.save_context({"input": user_input}, {"output": output})

        # Detect text within double quotes in the bot's output if it contains specific keywords
        keywords = ["song", "music", "track", "listen", "sing"]
        ignore_list = ["<img src=", "image.jpg", "Description of image"]
        user_input_keywords = ["play"]
        user_input_lower = user_input.lower()
        output_lower = output.lower()
        if any(keyword in user_input_lower for keyword in user_input_keywords):
            print(f"Keywords detected in input: {user_input_keywords}")
            pywhatkit.playonyt(user_input)
            for item in user_input_keywords:
                user_input = user_input.replace(item, "", 1)
                user_input = user_input.strip()
            response_json = {
                "response": True,
                "message": f"Playing \"{user_input}\" on YouTube."
            }
        
        elif any(keyword in output_lower for keyword in keywords):
            print(f"Keywords detected in output: {keywords}")
            first_quote = output.find('"')
            if first_quote != -1:
                second_quote = output.find('"', first_quote + 1)
                if second_quote != -1:
                    query = output[first_quote + 1:second_quote]
                    print(f"Query found: {query}")
                    if not any(ignore_word.lower() in output_lower for ignore_word in ignore_list):
                        pywhatkit.playonyt(query)
                        response_json = {
                            "response": True,
                            "message": f"Playing \"{query}\" on YouTube."
                        }
                    else:
                        response_json = {
                            "response": True,
                            "message": output  # Use the original output as the message when ignored words are detected
                        }
                else:
                    response_json = {
                        "response": True,
                        "message": output  # Use the original output as the message when ignored words are detected
                    }
            else:
                response_json = {
                    "response": True,
                    "message": output  # Use the original output as the message when no quotes are found
                }
        else:
            response_json = {"response": True, "message": output}

        # Append bot response to chat history
        chat_history.append({"type": "bot", "message": output})
        # Save updated chat history to session
        session['chat_history'] = chat_history

        return jsonify(response_json)
    except Exception as e:
        print(e)
        error_message = f'Error: {str(e)}'
        return jsonify({"message": error_message, "response": False})

@app.route('/history', methods=['GET'])
def get_history():
    chat_history = session.get('chat_history', [])
    return jsonify(chat_history)

@app.route('/clear', methods=['POST'])
def clear_history():
    save_chat_history_to_file()  # Save the chat history before clearing
    session.pop('chat_history', None)
    session.pop('last_keyword', None)  # Clear the last keyword
    return jsonify({"response": True, "message": "Chat history cleared."})

@app.route('/save', methods=['POST'])
def save_history():
    save_chat_history_to_file()
    return jsonify({"response": True, "message": "Chat history saved."})

def save_chat_history_to_file():
    chat_history = session.get('chat_history', [])
    with open('logs.txt', 'a') as f:
        for entry in chat_history:
            f.write(f"{entry['type'].upper()}: {entry['message']}\n")
        f.write("\n--- End of Session ---\n\n")

if __name__ == '__main__':
    # Get local IP address
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    port = 5000  # Default Flask port

    print(f"Running on http://{local_ip}:{port}")
    app.run(host='0.0.0.0', port=port)
