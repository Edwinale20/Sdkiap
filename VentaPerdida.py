import os
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import gdown

# Configuración de la página
st.set_page_config(
    page_title="Reporte de Venta Pérdida Cigarros y RRPS",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Título de la aplicación
st.title("📊 Reporte de Venta Pérdida Cigarros y RRPS")
st.markdown("En esta página podrás visualizar la venta pérdida día con día, por plaza, división, proveedor y otros datos que desees. Esto con el fin de dar acción y reducir la Venta pérdida")

# Escopos de la API
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# Cargar las credenciales desde la variable de entorno
def authenticate_drive():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # Si no hay (válidas) credenciales disponibles, deja que el usuario inicie sesión.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Guarda las credenciales para la próxima ejecución
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('drive', 'v3', credentials=creds)
    return service

# Función para obtener la lista de archivos en la carpeta de Google Drive
def get_files_in_folder(service, folder_id):
    results = service.files().list(
        q=f"'{folder_id}' in parents",
        pageSize=1000, fields="nextPageToken, files(id, name)").execute()
    items = results.get('files', [])
    return items

# Función para descargar y leer un archivo CSV desde Google Drive
def load_data(file_id):
    url = f'https://drive.google.com/uc?id={file_id}'
    output = f'{file_id}.csv'
    gdown.download(url, output, quiet=False)
    return pd.read_csv(output, encoding='ISO-8859-1')

# Función para procesar archivos en la carpeta especificada
@st.cache_data
def process_data(service, folder_id):
    items = get_files_in_folder(service, folder_id)
    all_data = []
    file_dates = []

    for item in items:
        try:
            file_id = item['id']
            file_name = item['name']
            date_str = file_name.split('.')[0]
            date = datetime.strptime(date_str, '%d%m%Y')
            df = load_data(file_id)
            df['Fecha'] = date
            all_data.append(df)
            file_dates.append(date)
        except Exception as e:
            st.write(f"Error leyendo el archivo {file_name}: {e}")

    if not all_data:
        return None, file_dates
    else:
        data = pd.concat(all_data)
        data['Fecha'] = pd.to_datetime(data['Fecha'])
        data['Semana'] = data['Fecha'].apply(lambda x: (x - timedelta(days=x.weekday())).strftime('%U'))
        return data, file_dates

# Función para procesar el archivo de Venta PR
@st.cache_data
def load_venta_pr(file_path):
    df = pd.read_excel(file_path)
    df['Día Contable'] = pd.to_datetime(df['Día Contable'], format='%d/%m/%Y')
    return df

# Autenticar y procesar los archivos desde Google Drive
service = authenticate_drive()
folder_id = '1WzWr_OTJymi2dVRdcypTqdN9J-QLkm--'  # Reemplaza con el ID de tu carpeta en Google Drive

data, file_dates = process_data(service, folder_id)


# Función para aplicar los filtros
def apply_filters(data, proveedor, plaza, categoria, fecha):
    if proveedor:
        data = data[data['PROVEEDOR'] == proveedor]
    if plaza:
        data = data[data['PLAZA'] == plaza]
    if categoria:
        data = data[data['CATEGORIA'] == categoria]
    if fecha:
        data = data[data['Fecha'] == fecha]
    return data

# Función para aplicar la vista acumulativa
def apply_accumulated_view(data):
    accumulated_data = data.copy()
    accumulated_data = accumulated_data.groupby(['Fecha', 'PLAZA', 'DESC_ARTICULO', 'DIVISION', 'NOMBRE_TIENDA']).sum().groupby(level=[1, 2, 3, 4]).cumsum().reset_index()
    return accumulated_data

# Función para gráfico de barras de VENTA_PERDIDA_PESOS por PLAZA
def plot_venta_perdida_plaza(data):
    if 'PLAZA' not in data.columns:
        return "No se encontraron datos para la columna 'PLAZA'."
    fig = go.Figure()
    grouped_data = data.groupby('PLAZA')['VENTA_PERDIDA_PESOS'].sum().reset_index()
    fig.add_trace(go.Bar(x=grouped_data['PLAZA'], y=grouped_data['VENTA_PERDIDA_PESOS'], marker_color='rgb(26, 118, 255)'))
    fig.update_layout(title='Venta Perdida en Pesos por Plaza',
                      xaxis_title='Plaza',
                      yaxis_title='Venta Perdida (Pesos)',
                      yaxis=dict(tickformat="$,d"))
    return fig

# Función para gráfico de los artículos con más venta perdida
def plot_articulos_venta_perdida(data):
    if 'DESC_ARTICULO' not in data.columns:
        return "No se encontraron datos para la columna 'DESC_ARTICULO'."
    fig = go.Figure()
    grouped_data = data.groupby('DESC_ARTICULO')['VENTA_PERDIDA_PESOS'].sum().reset_index()
    grouped_data = grouped_data.sort_values(by='VENTA_PERDIDA_PESOS', ascending=False).head(10)
    fig.add_trace(go.Bar(x=grouped_data['DESC_ARTICULO'], y=grouped_data['VENTA_PERDIDA_PESOS'], marker_color='rgb(55, 83, 109)'))
    fig.update_layout(title='Top 10 Artículos con Más Venta Perdida en Pesos',
                      xaxis_title='Artículo',
                      yaxis_title='Venta Perdida (Pesos)',
                      yaxis=dict(tickformat="$,d"))
    return fig

# Función para gráfico de serie temporal de venta perdida por día
def plot_venta_perdida_tiempo(data, venta_pr_data):
    fig = go.Figure()
    grouped_data = data.groupby('Fecha')['VENTA_PERDIDA_PESOS'].sum().reset_index()
    fig.add_trace(go.Scatter(x=grouped_data['Fecha'], y=grouped_data['VENTA_PERDIDA_PESOS'], mode='lines+markers', name='Venta Perdida', line=dict(color='rgb(219, 64, 82)')))
    
    venta_pr_grouped = venta_pr_data.groupby('Día Contable')['Venta Neta Total'].sum().reset_index()
    fig.add_trace(go.Scatter(x=venta_pr_grouped['Día Contable'], y=venta_pr_grouped['Venta Neta Total'], mode='lines+markers', name='Venta Neta', line=dict(color='rgb(55, 128, 191)')))

    fig.update_layout(title='Venta Total vs Venta Perdida por Día',
                      xaxis_title='Fecha',
                      yaxis_title='Monto (Pesos)',
                      yaxis=dict(tickformat="$,d"))
    return fig

# Función para gráfico de serie temporal de venta perdida por día
def plot_venta_perdida(data):
    fig = go.Figure()
    grouped_data = data.groupby('Fecha')['VENTA_PERDIDA_PESOS'].sum().reset_index()
    fig.add_trace(go.Scatter(x=grouped_data['Fecha'], y=grouped_data['VENTA_PERDIDA_PESOS'], mode='lines+markers', name='Venta Perdida', line=dict(color='rgb(219, 64, 82)')))

    fig.update_layout(title='Venta Perdida por Día',
                      xaxis_title='Fecha',
                      yaxis_title='Monto (Pesos)',
                      yaxis=dict(tickformat="$,d"))
    return fig

# Función para gráfico de artículos con más venta perdida por división
def plot_articulos_por_division(data):
    if 'DIVISION' not in data.columns:
        return "No se encontraron datos para la columna 'DIVISION'."
    fig = px.treemap(data, path=['DIVISION', 'DESC_ARTICULO'], values='VENTA_PERDIDA_PESOS',
                     color='VENTA_PERDIDA_PESOS', hover_data=['VENTA_PERDIDA_PESOS'],
                     color_continuous_scale='RdBu', title='Artículos con Mayor Venta Perdida por División')
    return fig

# Función para gráfico de barras de VENTA_PERDIDA_PESOS por PROVEEDOR
def plot_venta_perdida_proveedor(data):
    if 'PROVEEDOR' not in data.columns:
        return "No se encontraron datos para la columna 'PROVEEDOR'."
    fig = go.Figure()
    grouped_data = data.groupby('PROVEEDOR')['VENTA_PERDIDA_PESOS'].sum().reset_index()
    fig.add_trace(go.Bar(x=grouped_data['PROVEEDOR'], y=grouped_data['VENTA_PERDIDA_PESOS'], marker_color='rgb(255, 165, 0)'))
    fig.update_layout(title='Venta Perdida en Pesos por Proveedor',
                      xaxis_title='Proveedor',
                      yaxis_title='Venta Perdida (Pesos)',
                      yaxis=dict(tickformat="$,d"))
    return fig

# Función para gráfico de comparación de Venta Perdida vs Venta Neta Total
def plot_comparacion_venta_perdida_vs_neta(data, venta_pr_data, filtro_fechas):
    filtered_venta_pr = venta_pr_data[venta_pr_data['Día Contable'].isin(filtro_fechas)]
    comparacion_data = pd.DataFrame({
        'Tipo de Venta': ['Venta Perdida', 'Venta Neta Total'],
        'Monto (Pesos)': [data['VENTA_PERDIDA_PESOS'].sum(), filtered_venta_pr['Venta Neta Total'].sum()]
    })
    fig = px.bar(comparacion_data, x='Tipo de Venta', y='Monto (Pesos)', text='Monto (Pesos)', color='Tipo de Venta', color_discrete_map={'Venta Perdida': 'red', 'Venta Neta Total': 'blue'})
    fig.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
    fig.update_layout(title='Comparación de Venta Perdida vs Venta Neta Total',
                      yaxis=dict(tickformat="$,d"))
    return fig

# Función para gráfico de comparación de Venta Perdida vs Venta Neta Total día por día
def plot_comparacion_venta_perdida_vs_neta_diaria(data, venta_pr_data, filtro_fechas):
    filtered_venta_pr = venta_pr_data[venta_pr_data['Día Contable'].isin(filtro_fechas)]
    comparacion_diaria = data.groupby('Fecha')['VENTA_PERDIDA_PESOS'].sum().reset_index()
    comparacion_diaria = comparacion_diaria.merge(filtered_venta_pr.groupby('Día Contable')['Venta Neta Total'].sum().reset_index(), left_on='Fecha', right_on='Día Contable')
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=comparacion_diaria['Fecha'], y=comparacion_diaria['VENTA_PERDIDA_PESOS'], mode='lines+markers', name='Venta Perdida', line=dict(color='red')))
    fig.add_trace(go.Scatter(x=comparacion_diaria['Fecha'], y=comparacion_diaria['Venta Neta Total'], mode='lines+markers', name='Venta Neta Total', line=dict(color='blue')))
    fig.update_layout(title='Comparación de Venta Perdida vs Venta Neta Total Día por Día',
                      xaxis_title='Fecha',
                      yaxis_title='Monto (Pesos)',
                      yaxis=dict(tickformat="$,d"))
    return fig

