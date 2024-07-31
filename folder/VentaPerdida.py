import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from io import BytesIO
import requests

# Configuración de la página
st.set_page_config(page_title="Reporte de Venta Pérdida Cigarros y RRPS", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

# Título de la aplicación
st.title("📊 Reporte de Venta Perdida Cigarros y RRPS")
st.markdown("En esta página podrás visualizar la venta pérdida día con día, por plaza, división, proveedor y otros datos que desees. Esto con el fin de dar acción y reducir la Venta pérdida")

# Fetch GitHub token from secrets
try:
    github_token = st.secrets["github"]["token"]
except KeyError:
    st.error("GitHub token not found. Please add it to the secrets.")
    st.stop()

# GitHub repository details
repo_owner = "Edwinale20"
repo_name = "317B"

# File paths
venta_pr_path = "venta/Venta PR.xlsx"
folder_path = "venta"  # Folder path for daily loss files

# Function to fetch CSV files from GitHub
def fetch_csv_files(repo_owner, repo_name, path=""):
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{path}"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return [file['name'] for file in response.json() if file['name'].endswith('.csv')]

# Function to read a CSV file from GitHub
def read_csv_from_github(repo_owner, repo_name, file_path):
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{file_path}"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3.raw"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return pd.read_csv(BytesIO(response.content), encoding='ISO-8859-1')

# Function to process Venta PR file
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

    # Renombrar las columnas para coincidir con las esperadas en el código
    df = df.rename(columns={
        'Plaza': 'PLAZA',
        'División': 'DIVISION',
        'Categoría': 'CATEGORIA',
        'Artículo': 'ID_ARTICULO',
        'Semana Contable': 'Semana',
        'Venta Neta Total': 'Venta Neta Total',
        'Proveedor': 'PROVEEDOR'
    })

    return df

# Function to apply filters
def apply_filters(data, proveedor, plaza, categoria, semana, division, articulo):
    if proveedor: data = data[data['PROVEEDOR'] == proveedor]
    if plaza: data = data[data['PLAZA'] == plaza]
    if categoria: data = data[data['CATEGORIA'] == categoria]
    if semana: data = data[data['Semana'] == semana]
    if division: data = data[data['DIVISION'] == division]
    if articulo: data = data[data['ID_ARTICULO'].str.contains(articulo, case=False, na=False)]
    return data

# Function to apply weekly view
def apply_weekly_view(data):
    if 'VENTA_PERDIDA_PESOS' not in data.columns:
        st.error("La columna 'VENTA_PERDIDA_PESOS' no se encontró en los datos.")
        return pd.DataFrame()
    weekly_data = data.groupby(['Semana', 'PROVEEDOR', 'PLAZA', 'CATEGORIA', 'DIVISION', 'ID_ARTICULO']).agg({'VENTA_PERDIDA_PESOS': 'sum'}).reset_index()
    return weekly_data

# Cargar datos de Venta PR
venta_pr_data = load_venta_pr(venta_pr_path)

# Cargar y combinar datos de venta perdida de la carpeta
all_files = fetch_csv_files(repo_owner, repo_name, folder_path)
venta_perdida_data = pd.concat([read_csv_from_github(repo_owner, repo_name, f"{folder_path}/{file}") for file in all_files])

# Renombrar columnas en 'venta_perdida_data' para que coincidan con 'venta_pr_data'
venta_perdida_data = venta_perdida_data.rename(columns={
    'PLAZA': 'PLAZA',
    'DIVISION': 'DIVISION',
    'CATEGORIA': 'CATEGORIA',
    'ID_ARTICULO': 'ID_ARTICULO',
    'PROVEEDOR': 'PROVEEDOR',
    'Semana': 'Semana'
})

# Combinar datos de venta perdida con venta pr
combined_data = pd.merge(venta_perdida_data, venta_pr_data, on=["PLAZA", "DIVISION", "CATEGORIA", "ID_ARTICULO", "PROVEEDOR", "Semana"], how="left")

# Function to plot venta perdida vs venta neta total
def plot_comparacion_venta_perdida_vs_neta(data, venta_pr_data, view):
    if venta_pr_data.empty:
        st.warning("No hay datos disponibles para 'Venta PR'")
        return go.Figure()

    if view == "semanal":
        venta_pr_data_grouped = venta_pr_data.groupby('Semana')['Venta Neta Total'].sum().reset_index()
        comparacion = data.groupby('Semana')['VENTA_PERDIDA_PESOS'].sum().reset_index()
        comparacion = comparacion.merge(venta_pr_data_grouped, left_on='Semana', right_on='Semana', how='left')
    else:
        venta_pr_data['Mes'] = pd.to_datetime(venta_pr_data['Semana'], format='%Y%U').dt.to_period('M')
        venta_pr_data_grouped = venta_pr_data.groupby('Mes')['Venta Neta Total'].sum().reset_index()
        comparacion = data.groupby('Mes')['VENTA_PERDIDA_PESOS'].sum().reset_index()
        comparacion = comparacion.merge(venta_pr_data_grouped, left_on='Mes', right_on='Mes', how='left')

    comparacion['Venta No Perdida'] = comparacion['Venta Neta Total'] - comparacion['VENTA_PERDIDA_PESOS']
    comparacion['% Venta Perdida'] = (comparacion['VENTA_PERDIDA_PESOS'] / comparacion['Venta Neta Total']) * 100

    fig = go.Figure(data=[
        go.Bar(
            name='Venta Perdida',
            x=comparacion['Semana' if view == "semanal" else 'Mes'],
            y=comparacion['VENTA_PERDIDA_PESOS'],
            marker_color='red'
        ),
        go.Bar(
            name='Venta No Perdida',
            x=comparacion['Semana' if view == "semanal" else 'Mes'],
            y=comparacion['Venta No Perdida'],
            marker_color='blue'
        )
    ])
    fig.update_layout(
        barmode='stack',
        title='Venta Perdida vs Venta Neta Total',
        xaxis_title='Semana' if view == "semanal" else 'Mes',
        yaxis=dict(tickformat="$,d", title='Monto (Pesos)'),
        xaxis=dict(title='Tipo de Venta')
    )
    return fig

# Function to plot venta perdida por plaza
def plot_venta_perdida_plaza(data):
    fig = go.Figure()
    grouped_data = data.groupby('PLAZA')['VENTA_PERDIDA_PESOS'].sum().reset_index()
    
    fig.add_trace(go.Bar(
        x=grouped_data['PLAZA'], 
        y=grouped_data['VENTA_PERDIDA_PESOS'], 
        marker_color='rgb(26, 118, 255)'
    ))
    
    fig.update_layout(
        title='Venta Perdida por Plaza',
        xaxis_title='Plaza',
        yaxis_title='Venta Perdida (Pesos)',
        yaxis=dict(tickformat="$,d")
    )
    
    return fig

# Function to plot top 10 artículos con mayor venta perdida
def plot_articulos_venta_perdida(data):
    fig = go.Figure()
    grouped_data = data.groupby('DESC_ARTICULO')['VENTA_PERDIDA_PESOS'].sum().reset_index()
    grouped_data = grouped_data.sort_values(by='VENTA_PERDIDA_PESOS', ascending=False).head(10)
    fig.add_trace(go.Bar(
        x=grouped_data['DESC_ARTICULO'], 
        y=grouped_data['VENTA_PERDIDA_PESOS'], 
        marker_color='rgb(55, 83, 109)'
    ))
    fig.update_layout(
        title='Top 10 Artículos con mayor Venta Perdida',
        xaxis_title='Artículo',
        yaxis_title='Venta Perdida (Pesos)',
        yaxis=dict(t
