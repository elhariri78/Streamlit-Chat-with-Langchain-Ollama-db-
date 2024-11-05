import streamlit as st
import peewee as pw
from datetime import datetime
from langchain_ollama import OllamaLLM

## 1 ## Setup Database

# Create an SQLite database named 'chat_history.db' to store chat messages
db = pw.SqliteDatabase('chat_history.db')

# Define the Message model that will correspond to a table in the database
class Message(pw.Model):
    question = pw.CharField()  # Column to store the user's question
    answer = pw.CharField()    # Column to store the assistant's answer
    created_at = pw.DateTimeField(default=datetime.now)  # Column to store the timestamp of the message

    class Meta:
        database = db  # Specify the database to be used for this model

# Connect to the database and create the tables defined by the model
db.connect()
db.create_tables([Message])  # Create the Message table if it does not exist

## 2 ## Setup Streamlit Application

# Set the title of the Streamlit application
st.title("Chat With Ollama")

# Create a sidebar for the chat history
with st.sidebar:
    st.header("Chat History")  # Header for the sidebar

    # Retrieve messages from the database, ordered by creation time (newest first)
    messages = Message.select().order_by(Message.created_at.desc())

    # Display each message in the sidebar with buttons for selection and deletion
    for msg in messages:
        col1, col2 = st.columns([3, 1])  # Create two columns for the question and delete button
        with col1:
            # Create a button for each question; the button's key is a unique identifier
            if st.button(msg.question, key=f"{msg.question}{msg.id}"):
                st.session_state.selected_chat = msg.id  # Store the selected chat ID in session state
        with col2:
            # Create a delete button to remove the message from the database
            if st.button("X", key=msg.id):
                Message.delete().where(Message.id == msg.id).execute()  # Delete the message from the database
                st.rerun()  # Refresh the app to reflect changes

## 3 ## Create Chat Functionality

# Initialize an empty list in session state to hold the messages
if "messages" not in st.session_state:
    st.session_state.messages = []

# If a chat has been selected, display its answer in the main area
if 'selected_chat' in st.session_state:
    single_chat = Message.get_by_id(st.session_state.selected_chat)  # Retrieve the selected chat from the database
    st.write(single_chat.answer)  # Display the answer of the selected chat

# Display chat messages stored in the session state
for message in st.session_state.messages:
    with st.chat_message(message['question']):
        st.markdown(message['answer'])  # Display the answer as markdown

# Add an input field for user prompts
prompt = st.chat_input("What would you like to discuss?")

## 4 ## Setup Ollama Language Model

@st.cache_resource  # Caches the Ollama model instance to avoid reinitialization on every run
def initialize_ollama():
    llm = OllamaLLM(
        model="llama3.2:1b",  # Specify the model to be used for the language processing
    )
    return llm

llm = initialize_ollama()  # Initialize the Ollama language model

## 5 ## Handle Chat Logic

# If the user has entered a prompt, process it
if prompt:
    # Display the user's prompt in the chat
    with st.chat_message("user"):
        st.markdown(prompt)

    # Prepare to display the assistant's response
    with st.chat_message("assistant"):
        response_placeholder = st.empty()  # Placeholder for the response
        final_response = ''  # Initialize a variable to accumulate the final response

        # Stream the response from the language model token by token
        for token in llm.stream(prompt):
            final_response += token  # Append the new token to the final response
            response_placeholder.markdown(final_response)  # Update the placeholder with the current response

    # Save the session message to the session state
    st.session_state.messages.append({"question": prompt, "answer": final_response})

    # Save the conversation to the database
    Message.create(question=prompt, answer=final_response)  # Create a new record in the Message table
