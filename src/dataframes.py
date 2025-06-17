import os
import zipfile
import pandas as pd

base_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(base_dir, 'data', '202401_NFs.zip')


with zipfile.ZipFile(file_path, 'r') as zip_ref:
    with zip_ref.open('202401_NFs_Cabecalho.csv') as Cabecalho:
        df_cabecalho = pd.read_csv(Cabecalho)
    with zip_ref.open('202401_NFs_Itens.csv') as Itens:
        df_itens = pd.read_csv(Itens)