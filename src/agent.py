import pandas as pd
from src.class_agents import agents, llm
from dotenv import load_dotenv
import os
import zipfile
from langchain_core.prompts import ChatPromptTemplate
from src.prompt import new_prompt
import zipfile
from src.dataframes import df_cabecalho, df_itens


# Forma de carregar as chaves do arquivo .env(Criado para ocultar chaves importantes)
load_dotenv()


# DIAGNÓSTICO DOS DADOS
print("=== DIAGNÓSTICO DOS DADOS ===")
print(f"Shape do cabeçalho: {df_cabecalho.shape}")
print(f"Shape dos itens: {df_itens.shape}")
print("\nColunas do cabeçalho:")
print(df_cabecalho.columns.tolist())
print("\nColunas dos itens:")
print(df_itens.columns.tolist())

# Verificar se a coluna de valor existe e seu tipo
if 'VALOR NOTA FISCAL' in df_cabecalho.columns:
    print(f"\nTipo da coluna VALOR NOTA FISCAL: {df_cabecalho['VALOR NOTA FISCAL'].dtype}")
    print(f"Valores nulos: {df_cabecalho['VALOR NOTA FISCAL'].isnull().sum()}")
    print(f"Primeiros valores: {df_cabecalho['VALOR NOTA FISCAL'].head()}")
    print(f"Soma total: R$ {df_cabecalho['VALOR NOTA FISCAL'].sum():,.2f}")
else:
    print("\nColuna 'VALOR NOTA FISCAL' não encontrada!")




class call_ai:
    # print("\n=== TESTE DIRETO DO PANDAS ===")
    # valor_total_pandas = df_cabecalho['VALOR NOTA FISCAL'].sum()
    # print(f"Valor total (Pandas direto): R$ {valor_total_pandas:,.2f}")
    # print(f"Quantidade de registros: {len(df_cabecalho)}")
    
    
    @staticmethod
    def decidir_agente(pergunta):
            #Decide qual agente usar baseado na pergunta
        
        # Palavras-chave para cada agente
        palavras_cabecalho = ['valor total', 'nota fiscal', 'fornecedor', 'data', 'valor da nota', 'total das notas']
        palavras_itens = ['produto', 'item', 'quantidade', 'preço unitário', 'categoria', 'descrição']
        
        pergunta_lower = pergunta.lower()
        
        # Contar matches
        score_cabecalho = sum(1 for palavra in palavras_cabecalho if palavra in pergunta_lower)
        score_itens = sum(1 for palavra in palavras_itens if palavra in pergunta_lower)
        
        if score_cabecalho > score_itens:
            return 'cabecalho'
        elif score_itens > score_cabecalho:
            return 'itens'
        else:
            return 'cabecalho'  

    @staticmethod
    def analisar(pergunta):
        """Função principal que decide e executa"""
        
        agente_escolhido = call_ai.decidir_agente(pergunta)
        print(f"🤖 Usando agente: {agente_escolhido.upper()}")
        print("\n=== TESTE COM AGENT CUSTOMIZADO ===")
        
        prompt_template = ChatPromptTemplate.from_template(new_prompt)

        
      
        if agente_escolhido == 'cabecalho':
            resultado = agents.agent_cabecalho.invoke(pergunta)
            final_prompt = prompt_template.format_messages(question=f"Qual o valor da nota? O valor foi {resultado}")
            final_response = llm.invoke(final_prompt)
        else:
            
            resultado = agents.agent_itens.invoke(pergunta)
            final_prompt = prompt_template.format_messages(question=f"Qual o valor da nota? O valor foi {resultado}")
            final_response = llm.invoke(final_prompt)
        
        print(f"Resultado agent {agente_escolhido}: {final_response.content}")
        return final_response.content


    # perguntas = [
    #     "Qual o valor total das notas",
    #     # "Quantos produtos diferentes existem usando a coluna NCM/SH",
    #     # "Qual o menor e o maior valor das notas",
    #     # "Me mostre os 5 produtos mais caros"
    # ]
    
    # for pergunta in perguntas:
    #     print(f"Pergunta escolhida: {pergunta}")
    #     analisar(pergunta)
    #     print("="*50)

    
    # print("\n=== ANÁLISE COMPARATIVA ===")
    # print(f"Pandas direto: R$ {valor_total_pandas:,.2f}")
    # print(f"Registros totais: {len(df_cabecalho)}")
    # print(f"Primeiros 5 valores: {df_cabecalho['VALOR NOTA FISCAL'].head().tolist()}")
    # print(f"Últimos 5 valores: {df_cabecalho['VALOR NOTA FISCAL'].tail().tolist()}")
    
    # # Verificar se há problema de encoding ou sampling
    # print(f"\nEstatísticas da coluna:")
    # print(f"Média: R$ {df_cabecalho['VALOR NOTA FISCAL'].mean():,.2f}")
    # print(f"Mediana: R$ {df_cabecalho['VALOR NOTA FISCAL'].median():,.2f}")
    # print(f"Mínimo: R$ {df_cabecalho['VALOR NOTA FISCAL'].min():,.2f}")
    # print(f"Máximo: R$ {df_cabecalho['VALOR NOTA FISCAL'].max():,.2f}")

