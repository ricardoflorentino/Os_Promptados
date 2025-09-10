from flask import Flask, render_template, send_file, request
import pandas as pd
import os
import logging
import requests
import time
from validation import run_validation
from calculation import calcular_dias_uteis_por_colaborador, aplicar_regra_desligamento, calcular_valor_total_vr, gerar_planilha_final
from io import BytesIO

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Define the paths for input and output files
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_DIR = os.path.join(BASE_DIR, 'files')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
OUTPUT_FILENAME = os.path.join(OUTPUT_DIR, 'base_unificada.csv')
OUTPUT_VALID_FILENAME = os.path.join(OUTPUT_DIR, 'base_unificada_validada.csv')

# Ensure the output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

def process_files():
    """
    Unifica as planilhas recebidas em uma única, mantendo apenas os campos desejados.
    """
    app.logger.info("Iniciando o processamento dos arquivos...")
    try:
        def read_and_prepare(path, col_map):
            app.logger.info(f"Lendo o arquivo: {path}")
            df = pd.read_excel(path)
            df.columns = df.columns.str.strip()
            # Remove colunas Unnamed
            df = df.loc[:, ~df.columns.str.startswith('Unnamed')]
            df = df.rename(columns=col_map)
            # Seleciona apenas as colunas de interesse que existem no arquivo
            cols = [c for c in col_map.values() if c in df.columns]
            # Remove duplicatas de MATRICULA se houver
            df = df.loc[:,~df.columns.duplicated()]
            return df[cols]

        col_map = {
            'MATRICULA': 'MATRICULA',
            'Matricula': 'MATRICULA',
            'Admissão': 'Admissão',
            'ADMISSÃO': 'Admissão',
            'Cargo': 'Cargo',
            'TITULO DO CARGO': 'Cargo',  # Padroniza para 'Cargo'
            'DESC. SITUACAO': 'DESC. SITUACAO',
            'DIAS DE FÉRIAS': 'DIAS DE FÉRIAS',
            'Dias de férias': 'DIAS DE FÉRIAS',
            'Sindicato': 'Sindicato',
            'DATA DEMISSÃO': 'DATA DEMISSÃO',
            'Comunicado de desligamento': 'COMUNICADO DE DESLIGAMENTO',
            'COMUNICADO DE DESLIGAMENTO': 'COMUNICADO DE DESLIGAMENTO'
        }

        ativos_path = os.path.join(INPUT_DIR, 'ATIVOS.xlsx')
        ferias_path = os.path.join(INPUT_DIR, 'FÉRIAS.xlsx')
        desligados_path = os.path.join(INPUT_DIR, 'DESLIGADOS.xlsx')
        admissao_path = os.path.join(INPUT_DIR, 'ADMISSÃO ABRIL.xlsx')

        df_ativos = read_and_prepare(ativos_path, col_map)
        df_ferias = read_and_prepare(ferias_path, col_map)
        df_desligados = read_and_prepare(desligados_path, col_map)
        df_admissao = read_and_prepare(admissao_path, col_map)

        # Remove duplicatas de MATRICULA antes do merge
        for df in [df_ativos, df_ferias, df_desligados, df_admissao]:
            if df.columns.duplicated().any():
                df = df.loc[:,~df.columns.duplicated()]

        # Faz o merge sequencialmente, sempre removendo duplicatas de MATRICULA
        dfs = [df_ativos, df_ferias, df_desligados, df_admissao]
        merged_df = dfs[0]
        for df in dfs[1:]:
            # Garante que só existe uma coluna 'MATRICULA' em cada DataFrame antes do merge
            if merged_df.columns.duplicated().any():
                merged_df = merged_df.loc[:, ~merged_df.columns.duplicated()]
            if df.columns.duplicated().any():
                df = df.loc[:, ~df.columns.duplicated()]
            # Remove colunas extras 'MATRICULA' se houver
            merged_df = merged_df.loc[:, ~((merged_df.columns == 'MATRICULA') & (merged_df.columns.duplicated(keep='first')))]
            df = df.loc[:, ~((df.columns == 'MATRICULA') & (df.columns.duplicated(keep='first')))]
            merged_df = pd.merge(merged_df, df, on='MATRICULA', how='outer', suffixes=('', '_dup'))
            # Remove colunas duplicadas de MATRICULA se aparecerem após o merge
            matricula_cols = [col for col in merged_df.columns if col == 'MATRICULA']
            if len(matricula_cols) > 1:
                # Mantém apenas a primeira ocorrência
                first = True
                cols_to_keep = []
                for col in merged_df.columns:
                    if col == 'MATRICULA':
                        if first:
                            cols_to_keep.append(True)
                            first = False
                        else:
                            cols_to_keep.append(False)
                    else:
                        cols_to_keep.append(True)
                merged_df = merged_df.loc[:, cols_to_keep]

        # Coalesce de colunas duplicadas ("*_dup"): preenche valores faltantes e remove sufixos
        dup_cols = [c for c in merged_df.columns if c.endswith('_dup')]
        for dup_col in dup_cols:
            base_col = dup_col[:-4]
            if base_col in merged_df.columns:
                # Preenche valores faltantes do base_col com os do dup_col
                merged_df[base_col] = merged_df[base_col].combine_first(merged_df[dup_col])
                merged_df.drop(columns=[dup_col], inplace=True)
            else:
                # Se a coluna base não existe, apenas renomeia
                merged_df.rename(columns={dup_col: base_col}, inplace=True)

        campos = [
            'MATRICULA', 'Admissão', 'Cargo', 'DESC. SITUACAO',
            'DIAS DE FÉRIAS', 'Sindicato', 'DATA DEMISSÃO', 'COMUNICADO DE DESLIGAMENTO'
        ]
        # Remove colunas duplicadas de 'Cargo' se existirem
        cargo_cols = [col for col in merged_df.columns if col.lower() == 'cargo']
        if len(cargo_cols) > 1:
            # Mantém apenas a primeira ocorrência
            merged_df = merged_df.loc[:, ~((merged_df.columns.str.lower() == 'cargo') & (merged_df.columns.duplicated(keep='first')))]

        merged_df = merged_df[campos]

        # Normaliza/formatta a coluna de Admissão para dd/mm/aaaa se existir
        if 'Admissão' in merged_df.columns:
            try:
                adm_parsed = pd.to_datetime(merged_df['Admissão'], errors='coerce', dayfirst=True)
                merged_df['Admissão'] = adm_parsed.dt.strftime('%d/%m/%Y')
                # Mantém vazio onde não há data
                merged_df['Admissão'] = merged_df['Admissão'].where(~adm_parsed.isna(), '')
            except Exception:
                # Se não for possível formatar, mantém como está
                pass

        app.logger.info(f"Salvando arquivo unificado em: {OUTPUT_FILENAME}")
        merged_df.to_csv(OUTPUT_FILENAME, index=False, sep=';', encoding='utf-8-sig')

        app.logger.info("Processamento concluído com sucesso.")
        return f"Arquivo '{os.path.basename(OUTPUT_FILENAME)}' gerado com sucesso em '{OUTPUT_DIR}'"
    except FileNotFoundError as e:
        app.logger.error(f"Erro de arquivo não encontrado: {e.filename}")
        return f"Erro: Arquivo não encontrado - {e.filename}"
    except Exception as e:
        app.logger.error(f"Ocorreu um erro inesperado: {e}", exc_info=True)
        return f"Ocorreu um erro inesperado: {e}"

