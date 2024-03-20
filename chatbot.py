import requests
import streamlit as st
import openai
import json
from PIL import Image
import secrets
import string

image_logo = Image.open('bmw_logo.png')
st.set_page_config(page_title="Chatbot", layout="centered", initial_sidebar_state="collapsed", menu_items=None,)

if "session_id" not in st.session_state.keys():
    characters = string.ascii_letters + string.digits
    st.session_state.session_id = ''.join(secrets.choice(characters) for i in range(32))

with st.sidebar:
    st.session_state.params = st.experimental_get_query_params()
    st.write(st.session_state.params)
    # st.write("Location: " +st.session_state.params["location"][0])
    # st.write("Duration: " +st.session_state.params["duration"][0])
    # st.write("Usage: " +st.session_state.params["usage"][0])
    # st.write("Deal_type: " +st.session_state.params["deal_type"][0])

def call_chatbot_api(message):
    headers = {
        'Content-Type': 'application/json'  
    }

    try:
        data = {"question": message, "session_id": st.session_state.session_id}

        response = requests.post("http://bmwbot.mediqdemo.com/", headers=headers, json=data)
        response.raise_for_status()  # Raise an exception for 4xx and 5xx status codes

        # If the API returns JSON data in the response, you can access it like this:
        response_data = response.json()

        print("This is reply:"+response_data["reply"])
        print("This is session id:"+response_data["session_id"])

        return response_data["reply"]

    except requests.exceptions.RequestException as e:
        # Handle any request-related errors (e.g., connection error, timeout, etc.)
        print("Error in API:", e)
        return None

if "messages" not in st.session_state.keys(): # Initialize the chat messages history
    st.session_state.messages = [
        {"role": "assistant", "content": "Hi, I am a BMW car dealer assistant. How can I Help ?"}
    ]

if prompt := st.chat_input("Your question"): # Prompt for user input and save to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

for message in st.session_state.messages: # Display the prior chat messages
    if message["role"] == "assistant":
        with st.chat_message(message["role"],avatar=image_logo):
            st.markdown(message["content"], unsafe_allow_html=False)

    if message["role"] == "user":
        with st.chat_message(message["role"],avatar="👨‍💼"):
            st.markdown(message["content"], unsafe_allow_html=False)

# If last message is not from assistant, generate a new response
if st.session_state.messages[-1]["role"] != "assistant":
    with st.chat_message("assistant", avatar=image_logo):
        with st.spinner("Please wait ..."):
            #response = func_response(st.session_state.messages)
            response = call_chatbot_api(prompt)
            st.markdown(response, unsafe_allow_html=False)
            message = {"role": "assistant", "content": response}
            st.session_state.messages.append(message) # Add response to message history