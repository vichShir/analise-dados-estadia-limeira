import datetime
from datetime import date
from io import BytesIO
import pandas as pd
import numpy as np
import re
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.models import Variable
from minio import Minio

DEFAULT_ARGS = {
    'owner': 'Airflow',
    'depends_on_past': False,
    'start_date': datetime.datetime(2021, 1, 13),
}

dag = DAG('etl_webscraping_acomodacoes',
          default_args=DEFAULT_ARGS,
          schedule_interval="@once"
        )

data_lake_server = Variable.get("data_lake_server")
data_lake_login = Variable.get("data_lake_login")
data_lake_password = Variable.get("data_lake_password")

client = Minio(
        data_lake_server,
        access_key=data_lake_login,
        secret_key=data_lake_password,
        secure=False
    )

today = date.today()
current_date = today.strftime("%d_%m_%Y")

def extract():

    # Extrai os dados a partir do Data Lake.
    url_acomodacoes = client.presigned_get_object("landing", 'webscraping_acomodacoeshash_10_11_2021.csv')
    url_bairros = client.presigned_get_object("landing", "bairros/bairros_eleitos.csv")
    df_acomodacoes = pd.read_csv(url_acomodacoes)
    df_bairros = pd.read_csv(url_bairros)
    
    # Persiste os arquivos na área de Staging.
    df_acomodacoes.to_csv("/tmp/acomodacoeshash.csv", index=False)
    df_bairros.to_csv("/tmp/bairros_eleitos.csv", index=False)
 

