# Paso 1: Importar librerías---------------------------------------
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from io import BytesIO
import requests
from datetime import datetime

st.set_option('client.showErrorDetails', True)

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
master_path = "venta/MASTER.xlsx"
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
def load_and_process_venta_perdida_data(repo_owner, repo_name, folder_path):
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{folder_path}"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    all_files = [file['name'] for file in response.json() if file['name'].endswith('.csv')]
    
    all_data = []
    for file in all_files:
        date_str = file.split('.')[0]  # Obtener la fecha del nombre del archivo
        date = datetime.strptime(date_str, '%d%m%Y')
        df = read_csv_from_github(repo_owner, repo_name, f"{folder_path}/{file}")
        df['Fecha'] = date
        all_data.append(df)
    
    venta_perdida_data = pd.concat(all_data)
    venta_perdida_data['Semana'] = venta_perdida_data['Fecha'].dt.isocalendar().week
    venta_perdida_data['Mes'] = venta_perdida_data['Fecha'].dt.to_period('M')
    
    return venta_perdida_data

# Cargar los datos de ventas perdidas
venta_perdida_data = load_and_process_venta_perdida_data(repo_owner, repo_name, folder_path)

# Función para cargar los datos de Venta PR desde un archivo Excel almacenado en GitHub
@st.cache_data(show_spinner=True)
def load_venta_pr(repo_owner, repo_name, file_path):
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{file_path}"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3.raw"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    excel_content = BytesIO(response.content)
    df = pd.read_excel(excel_content)

    # Eliminar columnas no deseadas si están presentes
    columns_to_drop = ['PROVEEDOR', 'FAMILIA', 'SEGMENTO']  # Eliminar estas columnas porque ahora están en el MASTER
    df = df.drop(columns=[col for col in columns_to_drop if col in df.columns], errors='ignore')

    # Crear la columna de Mes a partir de la semana contable
    df['Semana'] = df['Semana Contable'].apply(lambda x: int(str(x)[-2:]))  # Extraer el número de la semana
    df['Mes'] = pd.to_datetime(df['Semana Contable'].astype(str) + '1', format='%G%V%u').dt.to_period('M')

    return df

venta_pr_data = load_venta_pr(repo_owner, repo_name, venta_pr_path)

# Función para cargar los datos de MASTER desde un archivo Excel almacenado en GitHub
@st.cache_data(show_spinner=True)
def load_master_data(repo_owner, repo_name, file_path):
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{file_path}"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3.raw"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    excel_content = BytesIO(response.content)
    return pd.read_excel(excel_content)

master_data = load_master_data(repo_owner, repo_name, master_path)

# Convertir UPC a string en ambos DataFrames
venta_perdida_data['UPC'] = venta_perdida_data['UPC'].astype(str)
master_data['UPC'] = master_data['UPC'].astype(str)

# Realizar el merge para traer FAMILIA y SEGMENTO a venta perdida data basado en UPC del archivo MASTER
venta_perdida_data = pd.merge(
    venta_perdida_data, 
    master_data[['UPC', 'PROVEEDOR', 'FAMILIA', 'SEGMENTO']], 
    on='UPC', 
    how='left'
)

# Filtrar solo las columnas necesarias
venta_perdida_data = venta_perdida_data[[
    'PROVEEDOR', 'CATEGORIA', 'ID_ARTICULO', 'UPC', 'DESC_ARTICULO', 
    'DIVISION', 'PLAZA', 'MERCADO', 'VENTA_PERDIDA_PESOS', 'FAMILIA', 'SEGMENTO', 'Fecha', 'Semana', 'Mes'
]]

# Realizar el merge para traer FAMILIA, SEGMENTO y PROVEEDOR a venta perdida data basado en UPC del archivo MASTER
venta_perdida_data = pd.merge(
    venta_perdida_data, 
    master_data[['UPC', 'PROVEEDOR', 'FAMILIA', 'SEGMENTO']], 
    on='UPC', 
    how='left'
)

# Verificar si las columnas están presentes después del merge
st.write("Columnas en venta_perdida_data después del merge:", venta_perdida_data.columns)

