import pandas as pd
import os
import re
import unicodedata

# Helpers para normalização de texto e mapeamento UF->Estado (sem acentos)
def _normalize_text(s: str) -> str:
    if s is None:
        return ''
    s = str(s).strip().upper()
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(ch for ch in s if not unicodedata.combining(ch))
    # normaliza espaços múltiplos
    s = re.sub(r"\s+", " ", s)
    return s

UF_TO_ESTADO = {
    'AC': 'ACRE',
    'AL': 'ALAGOAS',
    'AP': 'AMAPA',
    'AM': 'AMAZONAS',
    'BA': 'BAHIA',
    'CE': 'CEARA',
    'DF': 'DISTRITO FEDERAL',
    'ES': 'ESPIRITO SANTO',
    'GO': 'GOIAS',
    'MA': 'MARANHAO',
    'MT': 'MATO GROSSO',
    'MS': 'MATO GROSSO DO SUL',
    'MG': 'MINAS GERAIS',
    'PA': 'PARA',
    'PB': 'PARAIBA',
    'PR': 'PARANA',
    'PE': 'PERNAMBUCO',
    'PI': 'PIAUI',
    'RJ': 'RIO DE JANEIRO',
    'RN': 'RIO GRANDE DO NORTE',
    'RS': 'RIO GRANDE DO SUL',
    'RO': 'RONDONIA',
    'RR': 'RORAIMA',
    'SC': 'SANTA CATARINA',
    'SP': 'SAO PAULO',
    'SE': 'SERGIPE',
    'TO': 'TOCANTINS',
}

def _build_valor_mapping(df_valores: pd.DataFrame):
    """Cria mapa de chave->valor usando colunas de sindicato/estado, com aliases:
    - Normaliza texto (sem acentos)
    - Adiciona alias de UF para nomes de estados quando aplicável
    Retorna duas dicts: (map_raw_upper, map_norm)
    """
    cols = [str(c).strip().upper() for c in df_valores.columns]
    df = df_valores.copy()
    df.columns = cols
    key_candidates = ['SINDICATO', 'SINDICADO', 'ESTADO']
    val_candidates = ['VALOR', 'VALOR VR', 'VALORVR']
    col_key = next((c for c in df.columns if c in key_candidates), None)
    col_val = next((c for c in df.columns if c in val_candidates), None)
    if not col_key or not col_val:
        raise ValueError("Colunas de sindicato/estado ou valor não encontradas em 'Base sindicato x valor.xlsx'.")

    def _parse_valor(v):
        if pd.isna(v):
            return 0.0
        s = str(v)
        s = s.replace('R$', '').replace('\xa0', '').strip()
        s = s.replace('.', '').replace(',', '.')
        s = re.sub('[^0-9.-]', '', s)
        try:
            val = float(s) if s not in ['', '-', None] else 0.0
            # Ajuste de escala: alguns arquivos vêm com um zero a mais (ex.: 350 em vez de 35,00)
            # Normaliza para uma faixa plausível de VR/dia (10 a 100)
            if val > 0:
                for scale in (1, 10, 100, 1000):
                    cand = val / scale
                    if 10 <= cand <= 100:
                        val = cand
                        break
            return val
        except Exception:
            return 0.0

    map_raw = {}
    map_norm = {}

    # Primeiro, popula com a chave original e a versão normalizada
    for _, r in df.iterrows():
        k_raw = str(r[col_key]).strip().upper() if not pd.isna(r[col_key]) else ''
        if not k_raw:
            continue
        v = _parse_valor(r[col_val])
        map_raw[k_raw] = v
        map_norm[_normalize_text(k_raw)] = v

    # Depois, adiciona aliases de UF para chaves que são nomes de estados
    # Detecta chaves normalizadas que coincidem com algum nome de estado
    estado_to_uf = {v: k for k, v in UF_TO_ESTADO.items()}
    for k_norm, v in list(map_norm.items()):
        if k_norm in estado_to_uf:
            uf = estado_to_uf[k_norm]
            map_raw[uf] = v
            map_norm[_normalize_text(uf)] = v

    return map_raw, map_norm

