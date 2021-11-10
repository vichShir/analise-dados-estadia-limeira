import datetime
from io import BytesIO
import pandas as pd
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

dag = DAG('etl_column_area',
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

def extract():
    
    # Extrai os dados a partir do Data Lake.
    url = client.presigned_get_object("landing", "acomodacoes_hashcode.csv")
    df_ = pd.read_csv(url)
    
    # Persiste os arquivos na área de Staging.
    df_.to_csv("/tmp/acomodacoes_hashcode.csv", index=False)
 

def transform():

    # Ler os dados a partir da área de Staging.
    df_ = pd.read_csv("/tmp/acomodacoes_hashcode.csv")

    # Mapeando para inteiro
    map_vaga_garagem = {
        'Não': 0,
        'Sim': 1
    }

    df_['vaga_garagem'] = df_['vaga_garagem'].map(map_vaga_garagem)

    # Persiste os dados transformados na área de staging.
    df_.to_csv("/tmp/acomodacoes_hashcode.csv", index=False)


def load():

    # Carrega os dados a partir da área de staging.
    df_ = pd.read_csv("/tmp/acomodacoes_hashcode.csv")

    # Converte os dados para o formato parquet.
    df_.to_parquet("/tmp/acomodacoes_hashcode.parquet", index=False)

    # Carrega os dados para o Data Lake.
    client.fput_object(
        "processing",
        "acomodacoes_hashcode.parquet",
        "/tmp/acomodacoes_hashcode.parquet"
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