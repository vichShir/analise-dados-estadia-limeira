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

dag = DAG('etl_categorias_acomodacoes',
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
    url_acomodacoes = client.presigned_get_object("processing", 'acomodacoes_hashcode_10_11_2021.parquet')
    df_acomodacoes = pd.read_parquet(url_acomodacoes)
    
    # Persiste os arquivos na área de Staging.
    df_acomodacoes.to_csv("/tmp/acomodacoeshash.csv", index=False)
 

def transform():

    # Ler os dados a partir da área de Staging.
    df_acomodacoes = pd.read_csv("/tmp/acomodacoeshash.csv")

    ##############################################################
    # Bairros - perto
    ##############################################################
    filtro_bairros_pertos = (
        (df_acomodacoes['bairro'] == 'JD. Paulista') |
        (df_acomodacoes['bairro'] == 'JD. Morro Azul')
    )
    df_bairros_pertos = df_acomodacoes[filtro_bairros_pertos].copy()
    total_pertos = df_bairros_pertos.shape[0]
    print('Bairros pertos: OK')

    ### Perto e barato
    filtro_imobB_bairro_morro = (
        (df_bairros_pertos['imob'] == 'B') &
        (df_bairros_pertos['bairro'] == 'JD. Morro Azul')
    )
    df_bairros_pertos_baratos = df_bairros_pertos[filtro_imobB_bairro_morro]
    df_bairros_pertos_baratos.index.name = 'index'
    df_bairros_pertos_baratos.to_csv('/tmp/acomodacoes_perto_barato.csv')
    print('(1/6) [STAGING] Acomodações perto e barato: OK')

    ### Perto e caro
    filtro_caro = (
        (df_bairros_pertos['total'] > 700)
    )
    df_pertos_caros = df_bairros_pertos[filtro_caro]
    df_pertos_caros.index.name = 'index'
    df_pertos_caros.to_csv('/tmp/acomodacoes_perto_caro.csv')
    print('(2/6) [STAGING] Acomodações perto e caro: OK')

    ##############################################################
    # Bairros - longe
    ##############################################################
    filtro_bairros_longe = (
        (df_acomodacoes['bairro'] == 'JD. Cidade Universitária I') |
        (df_acomodacoes['bairro'] == 'Chácara Antonieta') |
        (df_acomodacoes['bairro'] == 'JD. São Paulo')
    )
    df_bairros_longe = df_acomodacoes[filtro_bairros_longe].copy()
    print('Bairros longes: OK')

    ### Longe e barato
    filtro_mais_baratos = (
        (df_bairros_longe['total'] < 1000)
    )
    df_bairros_longe_barato = df_bairros_longe[filtro_mais_baratos]

    # Menor preço m2
    filtro_barato_menor_m2 = (
        ((df_bairros_longe_barato['preco_m2'] < 35) | (df_bairros_longe_barato['preco_m2'].isnull()))
    )
    df_longe_barato_menor_m2 = df_bairros_longe_barato[filtro_barato_menor_m2].sort_values(by='total')
    df_longe_barato_menor_m2.index.name = 'index'
    df_longe_barato_menor_m2.to_csv('/tmp/acomodacoes_longe_barato_menorm2.csv')
    print('(3/6) [STAGING] Acomodações longe, barato e menor m2: OK')

    # Maior preço m2
    filtro_barato_maior_m2 = (
        (df_bairros_longe_barato['preco_m2'] >= 35)
    )
    df_longe_barato_maior_m2 = df_bairros_longe_barato[filtro_barato_maior_m2].sort_values(by='total')
    df_longe_barato_menor_m2.to_csv('/tmp/acomodacoes_longe_barato_maiorm2.csv')
    print('(4/6) [STAGING] Acomodações longe, barato e maior m2: OK')

    ### Longe e caro
    filtro_mais_caros = (
        (df_bairros_longe['total'] >= 1000)
    )
    df_bairros_longe_caro = df_bairros_longe[filtro_mais_caros]

    # Menor preço m2
    filtro_caro_menor_m2 = (
        ((df_bairros_longe_caro['preco_m2'] < 35) | (df_bairros_longe_caro['preco_m2'].isnull()))
    )
    df_longe_caro_menor_m2 = df_bairros_longe_caro[filtro_caro_menor_m2].sort_values(by='total')
    df_longe_caro_menor_m2.index.name = 'index'
    df_longe_caro_menor_m2.to_csv('/tmp/acomodacoes_longe_caro_menorm2.csv')
    print('(5/6) [STAGING] Acomodações longe, caro e menor m2: OK')

    # Maior preço m2
    filtro_caro_maior_m2 = (
        (df_bairros_longe_caro['total'] > 1040) & 
        ((df_bairros_longe_caro['preco_m2'] > 35) | (df_bairros_longe_caro['preco_m2'].isnull()))
    )
    df_longe_caro_maior_m2 = df_bairros_longe_caro[filtro_caro_maior_m2].sort_values(by='total')
    df_longe_caro_maior_m2.index.name = 'index'
    df_longe_caro_maior_m2.to_csv('/tmp/acomodacoes_longe_caro_maiorm2.csv')
    print('(6/6) [STAGING] Acomodações longe, caro e maior m2: OK')


def load():

    # Carrega os dados para o Data Lake.
    client.fput_object("curated", "categorias-acomodacoes/acomodacoes_perto_barato.csv", "/tmp/acomodacoes_perto_barato.csv")
    client.fput_object("curated", "categorias-acomodacoes/acomodacoes_perto_caro.csv", "/tmp/acomodacoes_perto_caro.csv")
    client.fput_object("curated", "categorias-acomodacoes/acomodacoes_longe_barato_menorm2.csv", "/tmp/acomodacoes_longe_barato_menorm2.csv")
    client.fput_object("curated", "categorias-acomodacoes/acomodacoes_longe_barato_maiorm2.csv", "/tmp/acomodacoes_longe_barato_maiorm2.csv")
    client.fput_object("curated", "categorias-acomodacoes/acomodacoes_longe_caro_menorm2.csv", "/tmp/acomodacoes_longe_caro_menorm2.csv")
    client.fput_object("curated", "categorias-acomodacoes/acomodacoes_longe_caro_maiorm2.csv", "/tmp/acomodacoes_longe_caro_maiorm2.csv")


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