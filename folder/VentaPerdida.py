# Paso 1: Importar librerias---------------------------------------
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from io import BytesIO
import requests

# PASO 2: CONFIGURACION DE LA PAGINA Y CARGA DE DATOS---------------------------------------
st.set_page_config(page_title="Reporte de Venta Pérdida Cigarros y RRPS", page_icon="📊", layout="wide", initial_sidebar_state="expanded")
st.title("📊 Reporte de Venta Perdida Cigarros y RRPS")
st.markdown("En esta página podrás visualizar la venta pérdida día con día, por plaza, división, proveedor y otros datos que desees. Esto con el fin de dar acción y reducir la Venta pérdida")

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

# Function to fetch CSV files from GitHub
@st.cache_data(show_spinner=True)
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


# Function to load and combine lost sales data from the folder
@st.cache_data(show_spinner=True)
def load_venta_perdida_data(repo_owner, repo_name, folder_path):
    all_files = fetch_csv_files(repo_owner, repo_name, folder_path)
    venta_perdida_data = pd.concat([
        read_csv_from_github(repo_owner, repo_name, f"{folder_path}/{file}").assign(Semana=filename_to_week(file))
        for file in all_files
    ])
    return venta_perdida_data

# Cargar los datos
venta_perdida_data = load_venta_perdida_data(repo_owner, repo_name, folder_path)

# PASO 3: LIMPIEZA DE DATOS---------------------------------------
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

# Cargar los datos de venta_pr_data
venta_pr_data = load_venta_pr(venta_pr_path)

# Convertir columnas necesarias a string para evitar errores en el merge
columns_to_convert = ['PLAZA', 'DIVISION', 'CATEGORIA', 'ID_ARTICULO', 'DESC_ARTICULO', 'PROVEEDOR']

# Convertir a string solo si la columna existe en ambos DataFrames
for col in columns_to_convert:
    if col in venta_perdida_data.columns and col in venta_pr_data.columns:
        venta_perdida_data[col] = venta_perdida_data[col].astype(str)
        venta_pr_data[col] = venta_pr_data[col].astype(str)

# Realizar el merge entre los dos DataFrames en función de las columnas comunes
combined_data = pd.merge(venta_perdida_data, venta_pr_data, on=columns_to_convert, how='left')

# PASO 4: SIDEBAR Y FILTROS---------------------------------------
with st.sidebar:
    st.header("Filtros")
    proveedor = st.selectbox("Proveedor", ["Todos"] + list(combined_data['PROVEEDOR'].unique()))
    plaza = st.selectbox("Plaza", ["Todas"] + list(combined_data['PLAZA'].unique()))
    categoria = st.selectbox("Categoría", ["Todas"] + list(combined_data['CATEGORIA'].unique()))
    semana = st.selectbox("Semana", ["Todas"] + list(combined_data['Semana'].unique()))
    division = st.selectbox("División", ["Todas"] + list(combined_data['DIVISION'].unique()))
    familia = st.selectbox("Familia", ["Todas"] + list(combined_data['FAMILIA'].unique()))
    segmento = st.selectbox("Segmento", ["Todos"] + list(combined_data['SEGMENTO'].unique()))

    # Selección de vista semanal o mensual
    view = st.selectbox("Selecciona la vista", ["semanal", "mensual"])

