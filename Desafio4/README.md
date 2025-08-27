# Projeto de Processamento VR

Este projeto utiliza N8N para automação e uma aplicação web em Python para processamento de dados de VR (Vale Refeição).

## Pré-requisitos

- N8N instalado e rodando
- Python 3.x
- Credenciais da OpenAI

## Passos para Configuração

1. **Iniciar N8N:**
   - Execute o N8N no seu ambiente local ou servidor.

2. **Adicione o Workflow no N8N:**
   - Importe o arquivo `N8N_ProcessamentoVR.json` no N8N.

3. **Configure o OPENAI Credential:**
   - No N8N, configure as credenciais da OpenAI para integração com IA.

4. **Iniciar app.py e Abra o Site:**
   - Navegue para a pasta `web/`.
   - Execute `python app.py`.
   - Abra o navegador e acesse o site local (geralmente http://localhost:5000).

5. **Realize o Upload de Todos os Arquivos Mencionados em example_required_files:**
   - No site, faça upload dos seguintes arquivos:
     - ADMISSÃO ABRIL.xlsx
     - AFASTAMENTOS.xlsx
     - APRENDIZ.xlsx
     - ATIVOS.xlsx
     - Base dias uteis.xlsx
     - Base sindicato x valor.xlsx
     - DESLIGADOS.xlsx
     - ESTÁGIO.xlsx
     - EXTERIOR.xlsx
     - FÉRIAS.xlsx
     - VR MENSAL 05.2025.xlsx

## Uso

Após o upload, o sistema processará os dados e gerará os resultados na pasta `output/`.
