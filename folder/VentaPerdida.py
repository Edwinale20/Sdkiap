# Paso 1: Importar librerías---------------------------------------
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from io import BytesIO
import requests

# PASO 2: CONFIGURACIÓN DE LA PÁGINA Y CARGA DE DATOS---------------------------------------
st.set_page_config(page_title="Reporte de Venta Pérdida Cigarros y RRPS", page_icon="📊", layout="wide", initial_sidebar_state="expanded")
st.title("📊 Reporte de Venta Perdida Cigarros y RRPS")
st.markdown("En esta página podrás visualizar la venta pérdida día con día, por plaza, división, proveedor y otros datos que desees. Esto con el fin de dar acción y reducir la Venta pérdida.")

# Fetch GitHub token from secrets
try:
    github_token = st.secrets["github"]["token"]
except KeyError:
    st.error("GitHub token not found. Please add it to the secrets.")
    st.stop()

repo_owner = "Edwinale20"
repo_name = "317B"
venta_pr_path = "venta/Venta PR.xlsx"
folder_path = "venta"  # Folder path for daily loss files

# Función para leer un archivo CSV desde GitHub
@st.cache_data(show_spinner=True)
def read_csv_from_github(repo_owner, repo_name, file_path):
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{file_path}"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3.raw"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return pd.read_csv(BytesIO(response.content), encoding='ISO-8859-1')

# Función para cargar y combinar los datos de ventas perdidas desde la carpeta
@st.cache_data(show_spinner=True)
def load_venta_perdida_data(repo_owner, repo_name, folder_path):
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{folder_path}"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    all_files = [file['name'] for file in response.json() if file['name'].endswith('.csv')]
    
    venta_perdida_data = pd.concat([
        read_csv_from_github(repo_owner, repo_name, f"{folder_path}/{file}")
        for file in all_files
    ])
    
    return venta_perdida_data

# Cargar los datos
venta_perdida_data = load_venta_perdida_data(repo_owner, repo_name, folder_path)

# Cargar los datos de Venta PR
@st.cache_data(show_spinner=True)
def load_venta_pr(file_path):
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{file_path}"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3.raw"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    excel_content = BytesIO(response.content)
    df = pd.read_excel(excel_content)
    return df

venta_pr_data = load_venta_pr(venta_pr_path)