def calcular_dias_uteis_por_colaborador(input_dir, output_csv):
    """
    Adiciona ao CSV unificado um campo 'DIAS_UTEIS' com a quantidade de dias úteis por colaborador,
    considerando sindicato, férias, afastamentos e data de desligamento.
    """
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("calculation")

    # Carrega o arquivo base_unificada.csv
    base = pd.read_csv(output_csv, sep=';', encoding='utf-8-sig')
    logger.info(f"Arquivo base carregado: {output_csv} ({len(base)} registros)")

    # Carrega as planilhas auxiliares
    dias_uteis = pd.read_excel(os.path.join(input_dir, 'Base dias uteis.xlsx'), header=1)
    logger.info(f"Planilha de dias úteis carregada ({len(dias_uteis)} sindicatos)")
    sindicato_valor = pd.read_excel(os.path.join(input_dir, 'Base sindicato x valor.xlsx'))
    afastamentos = pd.read_excel(os.path.join(input_dir, 'AFASTAMENTOS.xlsx'))
    logger.info(f"Planilha de afastamentos carregada ({len(afastamentos)} registros)")
    ferias = pd.read_excel(os.path.join(input_dir, 'FÉRIAS.xlsx'))
    desligados = pd.read_excel(os.path.join(input_dir, 'DESLIGADOS.xlsx'))

    # Identifica a coluna de sindicato e de dias uteis, independente do nome exato
    col_sindicato = None
    col_dias_uteis = None
    for col in dias_uteis.columns:
        nome = str(col).strip().upper()
        if nome in ['SINDICATO', 'SINDICADO']:
            col_sindicato = col
        if nome.replace(" ", "") in ['DIASUTEIS', 'DIASÚTEIS']:
            col_dias_uteis = col
    if not col_sindicato:
        raise ValueError("Coluna de sindicato não encontrada em 'Base dias uteis.xlsx' (esperado: 'SINDICATO' ou 'SINDICADO')")
    if not col_dias_uteis:
        raise ValueError("Coluna de dias úteis não encontrada em 'Base dias uteis.xlsx' (esperado: 'DIAS UTEIS')")

    sindicato_dias = dias_uteis.set_index(col_sindicato)[col_dias_uteis].to_dict()
    # Cria um set de matrículas afastadas
    matriculas_afastadas = set(afastamentos['MATRICULA'].astype(str))

    logs_modificacoes = []

    def calcular_linha(row):
        # Busca o sindicato na linha, independente do nome da coluna
        sindicato = (
            row.get('Sindicato') or
            row.get('SINDICATO') or
            row.get('sindicato') or
            row.get('SINDICADO')
        )
        if sindicato:
            sindicato = str(sindicato).strip().upper()
        # Padroniza as chaves do dicionário para maiúsculas
        sindicato_dias_padrao = {str(k).strip().upper(): v for k, v in sindicato_dias.items()}
        dias = sindicato_dias_padrao.get(sindicato, 0)
        matricula = str(row.get('MATRICULA'))

        log_msg = f"Matrícula {matricula}: sindicato='{sindicato}' dias_uteis_base={dias}"

        # Subtrai dias de férias
        dias_ferias = ferias.loc[ferias['MATRICULA'] == matricula, 'DIAS DE FÉRIAS'].sum() if 'DIAS DE FÉRIAS' in ferias else 0
        if dias_ferias > 0:
            log_msg += f" | Férias: -{dias_ferias}"

        # Se a matrícula está em afastamentos, considera todos os dias úteis como afastados
        if matricula in matriculas_afastadas:
            dias_afast = dias
            log_msg += f" | Afastamento: -{dias_afast} (afastado)"
        else:
            dias_afast = 0

        # Se houver data de desligamento, ajustar dias úteis proporcionalmente (exemplo simplificado)
        if pd.notnull(row.get('DATA DEMISSÃO')):
            dias_ant = dias
            dias = dias // 2  # Exemplo: reduz pela metade
            log_msg += f" | Desligamento: dias_uteis {dias_ant} -> {dias}"

        resultado = max(dias - dias_ferias - dias_afast, 0)
        log_msg += f" | DIAS_UTEIS final: {resultado}"
        logs_modificacoes.append(log_msg)
        return resultado

    base['DIAS_UTEIS'] = base.apply(calcular_linha, axis=1)

    # Garante que o novo arquivo será base_unificada_calculation.csv
    output_calc = os.path.join(os.path.dirname(output_csv), "base_unificada_calculation.csv")
    base.to_csv(output_calc, sep=';', index=False, encoding='utf-8-sig')
    logger.info(f"Arquivo CSV atualizado salvo em: {output_calc}")

    # Salva os logs em um arquivo txt para consulta
    log_path = os.path.splitext(output_calc)[0] + "_log.txt"
    with open(log_path, "w", encoding="utf-8") as f:
        for log in logs_modificacoes:
            f.write(log + "\n")
    logger.info(f"Log detalhado das modificações salvo em: {log_path}")

    return