def apply_filters(venta_perdida_data, venta_pr_data, proveedor, plaza, categoria, semana, division, familia, segmento):
    # Aplicar filtros acumulativamente
    if proveedor and proveedor != "Todos":
        venta_perdida_data = venta_perdida_data[venta_perdida_data['PROVEEDOR'] == proveedor]
        venta_pr_data = venta_pr_data[venta_pr_data['PROVEEDOR'] == proveedor]
    if plaza and plaza != "Todas":
        venta_perdida_data = venta_perdida_data[venta_perdida_data['PLAZA'] == plaza]
        venta_pr_data = venta_pr_data[venta_pr_data['PLAZA'] == plaza]
    if categoria and categoria != "Todas":
        venta_perdida_data = venta_perdida_data[venta_perdida_data['CATEGORIA'] == categoria]
        venta_pr_data = venta_pr_data[venta_pr_data['CATEGORIA'] == categoria]
    if semana and semana != "Todas":
        venta_perdida_data = venta_perdida_data[venta_perdida_data['Semana'] == str(semana)]  # Convertir a str para asegurarse
        venta_pr_data = venta_pr_data[venta_pr_data['Semana'] == str(semana)]  # Convertir a str para asegurarse
    if division and division != "Todas":
        venta_perdida_data = venta_perdida_data[venta_perdida_data['DIVISION'] == division]
        venta_pr_data = venta_pr_data[venta_pr_data['DIVISION'] == division]
    if familia and familia != "Todas":
        venta_perdida_data = venta_perdida_data[venta_perdida_data['FAMILIA'] == familia]
        venta_pr_data = venta_pr_data[venta_pr_data['FAMILIA'] == familia]
    if segmento and segmento != "Todos":
        venta_perdida_data = venta_perdida_data[venta_perdida_data['SEGMENTO'] == segmento]
        venta_pr_data = venta_pr_data[venta_pr_data['SEGMENTO'] == segmento]

    # Retornar los conjuntos de datos filtrados
    return venta_perdida_data, venta_pr_data


filtered_venta_perdida_data, filtered_venta_pr_data = apply_filters(
    venta_perdida_data,
    venta_pr_data,
    proveedor,
    plaza,
    categoria,
    semana,
    division,
    familia,
    segmento
)

# PASO 5: TIPO DE VISTA DE LA PAGINA---------------------------------------
filtered_venta_perdida_data['Mes'] = pd.to_datetime(filtered_venta_perdida_data['Semana'].astype(str) + '0', format='%Y%U%w').dt.to_period('M')

# Función para aplicar vista semanal
def apply_weekly_view(data):
    if 'VENTA_PERDIDA_PESOS' not in data.columns:
        st.error("La columna 'VENTA_PERDIDA_PESOS' no se encontró en los datos.")
        return pd.DataFrame()  # Retorna un DataFrame vacío si no se encuentra la columna

    weekly_data = data.groupby(['Semana', 'PROVEEDOR', 'PLAZA', 'CATEGORIA', 'DIVISION', 'ID_ARTICULO']).agg({'VENTA_PERDIDA_PESOS': 'sum'}).reset_index()
    return weekly_data

# Función para aplicar vista mensual
def apply_monthly_view(data):
    if 'VENTA_PERDIDA_PESOS' not in data.columns:
        st.error("La columna 'VENTA_PERDIDA_PESOS' no se encontró en los datos.")
        return pd.DataFrame()  # Retorna un DataFrame vacío si no se encuentra la columna

    if 'Mes' not in data.columns:
        st.error("La columna 'Mes' no se ha creado correctamente.")
        return pd.DataFrame()  # Retorna un DataFrame vacío si no se encuentra la columna

    monthly_data = data.groupby(['Mes', 'PROVEEDOR', 'PLAZA', 'CATEGORIA', 'DIVISION', 'ID_ARTICULO']).agg({'VENTA_PERDIDA_PESOS': 'sum'}).reset_index()
    return monthly_data

# Aplicar la vista semanal o mensual según la selección
if view == "mensual":
    filtered_venta_perdida_data = apply_monthly_view(filtered_venta_perdida_data)
else:
    filtered_venta_perdida_data = apply_weekly_view(filtered_venta_perdida_data)


