import streamlit as st
from src.dataframes import df_cabecalho, df_itens
from src.agent import call_ai
from langchain_core.messages import HumanMessage, AIMessage

def main():
    st.set_page_config(page_title="ChatBot para Nfes", page_icon="🤖")

    st.title("Agente de IA para Análises de notas fiscais - Os Promptados")
    st.write("## **Preview dos Datasets 📚**")

    col1, col2 = st.columns([3, 3])  
    no_key_acess_cabecalho = df_cabecalho.drop('CHAVE DE ACESSO', axis=1)
    no_key_acess_itens = df_itens.drop('CHAVE DE ACESSO', axis=1)

    with col1:
        st.write("#### Cabeçalho")
        st.write(no_key_acess_cabecalho)

    with col2:
        st.write("#### Itens")
        st.write(no_key_acess_itens)

    st.write("## Converse com o agente sobre as notas fiscais:")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if question := st.chat_input("Faça uma pergunta sobre as notas fiscais..."):
        st.session_state.messages.append({"role": "user", "content": question})
        
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("🤔 Analisando sua pergunta"):
                answer = call_ai.analisar(question)
            resposta = st.write_stream(answer)
            st.session_state.messages.append({"role": "assistant", "content": resposta})