@app.route('/', methods=['GET', 'POST'])
def index():
    """Renders the main page and handles file processing on POST."""
    message = None
    if request.method == 'POST':
        expected_filenames = [
            'ATIVOS.xlsx',
            'FÉRIAS.xlsx',
            'DESLIGADOS.xlsx',
            'ADMISSÃO ABRIL.xlsx',
            'Base dias uteis.xlsx',              
            'Base sindicato x valor.xlsx',
            'AFASTAMENTOS.xlsx',
            'APRENDIZ.xlsx',
            'ESTÁGIO.xlsx',
            'EXTERIOR.xlsx',
            'VR MENSAL 05.2025.xlsx',
        ]
        files = request.files.getlist('planilhas[]')
        saved_any = False
        for file in files:
            if file and file.filename in expected_filenames:
                save_path = os.path.join(INPUT_DIR, file.filename)
                file.save(save_path)
                saved_any = True
        # 1) Gera a base_unificada.csv primeiro
        if saved_any:
            message = process_files()

            # 2) Dispara o webhook (n8n) que irá chamar a API /calculation
            try:
                # Read the generated file and send it via the webhook
                if os.path.exists(OUTPUT_FILENAME):
                    response = requests.post(
                        "http://localhost:5678/webhook/038b55dc-fc6d-4253-8b24-acdf648216eb",
                        timeout=120
                    )
                    if response.status_code == 200:
                        app.logger.info("Webhook chamado com sucesso.")
                        target_prefix = 'RESULTADO_VR_MENSAL_'
                        try:
                            candidatos = [
                                os.path.join(OUTPUT_DIR, f)
                                for f in os.listdir(OUTPUT_DIR)
                                if f.startswith(target_prefix) and f.lower().endswith('.csv')
                            ]
                        except FileNotFoundError:
                            return "Arquivo não encontrado.", 404
                        if candidatos:
                            # pega o mais recente
                            candidatos.sort(key=lambda p: os.path.getmtime(p), reverse=True)
                            result_path = candidatos[0]
                            return send_file(result_path, as_attachment=True)
                        else:
                            return "Arquivo RESULTADO_VR_MENSAL_*.csv não encontrado.", 404
                    else:
                        app.logger.error(f"Webhook retornou status {response.status_code}")
                else:
                    app.logger.error("Arquivo base_unificada.csv não encontrado para envio via webhook.")
            except Exception as e:
                app.logger.error(f"Erro ao chamar webhook: {e}")

            # 3) Aguarda a geração do arquivo RESULTADO_VR_MENSAL_*.csv e faz o download
            start_time = time.time()
            timeout_s = int(os.environ.get('RESULT_TIMEOUT_SECONDS', '300'))
            target_prefix = 'RESULTADO_VR_MENSAL_'
            result_path = None
            while time.time() - start_time < timeout_s:
                try:
                    candidatos = [
                        os.path.join(OUTPUT_DIR, f)
                        for f in os.listdir(OUTPUT_DIR)
                        if f.startswith(target_prefix) and f.lower().endswith('.csv')
                    ]
                except FileNotFoundError:
                    candidatos = []
                if candidatos:
                    # pega o mais recente e, de preferência, gerado após o início da espera
                    candidatos.sort(key=lambda p: os.path.getmtime(p), reverse=True)
                    latest = candidatos[0]
                    if os.path.getmtime(latest) >= start_time - 1:  # tolerância de 1s
                        result_path = latest
                        break
                time.sleep(1)

            if result_path and os.path.exists(result_path):
                app.logger.info(f"Arquivo final encontrado: {result_path}. Enviando para download...")
                return send_file(result_path, as_attachment=True)
            else:
                message = (
                    (message + ' | ') if message else ''
                ) + "Tempo de espera esgotado para geração do RESULTADO_VR_MENSAL. Tente novamente."
    return render_template('index.html', message=message)