# PASO 6: CREACIÓN DE GRÁFICAS---------------------------------------
def plot_comparacion_venta_perdida_vs_neta(data, venta_pr_data, view):  
    if venta_pr_data.empty:
        st.warning("No hay datos disponibles para 'Venta PR'")
        return go.Figure()

    if view == "semanal":
        venta_pr_data_grouped = venta_pr_data.groupby('Semana')['Venta Neta Total'].sum().reset_index()
        comparacion = data.groupby('Semana')['VENTA_PERDIDA_PESOS'].sum().reset_index()
        comparacion = comparacion.merge(venta_pr_data_grouped, left_on='Semana', right_on='Semana', how='left')
    else:
        venta_pr_data['Mes'] = pd.to_datetime(venta_pr_data['Semana'].astype(str) + '0', format='%Y%U%w').dt.to_period('M')
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
            marker_color='red',
            text=comparacion['Semana' if view == "semanal" else 'Mes'],
            textposition='auto'
        ),
        go.Bar(
            name='Venta No Perdida',
            x=comparacion['Semana' if view == "semanal" else 'Mes'],
            y=comparacion['Venta No Perdida'],
            marker_color='blue',
            text=comparacion['Semana' if view == "semanal" else 'Mes'],
            textposition='auto'
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

# Function to plot venta perdida con tendencia
def plot_venta_perdida_con_tendencia(data, view):
    if view == "semanal":
        grouped_data = data.groupby('Semana')['VENTA_PERDIDA_PESOS'].sum().reset_index()
        x_title = 'Semana'
    else:
        grouped_data = data.groupby('Mes')['VENTA_PERDIDA_PESOS'].sum().reset_index()
        x_title = 'Mes'

    grouped_data['Cambio (%)'] = grouped_data['VENTA_PERDIDA_PESOS'].pct_change() * 100

    fig = go.Figure()

    # Agregar barras de venta perdida
    fig.add_trace(go.Bar(
        x=grouped_data[x_title], 
        y=grouped_data['VENTA_PERDIDA_PESOS'], 
        name='Venta Perdida', 
        marker_color='rgb(219, 64, 82)'
    ))

    # Agregar línea de cambio porcentual
    fig.add_trace(go.Scatter(
        x=grouped_data[x_title], 
        y=grouped_data['Cambio (%)'], 
        mode='lines+markers', 
        name='Cambio Porcentual', 
        line=dict(color='white'), 
        yaxis='y2'
    ))

    # Configuración del layout del gráfico
    fig.update_layout(
        title=f'Venta Perdida por {x_title} y Cambio Porcentual',
        xaxis_title=x_title,
        yaxis=dict(title='Monto (Pesos)', tickformat="$,d"),
        yaxis2=dict(title='Cambio Porcentual (%)', overlaying='y', side='right', tickformat=".2f", showgrid=False),
        legend=dict(x=0, y=1.1, orientation='h'),
        barmode='group'
    )

    return fig

# Function to plot venta perdida por plaza
def plot_venta_perdida_plaza(filtered_venta_perdida_data, filtered_venta_pr_data): 
    fig = go.Figure()

    # Sumar la venta perdida y la venta neta total por plaza
    venta_perdida_sum = filtered_venta_perdida_data.groupby('PLAZA')['VENTA_PERDIDA_PESOS'].sum().reset_index()
    venta_neta_sum = filtered_venta_pr_data.groupby('PLAZA')['Venta Neta Total'].sum().reset_index()

    # Unir los DataFrames por plaza
    comparacion = pd.merge(venta_perdida_sum, venta_neta_sum, on='PLAZA')

    # Calcular el porcentaje de venta perdida
    comparacion['% Venta Perdida'] = (comparacion['VENTA_PERDIDA_PESOS'] / comparacion['Venta Neta Total']) * 100

    # Crear gráfico de barras con tooltip que incluye el porcentaje
    fig.add_trace(go.Bar(
        x=comparacion['PLAZA'], 
        y=comparacion['VENTA_PERDIDA_PESOS'], 
        text=[f"{x:.2f}%" for x in comparacion['% Venta Perdida']],
        hovertemplate='<b>%{x}</b><br>Venta Perdida: %{y:$,.2f}<br>% Venta Perdida: %{text}<extra></extra>',
        marker_color='rgb(26, 118, 255)'
    ))

    fig.update_layout(
        title='Venta Perdida por Plaza',
        xaxis_title='Plaza',
        yaxis_title='Venta Perdida (Pesos)',
        yaxis=dict(tickformat="$,d")
    )

    return fig

# Function to plot venta perdida por proveedor
def plot_venta_perdida_proveedor(data, selected_proveedor=None):
    # Aplicar nombres cortos a los proveedores si es necesario
    proveedor_labels = data['PROVEEDOR'].replace(proveedores_renombrados)
    grouped_data = data.groupby(proveedor_labels)['VENTA_PERDIDA_PESOS'].sum().reset_index()
    colors = ['gold', 'mediumturquoise', 'darkorange', 'lightgreen', 'lightblue', 'pink', 'red', 'purple', 'brown', 'gray']
    pull = [0.2 if proveedor == selected_proveedor else 0 for proveedor in grouped_data['PROVEEDOR']]
    fig = go.Figure(data=[go.Pie(
        labels=grouped_data['PROVEEDOR'], 
        values=grouped_data['VENTA_PERDIDA_PESOS'], 
        pull=pull
    )])
    fig.update_traces(
        hoverinfo='label+percent', 
        textinfo='value', 
        texttemplate='$%{value:,.0f}', 
        textfont_size=20, 
        marker=dict(colors=colors, line=dict(color='#000000', width=2))
    )
    fig.update_layout(title='Venta Perdida por Proveedor')
    return fig

# Function to make a donut chart
def make_donut_chart(value, total, title, color):
    fig = go.Figure(go.Pie(
        values=[value, total - value], 
        labels=[title, 'Restante'], 
        marker_colors=[color, '#E2E2E2'], 
        hole=0.7, 
        textinfo='label', 
        hoverinfo='label+percent'
    ))
    fig.update_traces(texttemplate='', textposition='inside')
    fig.update_layout(
        title="Proporción de la Venta Perdida Filtrada respecto al Total",
        showlegend=True,
        margin=dict(t=50, b=0, l=0, r=0),
        height=300,
        width=300
    )
    return fig
    
def plot_venta_perdida(data, view):
    if view == "semanal":
        grouped_data = data.groupby('Semana')['VENTA_PERDIDA_PESOS'].sum().reset_index()
        x_title = 'Semana'
    else:
        # Añadir esta línea para verificar si 'Mes' existe
        st.write(data.head())
        grouped_data = data.groupby('Mes')['VENTA_PERDIDA_PESOS'].sum().reset_index()
        x_title = 'Mes'
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=grouped_data[x_title], 
        y=grouped_data['VENTA_PERDIDA_PESOS'], 
        mode='lines+markers', 
        name='Venta Perdida',
        line=dict(color='rgb(219, 64, 82)')
    ))
    fig.update_layout(
        title=f'Venta Perdida por {x_title}',
        xaxis_title=x_title,
        yaxis_title='Monto (Pesos)',
        yaxis=dict(tickformat="$,d")
    )
    return fig


