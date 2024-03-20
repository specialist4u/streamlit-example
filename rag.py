import streamlit as st
import openai
import pypdf 
import os
import streamlit as st
from llama_index import (
    GPTVectorStoreIndex,
    SimpleDirectoryReader,
    ServiceContext,
    StorageContext,
    LLMPredictor,
    VectorStoreIndex,
    load_index_from_storage,
)
from langchain.chat_models import ChatOpenAI

openai.api_key = "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" #st.secrets.openai_key

# @st.cache_resource(show_spinner=False)
# def load_rag():
#     with st.spinner(text="Loading index, memory and logic. Hang tight! This should take 1-2 minutes."):
#         reader = SimpleDirectoryReader(input_dir="./data", recursive=True)
#         docs = reader.load_data()
#         service_context = ServiceContext.from_defaults(llm=OpenAI(model="gpt-3.5-turbo-16k", temperature=0.5, system_prompt="You are a very enthusiastic Appex-Now representative who loves to help people! Given the following sections from the Appex-Now documentation, answer the question using only that information, outputted in markdown format. If you are unsure and the answer is not explicitly written in the documentation, say 'Sorry, but you must ask the right question.'"))
#         index = VectorStoreIndex.from_documents(docs, service_context=service_context)
        
#         return index

os.environ["OPENAI_API_KEY"] = "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"



index_name = "./saved_index"
documents_folder = "./documents"


@st.cache_resource
def initialize_index(index_name="./saved_index", documents_folder="./data"):
    llm_predictor = LLMPredictor(
        llm=ChatOpenAI(model_name="gpt-3.5-turbo-16k", temperature=0,openai_api_key="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"),system_prompt="You are a very enthusiastic Appex-Now representative who loves to help people! Given the following sections from the Appex-Now documentation, answer the question using only that information, outputted in markdown format. If you are unsure and the answer is not explicitly written in the documentation, say 'Sorry, but you must ask the right question.'"
    )
    service_context = ServiceContext.from_defaults(llm_predictor=llm_predictor)
    if os.path.exists(index_name):
        index = load_index_from_storage(
            StorageContext.from_defaults(persist_dir=index_name),
            service_context=service_context,
        )
    else:
        documents = SimpleDirectoryReader(documents_folder).load_data()
        index = VectorStoreIndex.from_documents(
            documents, service_context=service_context
        )
        index.storage_context.persist(persist_dir=index_name)

    return index


@st.cache_data(max_entries=200, persist=True)
def query_index(_index, query_text):
    if _index is None:
        return "Please initialize the index!"
    response = _index.as_chat_engine(chat_mode="condense_question", verbose=True).chat(query_text)
    return str(response)