@app.route('/download')
def download_file():
    """Allows the user to download the generated RESULTADO_VR_MENSAL_*.csv file."""
    target_prefix = 'RESULTADO_VR_MENSAL_'
    try:
        candidatos = [
            os.path.join(OUTPUT_DIR, f)
            for f in os.listdir(OUTPUT_DIR)
            if f.startswith(target_prefix) and f.lower().endswith('.csv')
        ]
    except FileNotFoundError:
        return "Arquivo não encontrado.", 404
    if candidatos:
        # pega o mais recente
        candidatos.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        result_path = candidatos[0]
        return send_file(result_path, as_attachment=True)
    else:
        return "Arquivo RESULTADO_VR_MENSAL_*.csv não encontrado.", 404

@app.route('/validation', methods=['GET','POST'])
def validation():
    """Endpoint que valida o arquivo base_unificada.csv gerado.

    - POST: executa a validação no OUTPUT_FILENAME e retorna o arquivo validado para download.
    - GET: retorna instruções simples.
    """
    if request.method == 'GET':
        return "Use POST para executar validação no arquivo base_unificada.csv.", 200

    # Verifica se o OUTPUT_FILENAME existe
    if not os.path.exists(OUTPUT_FILENAME):
        return {"status": "error", "message": "Arquivo base_unificada.csv não encontrado."}, 400

    # Executa validação apontando para o OUTPUT_FILENAME
    result = run_validation(INPUT_DIR, OUTPUT_DIR, base_csv_path=OUTPUT_FILENAME)
    if isinstance(result, dict):
        if result.get('success'):
            output_path = result.get('output_path')
            if output_path and os.path.exists(output_path):
                return {"status": "success", "message": str(result)}, 200
            else:
                return {"status": "error", "message": "Validação concluída, mas arquivo de saída não foi encontrado.", "details": result.get('message')}, 500
        else:
            return {"status": "error", "message": result.get('message')}, 400
    else:
        # Compatibilidade com implementações anteriores que retornavam string
        return {"status": "success", "message": str(result)}, 200


