import streamlit as st
from src.agent import df_cabecalho, df_itens
def main():
    st.title("Agente de IA para Análises de notas fiscais - Os Promptados")

    st.write("### Preview dos Datasets")
    cabecalho = st.write(df_cabecalho)
    itens = st.write(df_itens)
    