# Sustituyendo la gráfica de "Top 10 Artículos con Mayor Venta Perdida" por "Venta Perdida por Familia"
def plot_venta_perdida_familia(data):
    if 'FAMILIA' not in data.columns:
        st.warning("La columna 'FAMILIA' no está en los datos.")
        return go.Figure()  # Retorna una figura vacía si la columna no está presente

    fig = go.Figure()
    grouped_data = data.groupby('FAMILIA')['VENTA_PERDIDA_PESOS'].sum().reset_index()
    grouped_data = grouped_data.sort_values(by='VENTA_PERDIDA_PESOS', ascending=False)
    fig.add_trace(go.Bar(
        x=grouped_data['FAMILIA'], 
        y=grouped_data['VENTA_PERDIDA_PESOS'], 
        marker_color='rgb(55, 83, 109)'
    ))
    fig.update_layout(
        title='Venta Perdida por Familia',
        xaxis_title='Familia',
        yaxis_title='Venta Perdida (Pesos)',
        yaxis=dict(tickformat="$,d")
    )
    return fig

# Modificando la gráfica de "Venta Perdida por Mercado" para que esté aislada
def plot_venta_perdida_mercado(data):
    if 'MERCADO' not in data.columns:
        st.warning("La columna 'MERCADO' no está en los datos.")
        return go.Figure()

    grouped_data = data.groupby('MERCADO')['VENTA_PERDIDA_PESOS'].sum().reset_index()
    grouped_data = grouped_data.sort_values(by='VENTA_PERDIDA_PESOS', ascending=False)
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=grouped_data['MERCADO'],
        y=grouped_data['VENTA_PERDIDA_PESOS'],
        marker_color='rgb(26, 118, 255)',
        text=grouped_data['MERCADO'],
        textposition='auto'
    ))

    fig.update_layout(
        title='Venta Perdida por Mercado',
        xaxis_title='Mercado',
        yaxis_title='Venta Perdida (Pesos)',
        yaxis=dict(tickformat="$,d")
    )
    return fig


