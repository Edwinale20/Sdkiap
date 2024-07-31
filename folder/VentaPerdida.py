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
folder_path = "venta"
venta_pr_path = "venta/Venta PR.xlsx"

# Function to fetch contents from GitHub
def fetch_contents(repo_owner, repo_name, path=""):
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{path}"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

# Function to fetch CSV files from GitHub
def fetch_csv_files(repo_owner, repo_name, path=""):
    contents = fetch_contents(repo_owner, repo_name, path)
    return [file for file in contents if file["name"].endswith(".csv")]

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

# Function to process CSV files
@st.cache_data
def process_data(repo_owner, repo_name, folder_path):
    all_files = fetch_csv_files(repo_owner, repo_name, folder_path)
    all_data = []
    for file in all_files:
        try:
            df = read_csv_from_github(repo_owner, repo_name, f"{folder_path}/{file['name']}")
            all_data.append(df)
        except Exception as e:
            st.write(f"Error leyendo el archivo {file['name']}: {e}")
    if not all_data:
        return None
    data = pd.concat(all_data)
    return data

# Load and process the data
venta_pr_data = load_venta_pr(venta_pr_path)
venta_perdida_data = process_data(repo_owner, repo_name, folder_path)

# Ensure that data is loaded correctly before proceeding
if venta_perdida_data is not None and not venta_pr_data.empty:
    st.write("Datos cargados correctamente desde los archivos.")

    # Unir los datos de venta pérdida con los de Venta PR
    combined_data = pd.merge(venta_perdida_data, venta_pr_data, on=["PLAZA", "DIVISION", "CATEGORIA", "ID_ARTICULO", "PROVEEDOR", "Semana"], how="left")

    # Aquí puedes proceder a aplicar los filtros y generar las gráficas
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
        weekly_data = data.groupby(['Semana', 'PROVEEDOR', 'PLAZA', 'CATEGORIA', 'DIVISION', 'ID_ARTICULO']).agg({'VENTA_PERDIDA_PESOS': 'sum', 'Venta Neta Total': 'sum'}).reset_index()
        return weekly_data

    # Filtrar los datos
    filtered_data = apply_filters(combined_data, None, None, None, None, None, None)
    weekly_data = apply_weekly_view(filtered_data)

    # Function to plot venta perdida vs venta neta total
    def plot_comparacion_venta_perdida_vs_neta(data, view):
        comparacion = data.copy()
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

    # Mostrar gráfico de comparación
    st.plotly_chart(plot_comparacion_venta_perdida_vs_neta(weekly_data, "semanal"))

else:
    st.warning("No se encontraron datos en la carpeta especificada.")



