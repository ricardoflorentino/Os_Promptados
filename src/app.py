import streamlit as st
from src.agent import df_cabecalho, df_itens
from src.agent import call_ai
def main():
    st.title("Agente de IA para Análises de notas fiscais - Os Promptados")
    st.write("## **Preview dos Datasets 📚**")

    col1, col2 = col1, col2 = st.columns([3, 3])  # Porcentagens relativas das larguras
  

    with col1:
        st.write("#### Cabeçalho")
        st.write(df_cabecalho)

    with col2:
        st.write("#### Itens")
        st.write(df_itens)

    st.write("## Faça uma pergunta sobre as notas: ")
    question = st.text_input(placeholder="Faça uma pergunta sobre as notas fiscais...", label="Pergunta")
    if st.button("Fazer pergunta"):
        st.write("### Resposta")
        answer = call_ai.analisar(question)
        st.markdown(answer)