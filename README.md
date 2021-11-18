# ADEL - Análise de Dados para Estadia em Limeira 🏡
![Jupyter Notebook](https://img.shields.io/badge/Jupyter-F37626.svg?&style=for-the-badge&logo=Jupyter&logoColor=white) ![Google Colab](https://img.shields.io/badge/Colab-F9AB00?style=for-the-badge&logo=googlecolab&color=525252) ![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white) ![Airflow](https://img.shields.io/badge/Airflow-017CEE?style=for-the-badge&logo=Apache%20Airflow&logoColor=white) ![Selenium](https://img.shields.io/badge/Selenium-43B02A?style=for-the-badge&logo=Selenium&logoColor=white) 
### 📃 Descrição
O objetivo do projeto é desenvolver uma **análise de dados**, que auxilie a encontrar **a melhor acomodação** para minha estadia de **_1 a 2 anos_** em **Limeira, SP** para meus estudos na faculdade. 

### 😵 Problema

1. **Determinar os bairros para ficar em Limeira. Critérios:**
   1. **Se for perto da faculdade**, distância de até 1,5km, é um bairro elegível;
   2. **Se for longe da faculdade**, distância maior do que 1,5km, saber se posso ir de ônibus, para isso:
      1. Determinar se existe alguma linha de ônibus de Limeira que interliga o bairro até a faculdade.
2. **Determinar as melhores acomodações, baseadas em:**
   1. Localização (bairro)
   2. Custos (aluguel, condomínio, IPTU, energia, água, internet, gás...)
   3. Mobiliado (quarto, cozinha, banheiro, lavanderia, geladeira, fogão, armários, interfone...)

### 📚 Conteúdo
- **Airflow (DAGs):**
  - Automatização do processo de **ETL das acomodações.**
  - Automatização do processo de **categorização das acomodações.**

- **Minio (Datalake):**
  - Landing
  - Processing
  - Curated

- **Jupyter Notebooks:**
  - Webscraping dos **bairros de Limeira**.
  - Webscraping das **linhas de ônibus de Limeira**.
  - Geração dos **mapas dos pontos de cada linha de ônibus de Limeira.**
  - Análise e seleção dos **bairros de Limeira.**
  - Determinando as **linhas de ônibus de Limeira que interligam cada bairro até a faculdade**.
  - Webscraping das **acomodações** e exportação do **dataset.**
  - ETL e Análise manuais do **dataset das acomodações.**


### 🌐 Motivação
No início de 2020, após o resultado do **Vestibular da Unicamp**, fomos até o interior de SP em Limeira para conhecer a cidade, realizar a matrícula e ver um lugar para eu ficar. Fomos atraídos por stands na rua de imobiliárias e logo decidimos fechar a locação de uma kitnet. Contudo, logo veio a **pandemia do _Coronavírus_**, e tive que **desocupar** a kitnet e **pagar as multas** do contrato da imobiliária. Além de **não ter a certeza de que foi a melhor escolha**, pois não havia pesquisado todas as opções disponíveis.

No início de **2022**, provavelmente, voltaremos com as **aulas presenciais** na faculdade. E desta vez, quero ter a certeza de que escolhi o **melhor lugar**, com custo benefício, aconchego e afins, baseado na **análise de dados** das acomodações extraídas.

