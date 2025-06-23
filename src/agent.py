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
        try:
            agente_escolhido = call_ai.decidir_agente(pergunta)
            print(f"🤖 Usando agente: {agente_escolhido.upper()}")
            print("\n=== TESTE COM AGENT CUSTOMIZADO ===")
            prompt_template = ChatPromptTemplate.from_template(new_prompt)

            if agente_escolhido == 'cabecalho':
                resultado = agents.agent_cabecalho.invoke({"input": pergunta})
            else:
                resultado = agents.agent_itens.invoke({"input": pergunta})

            resultado_texto = None
            if isinstance(resultado, dict):
                if 'output' in resultado and resultado['output']:
                    resultado_texto = resultado['output']
                elif 'final_answer' in resultado and resultado['final_answer']:
                    resultado_texto = resultado['final_answer']
                else:
                    steps = resultado.get('intermediate_steps', [])
                    if steps:
                        resultado_texto = str(steps[-1])
                    else:
                        resultado_texto = str(resultado)
            else:
                resultado_texto = str(resultado)

            final_prompt = prompt_template.format_messages(question=f"{pergunta}: Resultado: {resultado_texto}")
            final_response = llm.stream(final_prompt)
            return final_response

        except Exception as e:
            print(f"Erro na análise: {str(e)}")
            if hasattr(e, 'args') and e.args:
                msg = str(e.args[0])
                if 'Final Answer:' in msg:
                    resposta = msg.split('Final Answer:')[-1].strip()
                    return iter([f"Resposta extraída apesar do erro: {resposta}"])
            return iter([f"Desculpe, ocorreu um erro ao processar sua pergunta: {str(e)}. Tente reformular sua pergunta."])

