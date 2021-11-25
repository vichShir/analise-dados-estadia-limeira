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
    url_acomodacoes = client.presigned_get_object("processing", 'acomodacoes_hashcode_' + current_date + '.parquet')
    df_acomodacoes = pd.read_parquet(url_acomodacoes)
    
    # Persiste os arquivos na área de Staging.
    df_acomodacoes.to_csv("/tmp/acomodacoeshash.csv", index=False)
 

def transform():

    # Ler os dados a partir da área de Staging.
    df_acomodacoes = pd.read_csv("/tmp/acomodacoeshash.csv")

    ##############################################################
    # Acomodações baratas
    ##############################################################
    filtro_mais_baratos = (
        (df_acomodacoes['total'] < 1000)
    )
    df_baratos = df_acomodacoes[filtro_mais_baratos].copy()
    total_baratos = df_baratos.shape[0]
    print('Acomodações baratas: OK')

    df_baratos.index.name = 'index'
    df_baratos.to_csv('/tmp/acomodacoes_baratas.csv')
    print('(1/2) [STAGING] Acomodações baratas: OK')

    ##############################################################
    # Acomodações caras
    ##############################################################
    filtro_mais_caros= (
        (df_acomodacoes['total'] >= 1000)
    )
    df_caros = df_acomodacoes[filtro_mais_caros].copy()
    total_caros = df_caros.shape[0]
    print('Acomodações baratas: OK')

    df_caros.index.name = 'index'
    df_caros.to_csv('/tmp/acomodacoes_caras.csv')
    print('(1/2) [STAGING] Acomodações caras: OK')


def load():

    # Carrega os dados para o Data Lake.
    client.fput_object("curated", "categorias-acomodacoes/acomodacoes_baratas.csv", "/tmp/acomodacoes_baratas.csv")
    client.fput_object("curated", "categorias-acomodacoes/acomodacoes_caras.csv", "/tmp/acomodacoes_caras.csv")

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