def aplicar_regra_desligamento(input_dir, output_csv):
    """
    Aplica a regra de desligamento:
    - Se o comunicado de desligamento for 'OK' até dia 15, não considerar para pagamento (DIAS_UTEIS = 0).
    - Se informado depois do dia 15, a compra deve ser proporcional (DIAS_UTEIS = metade).
    - Só aplica para quem for elegível ao benefício (vide base de tratamento de exclusões).
    """
    import logging
    from datetime import datetime

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("calculation-desligamento")

    # Carrega o arquivo base_unificada_calculation.csv
    base_path = os.path.join(os.path.dirname(output_csv), "base_unificada_calculation.csv")
    base = pd.read_csv(base_path, sep=';', encoding='utf-8-sig')
    logger.info(f"Arquivo base carregado: {base_path} ({len(base)} registros)")

    # Carrega a planilha de desligados
    desligados = pd.read_excel(os.path.join(input_dir, 'DESLIGADOS.xlsx'))  # MATRÍCULA, DATA DEMISSÃO, COMUNICADO DE DESLIGAMENTO
    # Padroniza os nomes das colunas para evitar erro de KeyError
    desligados.columns = [str(col).strip().upper() for col in desligados.columns]

    # Carrega a base de tratamento de exclusões (supondo nome e campo de matrícula)
    exclusoes_path = os.path.join(input_dir, 'base_tratamento_exclusoes.xlsx')
    if os.path.exists(exclusoes_path):
        exclusoes = pd.read_excel(exclusoes_path)
        matriculas_elegiveis = set(exclusoes['MATRICULA'].astype(str))
    else:
        matriculas_elegiveis = set(base['MATRICULA'].astype(str))  # Se não houver, considera todos elegíveis

    logs_desligamento = []

    for idx, row in base.iterrows():
        matricula = str(row['MATRICULA'])
        if matricula not in matriculas_elegiveis:
            logs_desligamento.append(f"Matrícula {matricula}: não elegível ao benefício (exclusão).")
            continue

        desligado = desligados[desligados['MATRICULA'].astype(str) == matricula]
        if desligado.empty:
            continue

        comunicado = str(desligado.iloc[0].get('COMUNICADO DE DESLIGAMENTO', '')).strip().upper()
        data_demissao = desligado.iloc[0].get('DATA DEMISSÃO')
        dias_uteis_atual = row['DIAS_UTEIS']

        if pd.notnull(data_demissao):
            try:
                data_demissao_dt = pd.to_datetime(data_demissao, dayfirst=True, errors='coerce')
            except Exception:
                data_demissao_dt = None
        else:
            data_demissao_dt = None

        if comunicado == 'OK' and data_demissao_dt and data_demissao_dt.day <= 15:
            base.at[idx, 'DIAS_UTEIS'] = 0
            logs_desligamento.append(
                f"Matrícula {matricula}: comunicado OK até dia 15 ({data_demissao_dt.date()}), DIAS_UTEIS=0"
            )
        elif comunicado == 'OK' and data_demissao_dt and data_demissao_dt.day > 15:
            novo_valor = int(dias_uteis_atual // 2)
            base.at[idx, 'DIAS_UTEIS'] = novo_valor
            logs_desligamento.append(
                f"Matrícula {matricula}: comunicado OK após dia 15 ({data_demissao_dt.date()}), DIAS_UTEIS={novo_valor} (proporcional)"
            )
        else:
            logs_desligamento.append(
                f"Matrícula {matricula}: comunicado '{comunicado}' ou data de demissão inválida, DIAS_UTEIS mantido ({dias_uteis_atual})"
            )

    # Salva o novo arquivo
    output_desligamento = os.path.join(os.path.dirname(output_csv), "base_unificada_calculation_desligamento.csv")
    base.to_csv(output_desligamento, sep=';', index=False, encoding='utf-8-sig')
    logger.info(f"Arquivo CSV com regra de desligamento salvo em: {output_desligamento}")

    # Salva os logs em um arquivo txt para consulta
    log_path = os.path.splitext(output_desligamento)[0] + "_log.txt"
    with open(log_path, "w", encoding="utf-8") as f:
        for log in logs_desligamento:
            f.write(log + "\n")
    logger.info(f"Log detalhado das modificações de desligamento salvo em: {log_path}")

    return

def calcular_valor_total_vr(input_dir, output_csv):
    """
    Calcula e adiciona a coluna 'VALOR TOTAL VR' ao CSV, conforme valor do sindicato de cada colaborador.
    """
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("calculation-vr")

    # Carrega o arquivo base_unificada_calculation_desligamento.csv se existir, senão base_unificada_calculation.csv
    base_path = os.path.join(os.path.dirname(output_csv), "base_unificada_calculation_desligamento.csv")
    if not os.path.exists(base_path):
        base_path = os.path.join(os.path.dirname(output_csv), "base_unificada_calculation.csv")
    base = pd.read_csv(base_path, sep=';', encoding='utf-8-sig')
    logger.info(f"Arquivo base carregado: {base_path} ({len(base)} registros)")

    # Carrega a planilha de valor por sindicato
    sindicato_valor_df = pd.read_excel(os.path.join(input_dir, 'Base sindicato x valor.xlsx'))
    map_raw, map_norm = _build_valor_mapping(sindicato_valor_df)
    if not map_raw:
        logger.warning("Mapa de sindicato/estado->valor ficou vazio após leitura de 'Base sindicato x valor.xlsx'.")

    # Calcula o valor total de VR para cada colaborador
    valores = []
    logs_vr = []
    # garantia: mapas prontos (raw e normalizado)

    for idx, row in base.iterrows():
        matricula = row.get('MATRICULA') or row.get('Matricula') or row.get('matricula') or ''
        matricula = str(matricula)
        sindicato = (
            row.get('Sindicato') or
            row.get('SINDICATO') or
            row.get('sindicato') or
            row.get('SINDICADO') or
            ''
        )
        sindicato_raw = str(sindicato).strip().upper()
        sindicato_norm = _normalize_text(sindicato_raw)

        valor_unitario = None
        reason = None

        # 1) tentativa exata pelo nome do sindicato
        if sindicato_raw and sindicato_raw in map_raw:
            valor_unitario = map_raw[sindicato_raw]
            reason = 'match_exact_sindicato'

        # 2) tentativa por coluna de estado/uf na base
        if valor_unitario is None:
            for estado_col in ['ESTADO', 'UF', 'STATE']:
                estado_val = row.get(estado_col)
                if estado_val is not None and not pd.isna(estado_val):
                    estado_key_raw = str(estado_val).strip().upper()
                    estado_key_norm = _normalize_text(estado_key_raw)
                    # Se vier UF, tenta converter para nome de estado
                    lookup_keys = [estado_key_raw, estado_key_norm]
                    if estado_key_raw in UF_TO_ESTADO:
                        nome_estado = UF_TO_ESTADO[estado_key_raw]
                        lookup_keys.extend([nome_estado, _normalize_text(nome_estado)])
                    for lk in lookup_keys:
                        if lk in map_raw:
                            valor_unitario = map_raw[lk]
                            reason = f'match_estado_column:{estado_col}'
                            break
                        if lk in map_norm:
                            valor_unitario = map_norm[lk]
                            reason = f'match_estado_column_norm:{estado_col}'
                            break
                    if valor_unitario is not None:
                        break

        # 3) tentativa por substring (ex.: sindicato string contém nome do estado)
        if valor_unitario is None and sindicato_norm:
            # tenta UF dentro do texto do sindicato (ex.: 'ESTADO DE SP')
            tokens = re.findall(r"\b([A-Z]{2})\b", sindicato_raw)
            for t in tokens:
                if t in UF_TO_ESTADO:
                    nome_estado = UF_TO_ESTADO[t]
                    for lk in [t, _normalize_text(t), nome_estado, _normalize_text(nome_estado)]:
                        if lk in map_raw:
                            valor_unitario = map_raw[lk]
                            reason = f'match_uf_in_sindicato:{t}'
                            break
                        if lk in map_norm:
                            valor_unitario = map_norm[lk]
                            reason = f'match_uf_in_sindicato_norm:{t}'
                            break
                    if valor_unitario is not None:
                        break
            # tenta substring por nome completo (normalizado)
            if valor_unitario is None:
                for k_norm, v in map_norm.items():
                    if k_norm and k_norm in sindicato_norm:
                        valor_unitario = v
                        reason = f'match_substring_norm:{k_norm}'
                        break

        # 4) fallback: não encontrado
        if valor_unitario is None:
            valor_unitario = 0.0
            reason = 'no_match'

        dias_uteis = row.get('DIAS_UTEIS', 0) or 0
        try:
            valor_total = float(valor_unitario) * float(dias_uteis)
        except Exception:
            valor_total = 0.0

        valores.append(valor_total)
        log_line = (f"Matrícula {matricula}: sindicato='{sindicato}', valor_unitario={valor_unitario}, "
                    f"dias_uteis={dias_uteis}, VALOR TOTAL VR={valor_total} (reason={reason})")
        logger.info(log_line)
        logs_vr.append(log_line)

    base['VALOR TOTAL VR'] = valores
    # Salva o novo arquivo
    output_vr = os.path.join(os.path.dirname(output_csv), "base_unificada_calculation_vr.csv")
    base.to_csv(output_vr, sep=';', index=False, encoding='utf-8-sig')
    logger.info(f"Arquivo CSV com valor total de VR salvo em: {output_vr}")

    # Salva também um log detalhado específico para VR
    vr_log_path = os.path.splitext(os.path.join(os.path.dirname(output_csv), "base_unificada_calculation_vr.csv"))[0] + "_log.txt"
    with open(vr_log_path, 'w', encoding='utf-8') as vf:
        for l in logs_vr:
            vf.write(l + '\n')
    logger.info(f"Log detalhado de VR salvo em: {vr_log_path}")
    return

def gerar_planilha_final(input_dir, output_csv, competencia=None):
    """
    Gera a planilha final para envio à operadora com os campos:
    Matricula	Admissão	Sindicato do Colaborador	Competência	Dias	VALOR DIÁRIO VR	TOTAL	Custo empresa	Desconto profissional	OBS GERAL

    - Usa o arquivo com valores de VR gerados (prefere base_unificada_calculation_vr.csv)
    - Calcula VALOR DIÁRIO como TOTAL / Dias quando possível; faz fallback para valor por sindicato
    - Custo empresa = 80% do TOTAL; Desconto profissional = 20% do TOTAL
    """
    import logging
    import math
    from datetime import datetime

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("calculation-final")

    if competencia is None:
        competencia = datetime.now().strftime("%m.%Y")

    # Carrega base de VR
    base_path = os.path.join(os.path.dirname(output_csv), "base_unificada_calculation_vr.csv")
    if not os.path.exists(base_path):
        base_path = os.path.join(os.path.dirname(output_csv), "base_unificada_calculation.csv")
    base = pd.read_csv(base_path, sep=';', encoding='utf-8-sig')
    logger.info(f"Arquivo base carregado para planilha final: {base_path} ({len(base)} registros)")

    # Carrega valores por sindicato (para fallback)
    sindicato_valor_df = pd.read_excel(os.path.join(input_dir, 'Base sindicato x valor.xlsx'))
    map_raw, map_norm = _build_valor_mapping(sindicato_valor_df)

    # Prepara linhas de saída
    out_rows = []
    logs_final = []

    for idx, row in base.iterrows():
        matricula = row.get('MATRICULA') or row.get('Matricula') or row.get('matricula') or ''
        matricula = str(matricula)
        # tenta várias colunas para admissão
        adm_candidates = [
            row.get('Admissão'), row.get('ADMISSÃO'), row.get('ADMISSAO'),
            row.get('DATA ADMISSAO'), row.get('DATA DE ADMISSAO'), row.get('DATA_ADMISSAO'),
            row.get('Data Admissao'), row.get('Data de Admissao')
        ]
        adm = next((v for v in adm_candidates if v is not None and not pd.isna(v) and str(v).strip() != ''), '')
        # Formata data de admissão como dd/mm/aaaa quando possível
        if adm not in ['', None] and not pd.isna(adm):
            try:
                adm_dt = pd.to_datetime(adm, errors='coerce', dayfirst=True)
                if pd.notnull(adm_dt):
                    adm = adm_dt.strftime('%d/%m/%Y')
                else:
                    adm = str(adm)
            except Exception:
                adm = str(adm)
        sindicato = (row.get('Sindicato') or row.get('SINDICATO') or row.get('sindicato') or row.get('SINDICADO') or '')
        sindicato = str(sindicato).strip()
        dias = row.get('DIAS_UTEIS') or row.get('DIAS') or 0
        try:
            dias_n = int(dias) if not pd.isna(dias) else 0
        except Exception:
            try:
                dias_n = int(float(dias))
            except Exception:
                dias_n = 0

        total = row.get('VALOR TOTAL VR') or row.get('VALOR_TOTAL_VR') or row.get('VALOR TOTAL VR ') or 0
        try:
            total_f = float(total) if not pd.isna(total) else 0.0
        except Exception:
            total_f = 0.0

        # Calcula valor diário
        obs_msgs = []
        # Avisos iniciais
        if not sindicato or str(sindicato).strip().lower() in ['nan', '']:
            obs_msgs.append('Sindicato não informado')
        if dias_n == 0:
            obs_msgs.append('Sem dias úteis no período')

        if dias_n > 0:
            valor_diario = total_f / dias_n
            reason = 'calc_from_total'
        else:
            # fallback: tentar obter valor unitário por sindicato/estado com mapas melhorados
            valor_unit = 0.0
            s_key_raw = sindicato.strip().upper()
            s_key_norm = _normalize_text(s_key_raw)
            # tentativas ordenadas
            if s_key_raw in map_raw:
                valor_unit = map_raw[s_key_raw]
                reason = 'fallback_by_sindicato_raw'
            elif s_key_norm in map_norm:
                valor_unit = map_norm[s_key_norm]
                reason = 'fallback_by_sindicato_norm'
            else:
                # tenta UF em colunas conhecidas
                matched = False
                for estado_col in ['ESTADO', 'UF', 'STATE']:
                    estado_val = row.get(estado_col)
                    if estado_val is None or pd.isna(estado_val):
                        continue
                    estado_key_raw = str(estado_val).strip().upper()
                    estado_key_norm = _normalize_text(estado_key_raw)
                    lookup = [estado_key_raw, estado_key_norm]
                    if estado_key_raw in UF_TO_ESTADO:
                        nome_estado = UF_TO_ESTADO[estado_key_raw]
                        lookup.extend([nome_estado, _normalize_text(nome_estado)])
                    for lk in lookup:
                        if lk in map_raw:
                            valor_unit = map_raw[lk]
                            reason = f'fallback_estado_column:{estado_col}'
                            matched = True
                            break
                        if lk in map_norm:
                            valor_unit = map_norm[lk]
                            reason = f'fallback_estado_column_norm:{estado_col}'
                            matched = True
                            break
                    if matched:
                        break
                if not matched:
                    # tenta UF dentro do próprio texto do sindicato
                    tokens = re.findall(r"\b([A-Z]{2})\b", s_key_raw)
                    for t in tokens:
                        if t in UF_TO_ESTADO:
                            nome_estado = UF_TO_ESTADO[t]
                            for lk in [t, _normalize_text(t), nome_estado, _normalize_text(nome_estado)]:
                                if lk in map_raw:
                                    valor_unit = map_raw[lk]
                                    reason = f'fallback_uf_in_sindicato:{t}'
                                    matched = True
                                    break
                                if lk in map_norm:
                                    valor_unit = map_norm[lk]
                                    reason = f'fallback_uf_in_sindicato_norm:{t}'
                                    matched = True
                                    break
                        if matched:
                            break
                if not matched:
                    # por fim substring normalizada
                    for k_norm, v in map_norm.items():
                        if k_norm and k_norm in s_key_norm:
                            valor_unit = v
                            reason = f'fallback_substring_norm:{k_norm}'
                            matched = True
                            break
                if not matched:
                    reason = 'no_valor_found'
            valor_diario = valor_unit
            total_f = valor_diario * dias_n

        # Observações com base no método de cálculo/erros
        if 'reason' in locals():
            if reason == 'no_valor_found':
                obs_msgs.append('Valor unitário do sindicato/estado não encontrado')
            elif reason.startswith('fallback_'):
                # Mensagens mais amigáveis para alguns fallbacks
                if 'estado_column' in reason or 'uf_in_sindicato' in reason:
                    obs_msgs.append('Valor diário obtido por fallback (UF/Estado)')
                elif 'substring' in reason:
                    obs_msgs.append('Valor diário obtido por fallback (substring)')
                else:
                    obs_msgs.append('Valor diário obtido por fallback')

        # Observações de desligamento quando possível
        comunicado = row.get('COMUNICADO DE DESLIGAMENTO') or row.get('Comunicado de desligamento')
        data_dem = row.get('DATA DEMISSÃO') or row.get('Data Demissão') or row.get('DATA DEMISSAO')
        if comunicado:
            comunicado_up = str(comunicado).strip().upper()
        else:
            comunicado_up = ''
        if data_dem is not None and not pd.isna(data_dem):
            try:
                data_dem_dt = pd.to_datetime(data_dem, errors='coerce', dayfirst=True)
            except Exception:
                data_dem_dt = None
        else:
            data_dem_dt = None
        if comunicado_up == 'OK' and data_dem_dt is not None and pd.notnull(data_dem_dt):
            if data_dem_dt.day <= 15:
                obs_msgs.append('Desligamento comunicado até dia 15')
            else:
                obs_msgs.append('Desligamento após dia 15 (proporcional)')

        custo_empresa = round(total_f * 0.8, 2)
        desconto_prof = round(total_f * 0.2, 2)

        out_row = {
            'Matricula': matricula,
            'Admissão': adm,
            'Sindicato do Colaborador': sindicato,
            'Competência': competencia,
            'Dias': dias_n,
            'VALOR DIÁRIO VR': round(valor_diario, 2),
            'TOTAL': round(total_f, 2),
            'Custo empresa': custo_empresa,
            'Desconto profissional': desconto_prof,
            'OBS GERAL': ' | '.join(dict.fromkeys([m for m in obs_msgs if m]))
        }
        out_rows.append(out_row)
        logs_final.append(f"Matricula {matricula}: dias={dias_n}, valor_diario={valor_diario}, total={total_f} (reason={locals().get('reason','')}) obs={' | '.join(obs_msgs)}")

    df_out = pd.DataFrame(out_rows, columns=['Matricula', 'Admissão', 'Sindicato do Colaborador', 'Competência', 'Dias', 'VALOR DIÁRIO VR', 'TOTAL', 'Custo empresa', 'Desconto profissional', 'OBS GERAL'])

    # Salva CSV
    out_filename = os.path.join(os.path.dirname(output_csv), f"RESULTADO_VR_MENSAL_{competencia.replace('.', '_')}.csv")
    df_out.to_csv(out_filename, sep=';', index=False, encoding='utf-8-sig')
    logger.info(f"Planilha final CSV salva em: {out_filename}")

    # salva log
    log_path = os.path.splitext(out_filename)[0] + '_log.txt'
    with open(log_path, 'w', encoding='utf-8') as lf:
        for l in logs_final:
            lf.write(l + '\n')
    logger.info(f"Log da geração final salvo em: {log_path}")

    return out_filename