def transform():

    # Ler os dados a partir da área de Staging.
    df = pd.read_csv("/tmp/acomodacoeshash.csv")
    df_bairros = pd.read_csv("/tmp/bairros_eleitos.csv")

    ##############################################################
    # Coluna - Vaga de garagem
    ##############################################################
    map_vaga_garagem = {
        'Não': 0,
        'Sim': 1
    }
    df['vaga_garagem'] = df['vaga_garagem'].map(map_vaga_garagem)
    df['vaga_garagem'] = df['vaga_garagem'].fillna(0)
    print('Coluna - Vaga de garagem: OK')

    ##############################################################
    # Coluna - Área
    ##############################################################
    # Coletando apenas o número e convertendo para int
    areas = []
    for i in range(len(df['area'])):
      try:
        area_value = int(re.findall('\d[0-9]+', df['area'][i])[0])
      except:
        area_value = np.nan
      areas.append(area_value)
    df['area'] = areas
    print('Coluna - Área: OK')

    ##############################################################
    # Coluna - Aluguel
    ##############################################################
    # Extraindo numeros com ',' e convertendo para float
    values_extracted = []
    for i in range(len(df['aluguel'])):
      try:
        value_extracted = re.findall('[0-9]+[,]*', df['aluguel'][i])
        value_extracted = float(''.join(value_extracted).replace(',', '.'))
      except:
        value_extracted = np.nan
      values_extracted.append(value_extracted)
    df['aluguel'] = values_extracted
    print('Coluna - Aluguel: OK')

    ##############################################################
    # Coluna - Condomínio
    ##############################################################
    # Extraindo somente os numeros e convertendo para float
    values_extracted = []
    for i in range(len(df['condominio'])):
      try:
        value_extracted = re.findall('[0-9]+[,.][0-9]+', df['condominio'][i])
        value_extracted = [float(x.replace(',', '.')) for x in value_extracted]
        value_extracted = sum(value_extracted)
      except:
        value_extracted = np.nan
      values_extracted.append(value_extracted)
    df['condominio'] = values_extracted
    print('Coluna - Condomínio: OK')

    ##############################################################
    # Coluna - Bairro
    ##############################################################
    texts_extracted = [x.split('-')[0].strip() for x in df['bairro']]
    df['bairro'] = texts_extracted
    bairro_map = {
        'Jardim Cidade Universitária I': 'JD. Cidade Universitária I',
        'CIDADE UNIVERSITARIA': 'JD. Cidade Universitária I',
        'Jardim Cidade Universitaria I': 'JD. Cidade Universitária I',
        'Jardim Paulista': 'JD. Paulista',
        'JD. PAULISTA': 'JD. Paulista',
        'Jardim Morro Azul': 'JD. Morro Azul',
        'Chacara Antonieta': 'Chácara Antonieta',
        'Jardim São Paulo': 'JD. São Paulo'
    }
    df['bairro'] = df['bairro'].map(bairro_map)
    print('Coluna - Bairro: OK')

    ##############################################################
    # Filtrando colunas
    ##############################################################
    df = df.drop(columns=['imovel_url', 'nome'])
    print('Filtrando colunas: OK')

    ##############################################################
    # Alterando códigos das imobiliárias
    ##############################################################
    imob_map = {
        '53dd1202c5ef8ce3878ffbd4b3c79bd2': 'A',
        'ef23a7e1738f4b316011bbdd88e514a2': 'B',
        'c7234506476bbf0aff48eda764ff9eba': 'C'
    }
    df['imob'] = df['imob'].map(imob_map)
    print('Imobiliárias códigos: OK')

    ##############################################################
    # Criando coluna: total
    ##############################################################
    df['total'] = df['aluguel'] + df['condominio']
    print('Criação da coluna total: OK')

    ##############################################################
    # Criando coluna: preço por metro quadrado
    ##############################################################
    df['preco_m2'] = df['total'] / df['area']
    df['preco_m2'] = df['preco_m2'].replace(np.inf, np.nan)
    print('Criação da coluna preço por metro quadrado: OK')

    ##############################################################
    # Tratando dataframe dos bairros eleitos
    ##############################################################
    df_bairros = df_bairros.drop(columns=['lat', 'lon'])
    df_bairros = df_bairros.iloc[[7, 11, 10, 19],:]
    df_bairros = df_bairros.sort_values(by='dist').reset_index(drop=True)
    print('Tratando dataframe dos bairros eleitos: OK')

    ##############################################################
    # Criando coluna: distância da faculdade
    ##############################################################
    dists_unicamp = []
    for bairro in df['bairro']:
      if bairro == 'JD. Cidade Universitária I':
        dists_unicamp.append(df_bairros.loc[2, 'dist'])
      elif bairro == 'JD. Paulista':
        dists_unicamp.append(df_bairros.loc[0, 'dist'])
      elif bairro == 'JD. Morro Azul':
        dists_unicamp.append(df_bairros.loc[1, 'dist'])
      elif bairro == 'Chácara Antonieta':
        dists_unicamp.append(df_bairros.loc[3, 'dist'])
      elif bairro == 'JD. São Paulo':
        dists_unicamp.append(np.nan)
    df['dist_unicamp'] = dists_unicamp
    print('Criaçaõ da coluna distância da faculdade: OK')

    ##############################################################
    # Removendo linhas com aluguel nulo
    ##############################################################
    df = df[df['aluguel'].notna()]
    print('Remoção das linhas com aluguel nulo: OK')

    # Persiste os dados transformados na área de staging.
    df.to_csv("/tmp/acomodacoeshash.csv", index=False)


def load():

    # Carrega os dados a partir da área de staging.
    df_ = pd.read_csv("/tmp/acomodacoeshash.csv")

    acomodacoes_filename = 'acomodacoes_hashcode_' + current_date + '.parquet'

    # Converte os dados para o formato parquet.
    df_.to_parquet("/tmp/" + acomodacoes_filename, index=False)

    # Carrega os dados para o Data Lake.
    client.fput_object(
        "processing",
        acomodacoes_filename,
        "/tmp/" + acomodacoes_filename
    )


extract_task = PythonOperator(
    task_id='extract_file_from_data_lake',
    provide_context=True,
    python_callable=extract,
    dag=dag
)

transform_task = PythonOperator(
    task_id='transform_data',
    provide_context=True,
    python_callable=transform,
    dag=dag
)

load_task = PythonOperator(
    task_id='load_file_to_data_lake',
    provide_context=True,
    python_callable=load,
    dag=dag
)

clean_task = BashOperator(
    task_id="clean_files_on_staging",
    bash_command="rm -f /tmp/*.csv;rm -f /tmp/*.json;rm -f /tmp/*.parquet;",
    dag=dag
)

extract_task >> transform_task >> load_task >> clean_task