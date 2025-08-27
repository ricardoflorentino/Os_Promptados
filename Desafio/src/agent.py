from src.class_agents import agents, llm
from langchain_core.prompts import ChatPromptTemplate
from src.prompt import new_prompt


class call_ai:
    
    @staticmethod
    def decidir_agente(pergunta):
            #Decide qual agente usar baseado na pergunta
        
        # Palavras-chave para cada agente
        palavras_cabecalho = ['valor total', 'nota fiscal', 'fornecedor', 'data', 'valor da nota', 'total das notas']
        palavras_itens = ['produto', 'item', 'quantidade', 'preço unitário', 'categoria', 'descrição', 'itens']
        
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
            final_prompt = prompt_template.format_messages(question=f"{pergunta}: Resultado: {resultado}")
            final_response = llm.stream(final_prompt)
        else:
            resultado = agents.agent_itens.invoke(pergunta)
            final_prompt = prompt_template.format_messages(question=f"Qual o valor da nota? O valor foi {resultado}")
            final_response = llm.stream(final_prompt)
        
        return final_response

