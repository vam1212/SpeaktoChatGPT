import os
import openai
import speech_recognition as sr
import uuid
from google.cloud import texttospeech
from pydub import AudioSegment
from pydub.playback import play
import threading

# Set your API keys as environment variables
os.environ['OPENAI_API_KEY'] = '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'
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "C:\\Users\\Dom\\OneDrive\\Desktop\\desktop\\vscode projects\\speaktochatgpt\\dynamic-art-353419-aa899bb20b66.json"

# Initialize OpenAI API
openai.api_key = os.environ['OPENAI_API_KEY']

# Initialize Google Text-to-Speech client
tts_client = texttospeech.TextToSpeechClient()

# Set the chat directory
chat_directory = os.path.join("C:", os.sep, "Users", "Dom", "OneDrive", "Desktop", "desktop", "vscode projects", "talktochatgpt", "chats")

if not os.path.exists(chat_directory):
    os.makedirs(chat_directory)

stop_audio_playback = False

def listen_for_stop_command():
    global stop_audio_playback
    recognizer = sr.Recognizer()
    while True:
        with sr.Microphone() as source:
            audio = recognizer.listen(source)

        try:
            command = recognizer.recognize_google(audio)
            if command.lower() == "stop":
                stop_audio_playback = True
                break
        except sr.UnknownValueError:
            pass
        except sr.RequestError as e:
            print("Error with Google Speech Recognition service: {0}".format(e))

# Function to play the AI's response
def play_response(audio_file):
    global stop_audio_playback
    try:
        audio = AudioSegment.from_file(audio_file, format="mp3")
        stop_audio_playback = False
        stop_listen_thread = threading.Thread(target=listen_for_stop_command)
        stop_listen_thread.start()

        for chunk in audio[::100]:
            if stop_audio_playback:
                break
            play(chunk)

        stop_listen_thread.join()
    except KeyboardInterrupt:
        print("\nStopped playback. You can ask another question now.")

# Load conversation history from all files in the directory
def load_all_conversation_history(directory):
    conversation_history = []
    for filename in os.listdir(directory):
        if filename.endswith(".txt"):
            filepath = os.path.join(directory, filename)
            with open(filepath, "r") as f:
                for line in f:
                    role, content = line.strip().split(": ", 1)
                    role = role.lower()
                    conversation_history.append({"role": role, "content": content})
    return conversation_history

# Truncate conversation history to fit within the token limit
def estimate_token_count(text):
    return len(text.split())

def truncate_conversation_history(conversation_history, max_tokens=4096):
    total_tokens = 0
    truncated_history = []

    for message in reversed(conversation_history):
        tokens = estimate_token_count(message["content"])
        if total_tokens + tokens < max_tokens:
            truncated_history.insert(0, message)
            total_tokens += tokens
        else:
            break

    return truncated_history

# Load all chat history files from the chat directory
conversation_history = load_all_conversation_history(chat_directory)

# Truncate conversation history to fit within the token limit
conversation_history = truncate_conversation_history(conversation_history)

if not conversation_history:
    # Initialize conversation history for 
        conversation_history = [    {"role": "system", "content": "You are chatting with an AI assistant."}]

def chat_with_chatgpt(prompt):
    global conversation_history
    conversation_history.append({"role": "user", "content": prompt})
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=conversation_history,
            max_tokens=1024,
            n=1,
            temperature=0.5,
            timeout=30 # 30 seconds timeout
        )
        message = response.choices[0].message['content'].strip()
        conversation_history.append({"role": "assistant", "content": message})
        return message
    except openai.error.OpenAIError as e:
        print(f"Error occurred: {e}")
        return "An error occurred while generating a response."

def text_to_speech(text):
    try:
        input_text = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            ssml_gender=texttospeech.SsmlVoiceGender.FEMALE,
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        response = tts_client.synthesize_speech(
            input=input_text, voice=voice, audio_config=audio_config
        )

        output_file = f"{chat_directory}/{str(uuid.uuid4())}.mp3"
        with open(output_file, "wb") as out:
            out.write(response.audio_content)
        return output_file
    except Exception as e:
        print(f"Error occurred: {e}")
        return None

def listen_and_recognize():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        audio = recognizer.listen(source)
    try:
        print("Recognizing...")
        text = recognizer.recognize_google(audio)
        return text
    except sr.UnknownValueError:
        print("Could not understand audio")
    except sr.RequestError as e:
        print("Could not request results; {0}".format(e))

def save_conversation_history():
    filename = f"{chat_directory}/conversation_{str(uuid.uuid4())}.txt"
    with open(filename, "w") as f:
        for message in conversation_history:
            role = message["role"]
            content = message["content"]
            f.write(f"{role.capitalize()}: {content}\n")

if __name__ == "__main__":
    while True:
        user_input = listen_and_recognize()
        if user_input:
            print("You said:", user_input)
            if user_input.lower() == "end":
                save_conversation_history()
                break
            chatgpt_response = chat_with_chatgpt(user_input)
            print("ChatGPT Response:", chatgpt_response)
            output_audio_path = text_to_speech(chatgpt_response)
            if output_audio_path:
                output_audio = AudioSegment.from_mp3(output_audio_path)
                play(output_audio)
            else:
                print("Failed to generate audio response.")
        else:
            print("Please try again.")