@app.route('/calculation', methods=['POST'])
def calculation():
    """
    Endpoint HTTP para calcular e adicionar o campo de dias úteis no CSV.
    Não espera arquivo no POST; usa o arquivo presente no diretório de saída.

    Prioridade de arquivos de entrada:
    1. OUTPUT_VALID_FILENAME (base_unificada_validada.csv)
    2. OUTPUT_FILENAME (base_unificada.csv) — fallback

    NÃO retorna o arquivo final como anexo; retorna apenas um JSON com status em caso de sucesso.
    """
    try:
        # Não espera arquivo enviado via POST: escolhe arquivo no diretório de output
        if os.path.exists(OUTPUT_VALID_FILENAME):
            output_csv = OUTPUT_VALID_FILENAME
            app.logger.info(f"Usando arquivo validado: {output_csv}")
        elif os.path.exists(OUTPUT_FILENAME):
            output_csv = OUTPUT_FILENAME
            app.logger.warning(f"Arquivo validado não encontrado. Usando fallback: {output_csv}")
        else:
            app.logger.error("Nenhum arquivo de entrada encontrado para execução dos cálculos.")
            return {"status": "error", "message": "Nenhum arquivo de entrada encontrado. Certifique-se que 'base_unificada_validada.csv' ou 'base_unificada.csv' exista em output/."}, 400

        # Executa pipeline de cálculos usando o arquivo escolhido
        app.logger.info(f"Iniciando pipeline de cálculos usando: {output_csv}")
        calcular_dias_uteis_por_colaborador(INPUT_DIR, output_csv)
        aplicar_regra_desligamento(INPUT_DIR, output_csv)
        calcular_valor_total_vr(INPUT_DIR, output_csv)
        final_path = gerar_planilha_final(INPUT_DIR, output_csv)

        if final_path and os.path.exists(final_path):
            app.logger.info(f"Processamento concluído. Arquivo final gerado em: {final_path}")
        else:
            app.logger.warning("Processamento concluído, mas não foi possível localizar o arquivo RESULTADO_VR_MENSAL_*.csv gerado.")

        # Retorna apenas indicação de sucesso (HTTP 200) sem enviar o arquivo
        return {"status": "success", "message": "Processamento concluído."}, 200
    except Exception as e:
        app.logger.error(f"Erro no cálculo de dias úteis: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}, 500

if __name__ == '__main__':
    app.run(debug=True)