# PAOS 7: VALIDACIÓN DE COLUMNAS---------------------------------------
if 'VENTA_PERDIDA_PESOS' not in filtered_venta_perdida_data.columns:
    st.error("La columna 'VENTA_PERDIDA_PESOS' no se encontró en los datos filtrados.")
elif 'Venta Neta Total' not in filtered_venta_pr_data.columns:
    st.error("La columna 'Venta Neta Total' no se encontró en los datos filtrados.")
else:
    # Calcula total_venta_perdida sin filtros aplicados
    total_venta_perdida = venta_perdida_data['VENTA_PERDIDA_PESOS'].sum()  # Sumar sin filtros aplicados

# Calcula las métricas con los datos filtrados
    total_venta_perdida_filtrada = filtered_venta_perdida_data['VENTA_PERDIDA_PESOS'].sum()
    total_venta_pr_filtrada = filtered_venta_pr_data['Venta Neta Total'].sum()

    # Evitar división por cero
    if total_venta_pr_filtrada != 0:
        porcentaje_venta_perdida_dia = (total_venta_perdida_filtrada / total_venta_pr_filtrada) * 100
    else:
        porcentaje_venta_perdida_dia = 0

    # Evitar división por cero
    if total_venta_perdida != 0:
        porcentaje_acumulado = (total_venta_perdida_filtrada / total_venta_perdida) * 100
    else:
        porcentaje_acumulado = 0

# PASO 8: VISUALIZACIÒN Y CONFIGURACIÓN DE GRAFICAS---------------------------------------
    col1, col2 = st.columns((1, 1))
    with col1:
        st.markdown('#### 🧮 KPI´s de Venta Perdida ')
        st.metric(label="Proporción de la Venta Perdida Filtrada al Total", value=f"{porcentaje_acumulado:.0f}%")
        st.metric(label="Proporción de Venta Perdida respecto a la Venta Neta Total", value=f"{porcentaje_venta_perdida_dia:.3f}%")
        st.metric(label="Total Venta Perdida (21/6/2024-Presente)", value=f"${total_venta_perdida_filtrada:,.0f}")
        st.markdown(f'#### 🕰️ Venta Perdida {view} ')
        st.plotly_chart(plot_venta_perdida(filtered_venta_perdida_data, view), use_container_width=True)
    with col2:
        st.markdown('#### 📅 Venta Perdida Acumulada ')
        st.plotly_chart(make_donut_chart(total_venta_perdida_filtrada, total_venta_perdida, 'Acumulada', 'orange'), use_container_width=True)

    # Otros gráficos
    col3, col4 = st.columns((1, 1))
    with col3:
        st.markdown('#### 🏝️ Venta Perdida por Plaza ')
        st.plotly_chart(plot_venta_perdida_plaza(filtered_venta_perdida_data, filtered_venta_pr_data), use_container_width=True)
    with col4:
        st.markdown('#### 🔝 Venta perdida por familia ')
        st.plotly_chart(plot_venta_perdida_familia(filtered_venta_perdida_data), use_container_width=True)
    
    col5, col6 = st.columns((1, 1))
    with col5:
        st.markdown('#### 🚩 Venta Perdida por Proveedor ')
        st.plotly_chart(plot_venta_perdida_proveedor(filtered_venta_perdida_data), use_container_width=True)
    col7, col8 = st.columns((1, 1))
    with col7:
        st.markdown('#### 🎢 Cambio porcentual de venta perdida ')
        st.plotly_chart(plot_venta_perdida_con_tendencia(filtered_venta_perdida_data, view), use_container_width=True)
    with col8: 
        st.markdown('#### 📶 Venta Perdida vs Venta Neta Total ')
        st.plotly_chart(plot_comparacion_venta_perdida_vs_neta(filtered_venta_perdida_data, filtered_venta_pr_data, view), use_container_width=True)
    
    st.markdown(f'#### Venta Perdida {view} por Mercado')
    st.plotly_chart(plot_venta_perdida_mercado(filtered_venta_perdida_data, view), use_container_width=True)
