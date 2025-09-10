import os
import pandas as pd
from flask import current_app as app

def run_validation(INPUT_DIR, OUTPUT_DIR, base_csv_path=None):
    """
    Realiza validações na base_unificada.csv e remove profissionais conforme regras:
    - Cargos: diretores, estagiários, aprendizes
    - Situação: afastados em geral (ex: licença maternidade)
    - Profissionais que atuam no exterior
    - Trata datas inconsistentes ou quebradas
    - Preenche campos faltantes
    - Corrige férias mal preenchidas
    - Aplica corretamente feriados estaduais e municipais

    Agora aceita um caminho opcional `base_csv_path` que, se fornecido, será usado
    como arquivo base a ser validado (ao invés de procurar em OUTPUT_DIR).

    Retorna um dict: { 'success': bool, 'message': str, 'output_path': str or None }
    """
    try:
        # Carrega a base unificada
        if base_csv_path:
            base_path = base_csv_path
        else:
            base_path = os.path.join(OUTPUT_DIR, 'base_unificada.csv')
        df = pd.read_csv(base_path, sep=';', encoding='utf-8-sig')
        app.logger.info(f"Base carregada: {df.shape[0]} linhas.")

        # Carrega as bases auxiliares, se existirem
        sindicato_path = os.path.join(INPUT_DIR, 'Base sindicato x valor.xlsx')
        dias_uteis_path = os.path.join(INPUT_DIR, 'Base dias uteis.xlsx')
        df_sindicato = pd.read_excel(sindicato_path) if os.path.exists(sindicato_path) else pd.DataFrame()
        df_dias_uteis = pd.read_excel(dias_uteis_path) if os.path.exists(dias_uteis_path) else pd.DataFrame()

        # Normaliza colunas para evitar problemas de maiúsculas/minúsculas
        df.columns = df.columns.str.strip()
        if 'Cargo' in df.columns:
            cargos = df['Cargo'].str.lower().fillna('')
        else:
            cargos = pd.Series([''] * len(df))

        # Critérios de exclusão
        cargos_excluir = ['diretor', 'estagiário', 'estagiario', 'aprendiz']
        mask_cargo = cargos.str.contains('|'.join(cargos_excluir), na=False)
        app.logger.info(f"Removendo por cargo: {mask_cargo.sum()} linhas.")

        # Situação de afastamento
        situacao_col = next((col for col in df.columns if 'situacao' in col.lower()), None)
        if situacao_col:
            afastados = df[situacao_col].str.lower().fillna('').str.contains('afast', na=False) | \
                        df[situacao_col].str.lower().fillna('').str.contains('licen', na=False)
            app.logger.info(f"Removendo por afastamento/licença: {afastados.sum()} linhas.")
        else:
            afastados = pd.Series([False] * len(df))
            app.logger.info("Coluna de situação não encontrada.")

        # Profissionais no exterior
        exterior_mask = cargos.str.contains('exterior', na=False)
        app.logger.info(f"Removendo por atuação no exterior: {exterior_mask.sum()} linhas.")

        # Combina todas as máscaras de exclusão
        excluir = mask_cargo | afastados | exterior_mask
        total_removidos = excluir.sum()
        app.logger.info(f"Total de linhas removidas: {total_removidos}")

        # Para log detalhado, mostra as matrículas removidas
        matriculas_removidas = df.loc[excluir, 'MATRICULA'].tolist() if 'MATRICULA' in df.columns else []
        if matriculas_removidas:
            app.logger.debug(f"Matrículas removidas: {matriculas_removidas}")

        # Remove linhas que atendem a qualquer critério de exclusão
        df_validado = df[~excluir].copy()
        app.logger.info(f"Base após exclusões: {df_validado.shape[0]} linhas.")

        # --- Tratamento de datas inconsistentes ou quebradas ---
        date_cols = [col for col in df_validado.columns if 'data' in col.lower() or 'admiss' in col.lower()]
        for col in date_cols:
            before = df_validado[col].copy()
            # Tenta converter usando o formato ISO primeiro, depois tenta com dayfirst=True
            try:
                df_validado[col] = pd.to_datetime(df_validado[col], errors='coerce', format='%Y-%m-%d')
            except Exception:
                df_validado[col] = pd.to_datetime(df_validado[col], errors='coerce', dayfirst=True)
            n_invalid = df_validado[col].isna().sum()
            app.logger.info(f"Coluna {col}: {n_invalid} datas inválidas convertidas para NaT.")
            # Log exemplos de datas quebradas
            broken = before[before.apply(lambda x: not pd.to_datetime(x, errors='coerce', dayfirst=True, exact=False))]
            if not broken.empty:
                app.logger.debug(f"Exemplos de datas quebradas em {col}: {broken.head(5).tolist()}")

        # --- Preenchimento de campos faltantes ---
        missing_cols = df_validado.columns[df_validado.isnull().any()].tolist()
        for col in missing_cols:
            n_missing = df_validado[col].isnull().sum()
            if pd.api.types.is_datetime64_any_dtype(df_validado[col]):
                df_validado[col] = df_validado[col].fillna(pd.NaT)
            elif df_validado[col].dtype == 'O':
                df_validado[col] = df_validado[col].fillna('NÃO INFORMADO')
            else:
                df_validado[col] = df_validado[col].fillna(0)
            app.logger.info(f"Coluna {col}: {n_missing} valores faltantes preenchidos.")

        # --- Correção de férias mal preenchidas ---
        if 'DIAS DE FÉRIAS' in df_validado.columns:
            invalid_ferias = (df_validado['DIAS DE FÉRIAS'].isnull()) | (df_validado['DIAS DE FÉRIAS'] < 0) | (df_validado['DIAS DE FÉRIAS'] > 60)
            n_invalid_ferias = invalid_ferias.sum()
            df_validado.loc[invalid_ferias, 'DIAS DE FÉRIAS'] = 0
            app.logger.info(f"Corrigidos {n_invalid_ferias} registros de férias mal preenchidas.")

        # --- Aplicação de feriados estaduais e municipais ---
        if not df_dias_uteis.empty and 'Dias Úteis' in df_dias_uteis.columns:
            if 'UF' in df_validado.columns and 'Município' in df_validado.columns:
                df_validado = pd.merge(
                    df_validado,
                    df_dias_uteis[['UF', 'Município', 'Dias Úteis', 'Feriados']],
                    on=['UF', 'Município'],
                    how='left',
                    suffixes=('', '_FERIADOS')
                )
                app.logger.info("Feriados estaduais e municipais aplicados via merge com base de dias úteis.")
            else:
                app.logger.warning("Colunas 'UF' e/ou 'Município' não encontradas para aplicar feriados.")

        # Salva resultado validado
        valid_output = os.path.join(OUTPUT_DIR, 'base_unificada_validada.csv')
        df_validado.to_csv(valid_output, index=False, sep=';', encoding='utf-8-sig')

        return { 'success': True, 'message': f"Validação concluída. Arquivo salvo em: {valid_output} (Total removidos: {total_removidos})", 'output_path': valid_output }
    except Exception as e:
        app.logger.error(f"Erro na validação: {e}", exc_info=True)
        return { 'success': False, 'message': f"Erro na validação: {e}", 'output_path': None }