# Filtrar solo las columnas necesarias
try:
    venta_perdida_data = venta_perdida_data[[
        'PROVEEDOR', 'CATEGORIA', 'ID_ARTICULO', 'UPC', 'DESC_ARTICULO', 
        'DIVISION', 'PLAZA', 'MERCADO', 'VENTA_PERDIDA_PESOS', 'FAMILIA', 'SEGMENTO', 'Fecha', 'Semana', 'Mes'
    ]]
except KeyError as e:
    st.error(f"Error al filtrar las columnas: {e}")


# Mostrar un mensaje indicando que la limpieza y preparación de datos ha sido exitosa
st.success("Limpieza, procesamiento y preparación de datos completada.")


# PASO 5: APLICAR FILTROS Y SIDE BAR---------------------------------------
# Asegurarse de que las columnas 'FAMILIA' y 'SEGMENTO' estén presentes y convertidas a string
venta_perdida_data['FAMILIA'] = venta_perdida_data['FAMILIA'].fillna('').astype(str)
venta_perdida_data['SEGMENTO'] = venta_perdida_data['SEGMENTO'].fillna('').astype(str)
venta_pr_data['FAMILIA'] = venta_pr_data['FAMILIA'].fillna('').astype(str)
venta_pr_data['SEGMENTO'] = venta_pr_data['SEGMENTO'].fillna('').astype(str)

# Aplicar los filtros en el sidebar
with st.sidebar:
    st.header("Filtros")
    proveedor = st.selectbox("Proveedor", ["Todos"] + sorted(venta_perdida_data['PROVEEDOR'].unique().tolist()))
    plaza = st.selectbox("Plaza", ["Todas"] + sorted(venta_perdida_data['PLAZA'].unique().tolist()))
    division = st.selectbox("División", ["Todas"] + sorted(venta_perdida_data['DIVISION'].unique().tolist()))
    familia = st.selectbox("Familia", ["Todas"] + sorted(venta_perdida_data['FAMILIA'].unique().tolist()))
    segmento = st.selectbox("Segmento", ["Todos"] + sorted(venta_perdida_data['SEGMENTO'].unique().tolist()))
    view = st.selectbox("Vista", ["semanal", "mensual"])


# Función para aplicar filtros
def apply_filters(data, proveedor, plaza, division, familia, segmento):
    if proveedor != "Todos":
        data = data[data['PROVEEDOR'] == proveedor]
    if plaza != "Todas":
        data = data[data['PLAZA'] == plaza]
    if division != "Todas":
        data = data[data['DIVISION'] == division]
    if familia != "Todas":
        data = data[data['FAMILIA'] == familia]
    if segmento != "Todos":
        data = data[data['SEGMENTO'] == segmento]
    return data

# Aplicar filtros a los datos de venta perdida y venta PR
filtered_venta_perdida_data = apply_filters(venta_perdida_data, proveedor, plaza, division, familia, segmento)
filtered_venta_pr_data = apply_filters(venta_pr_data, proveedor, plaza, division, familia, segmento)

# Mostrar los datos filtrados en tablas para verificación
st.write("Datos de Venta Perdida Filtrados:", filtered_venta_perdida_data)
st.write("Datos de Venta PR Filtrados:", filtered_venta_pr_data)

# PASO 6: CREACIÓN DE GRÁFICAS---------------------------------------
# Ejemplo de gráfica de barras de venta perdida por proveedor

def plot_venta_perdida_por_proveedor(data):
    fig = go.Figure(data=[
        go.Bar(name='Venta Perdida', x=data['PROVEEDOR'], y=data['VENTA_PERDIDA_PESOS'])
    ])
    fig.update_layout(title="Venta Perdida por Proveedor", xaxis_title="Proveedor", yaxis_title="Venta Perdida (Pesos)")
    return fig

# Graficar la venta perdida por proveedor
st.plotly_chart(plot_venta_perdida_por_proveedor(filtered_venta_perdida_data))

st.success("Filtros aplicados y visualización generada.")