# Función para gráfico de donut
def make_donut_chart(value, total, title, color):
    percentage = (value / total) * 100
    fig = go.Figure(go.Pie(
        values=[percentage, 100 - percentage],
        labels=[title, ''],
        marker_colors=[color, '#E2E2E2'],
        hole=0.7,
        textinfo='label+percent',
    ))
    fig.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0), height=200, width=200)
    return fig

# Autenticar y procesar los archivos desde Google Drive
service = authenticate_drive()
folder_id = 'your_folder_id'  # Reemplaza con el ID de tu carpeta en Google Drive
data, file_dates = process_data(service, folder_id)
venta_pr_data = load_venta_pr(venta_pr_path)

# Mostrar dashboard si hay datos disponibles
if data is not None:
    st.sidebar.title('Configuración del Dashboard')

    # Crear dropdowns para filtros
    proveedores = st.sidebar.selectbox("Selecciona un proveedor", options=[None] + data['PROVEEDOR'].unique().tolist())
    plaza = st.sidebar.selectbox("Selecciona una plaza", options=[None] + data['PLAZA'].unique().tolist())
    categoria = st.sidebar.selectbox("Selecciona una categoría", options=[None] + data['CATEGORIA'].unique().tolist())
    fecha_opciones = [None] + sorted(file_dates) if file_dates else [None]
    fecha_seleccionada = st.sidebar.selectbox("Selecciona una fecha", options=fecha_opciones)

    # Selección de vista acumulativa o diaria
    vista = st.sidebar.radio("Selecciona la vista:", ("Diaria", "Acumulada"))

    # Aplicar filtros
    filtered_data = apply_filters(data, proveedores, plaza, categoria, fecha_seleccionada)

    # Aplicar vista acumulativa si es necesario
    if vista == "Acumulada":
        filtered_data = apply_accumulated_view(filtered_data)

    # Columnas para la disposición de gráficos
    col1, col2 = st.columns((1, 1))

    with col1:
        st.markdown('#### Venta Perdida Total')
        total_venta_perdida = data['VENTA_PERDIDA_PESOS'].sum()
        total_venta_perdida_filtrada = filtered_data['VENTA_PERDIDA_PESOS'].sum()
        st.metric(label="Total Venta Perdida", value=f"${total_venta_perdida_filtrada:,.0f}")

        st.markdown('#### Venta Perdida Acumulada')
        total_venta_perdida_acumulada = filtered_data['VENTA_PERDIDA_PESOS'].sum()
        venta_perdida_acumulada_chart = make_donut_chart(total_venta_perdida_acumulada, total_venta_perdida, 'Acumulada', 'orange')
        st.plotly_chart(venta_perdida_acumulada_chart, use_container_width=True)

    with col2:
        st.markdown('#### Comparación de Venta Perdida vs Venta Neta Total')
        comparacion_chart = plot_comparacion_venta_perdida_vs_neta(filtered_data, venta_pr_data, filtered_data['Fecha'])
        st.plotly_chart(comparacion_chart, use_container_width=True)

    # Segunda fila de gráficos
    col3, col4 = st.columns((1, 1))

    with col3:
        st.markdown('#### Venta Perdida por Día')
        venta_perdida_dia_chart = plot_venta_perdida(data)
        st.plotly_chart(venta_perdida_dia_chart, use_container_width=True)

    with col4:
        st.markdown('#### Venta Perdida en Pesos por Plaza')
        venta_perdida_plaza_chart = plot_venta_perdida_plaza(filtered_data)
        st.plotly_chart(venta_perdida_plaza_chart, use_container_width=True)

    # Tercera fila de gráficos
    col5, col6 = st.columns((1, 1))
    
    with col5:
        st.markdown('#### Top 10 Artículos con Mayor Venta Perdida')
        articulos_venta_perdida_chart = plot_articulos_venta_perdida(filtered_data)
        st.plotly_chart(articulos_venta_perdida_chart, use_container_width=True)

    with col6:
        st.markdown('#### Venta Perdida en Pesos por Proveedor')
        venta_perdida_proveedor_chart = plot_venta_perdida_proveedor(filtered_data)
        st.plotly_chart(venta_perdida_proveedor_chart, use_container_width=True)

    # Cuarta fila de gráficos
    col7, col8 = st.columns((1, 1))

    with col7:
        st.markdown('#### Artículos con Mayor Venta Perdida por División')
        articulos_por_division_chart = plot_articulos_por_division(filtered_data)
        st.plotly_chart(articulos_por_division_chart, use_container_width=True)

    with col8:
        st.markdown('#### Comparación de Venta Perdida vs Venta Neta Total Día por Día')
        comparacion_diaria_chart = plot_comparacion_venta_perdida_vs_neta_diaria(filtered_data, venta_pr_data, filtered_data['Fecha'])
        st.plotly_chart(comparacion_diaria_chart, use_container_width=True)

else:
    st.warning("No se encontraron datos en la carpeta especificada.")


