import os
import csv
import streamlit as st
from llama_index import VectorStoreIndex, ServiceContext, Document
from llama_index.llms import OpenAI
import openai
import PyPDF2
import requests


openai.api_key = os.environ.get("OPENAI_API_KEY")


st.set_page_config(page_title="Chat with docs, powered by MindTickle", page_icon="🦙", layout="centered", initial_sidebar_state="auto", menu_items=None)
# openai.api_key = "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"
st.title("Chat with the Streamlit docs, powered by MindTickle 💬🦙")

uploaded_pdf = st.file_uploader("Upload a PDF file", type=["pdf"])

if "messages" not in st.session_state.keys():
    st.session_state.messages = [{"role": "assistant", "content": "Upload a PDF and then ask me a question about its content!"}]

def extract_text_from_pdf(pdf_file):
    pdf_reader = PyPDF2.PdfFileReader(pdf_file)
    text = ""
    for page in range(pdf_reader.numPages):
        text += pdf_reader.getPage(page).extractText()
    return text

def display_feedbacks():
    if "feedbacks" in st.session_state and st.session_state.feedbacks:
        st.subheader("Feedbacks Received")
        for idx, feedback in enumerate(st.session_state.feedbacks, 1):
            st.text(f"Feedback {idx}: {feedback}/5")
        avg_feedback = sum(st.session_state.feedbacks) / len(st.session_state.feedbacks)
        st.write(f"Average feedback score: {avg_feedback:.2f}/5")


def check_content_moderation(text):
    try:
        url = "https://api.openai.com/v1/moderations"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {openai.api_key}"
        }
        data = {"input": text}
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        data = response.json()
        flagged_status = data['results'][0]['flagged']
        return {"flagged": flagged_status}
    except requests.RequestException as e:
        st.error(f"Error checking content moderation: {e}")
        return {"flagged": True} 
    except KeyError:
        st.warning("Unexpected response format from moderation API.")
        return {"flagged": True} 
    
def save_feedback_to_csv(question, answer,feedback):
    with open('user_feedbacks.csv', mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([question, answer, feedback])

if uploaded_pdf:
    st.success("PDF uploaded successfully! Indexing content...")
    extracted_text = extract_text_from_pdf(uploaded_pdf)
    docs = [Document(title="Uploaded PDF", text=extracted_text)]
    service_context = ServiceContext.from_defaults(llm=OpenAI(model="gpt-3.5-turbo", temperature=0.5, system_prompt="You are an expert on the uploaded document content. Your job is to answer questions based on this content."))
    index = VectorStoreIndex.from_documents(docs, service_context=service_context)
    chat_engine = index.as_chat_engine(chat_mode="condense_question", verbose=True)

    prompt = st.chat_input("Your question")
    if prompt:
        moderation_result = check_content_moderation(prompt)
        if moderation_result["flagged"]:
            with st.chat_message("assistant"):
                st.write("Sorry, that content is not appropriate. Please provide a different input.")
        else:
            st.session_state.messages.append({"role": "user", "content": prompt})
            # Process and add the assistant's response.
            response = chat_engine.chat(prompt)
            message = {"role": "assistant", "content": response.response}
            st.session_state.messages.append(message)
        
    # Display all the chat messages from session_state.
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    if prompt and not moderation_result["flagged"]:
        # Feedback mechanism
        feedback = st.slider("Rate the accuracy of the response (1=poor, 5=excellent):", 1, 5)
        if st.button("Submit Feedback"):
            st.session_state.feedbacks.append(feedback)
            save_feedback_to_csv(prompt, response,feedback)
            display_feedbacks()

else:
    st.text("Please upload a PDF to proceed.")


# After processing user input and displaying responses, display the feedbacks
display_feedbacks()
