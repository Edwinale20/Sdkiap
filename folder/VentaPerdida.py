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

#PASO 3: LIMPIEZA Y PREPARACION DE DATOS

# Renombrar proveedores y eliminar proveedor dummy en venta perdida
proveedores_renombrados = {
    "1822 PHILIP MORRIS MEXICO, S.A. DE C.V.": "PMI",
    "1852 BRITISH AMERICAN TOBACCO MEXICO COMERCIAL, S.A. DE C.V.": "BAT",
    "6247 MAS BODEGA Y LOGISTICA, S.A. DE C.V.": "JTI",
    "21864 ARTICUN DISTRIBUIDORA S.A. DE C.V.": "Articun",
    "2216 NUEVA DISTABAC, S.A. DE C.V.": "Nueva Distabac",
    "8976 DRUGS EXPRESS, S.A DE C.V.": "Drugs Express",
    "1 PROVEEDOR DUMMY MIGRACION": "Eliminar"
}
venta_perdida_data['PROVEEDOR'] = venta_perdida_data['PROVEEDOR'].replace(proveedores_renombrados)
venta_perdida_data = venta_perdida_data[venta_perdida_data['PROVEEDOR'] != "Eliminar"]

# Renombrar categorías en venta perdida
venta_perdida_data['CATEGORIA'] = venta_perdida_data['CATEGORIA'].replace({
    "008 Cigarros": "8",
    "062 RRPs (Vapor y tabaco calentado)": "62"
})

# Categorizar todos los artículos que contienen "Vuse" en la categoría 62
venta_perdida_data.loc[venta_perdida_data['DESC_ARTICULO'].str.contains('Vuse', case=False, na=False), 'CATEGORIA'] = "62"

# Convertir las columnas necesarias a string para evitar errores en el merge
columns_to_convert = ['PLAZA', 'DIVISION', 'CATEGORIA', 'ID_ARTICULO', 'DESC_ARTICULO', 'PROVEEDOR']
for col in columns_to_convert:
    if col in venta_perdida_data.columns and col in venta_pr_data.columns:
        venta_perdida_data[col] = venta_perdida_data[col].astype(str)
        venta_pr_data[col] = venta_pr_data[col].astype(str)

# Realizar el merge para traer FAMILIA y SEGMENTO a venta perdida data basado en ID_ARTICULO
venta_perdida_data = pd.merge(
    venta_perdida_data, 
    venta_pr_data[['ID_ARTICULO', 'FAMILIA', 'SEGMENTO']], 
    on='ID_ARTICULO', 
    how='left'
)

# Filtrar solo las columnas necesarias
venta_perdida_data = venta_perdida_data[[
    'PROVEEDOR', 'CATEGORIA', 'ID_ARTICULO', 'UPC', 'DESC_ARTICULO', 
    'DIVISION', 'PLAZA', 'MERCADO', 'VENTA_PERDIDA_PESOS', 'FAMILIA', 'SEGMENTO'
]]

# Mostrar un mensaje indicando que la limpieza y preparación de datos ha sido exitosa
st.success("Limpieza y preparación de datos completada.")
