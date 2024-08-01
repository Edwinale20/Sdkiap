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

# Function to process Venta PR file
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

    # Renombrar las columnas para coincidir con las esperadas en el código
    df = df.rename(columns={
        'Plaza': 'PLAZA',
        'DIVISION': 'DIVISION',
        'Categoría': 'CATEGORIA',
        'Artículo': 'ID_ARTICULO',
        'Semana Contable': 'Semana',
        'Venta Neta Total': 'Venta Neta Total',
        'DESC_ARTICULO': 'DESC_ARTICULO',
        'Proveedor': 'PROVEEDOR'
    })

    return df

# Función para limpiar las columnas de PLAZA y DIVISION
def clean_plaza_division(data):
    data['PLAZA'] = data['PLAZA'].astype(str).str.extract('(\d+)').astype(str)
    data['DIVISION'] = data['DIVISION'].astype(str).str.extract('(\d+)').astype(str)
    return data

# Función para convertir nombre del archivo en semana del año
def filename_to_week(filename):
    # Extraer la fecha del nombre del archivo
    date_str = filename[:8]  # Tomar los primeros 8 caracteres del nombre del archivo (ej. 01072024.csv)
    # Convertir a fecha
    date_obj = pd.to_datetime(date_str, format='%d%m%Y')
    # Obtener la semana del año (sin el año)
    week_number = date_obj.strftime('%U')
    return int(week_number)

# Function to load and combine lost sales data from the folder
@st.cache_data(show_spinner=True)
def load_venta_perdida_data(repo_owner, repo_name, folder_path):
    all_files = fetch_csv_files(repo_owner, repo_name, folder_path)
    venta_perdida_data = pd.concat([
        read_csv_from_github(repo_owner, repo_name, f"{folder_path}/{file}").assign(Semana=filename_to_week(file))
        for file in all_files
    ])
    return venta_perdida_data

# Cargar datos de Venta PR con caché
venta_pr_data = load_venta_pr(venta_pr_path)

# Limpiar las columnas PLAZA y DIVISION en ambos conjuntos de datos
venta_pr_data = clean_plaza_division(venta_pr_data)

# Cargar y combinar datos de venta perdida con caché
venta_perdida_data = load_venta_perdida_data(repo_owner, repo_name, folder_path)
venta_perdida_data = clean_plaza_division(venta_perdida_data)

# Renombrar columnas en 'venta_perdida_data' para que coincidan con 'venta_pr_data'
venta_perdida_data = venta_perdida_data.rename(columns={
    'PLAZA': 'PLAZA',
    'DIVISION': 'DIVISION',
    'CATEGORIA': 'CATEGORIA',
    'ID_ARTICULO': 'ID_ARTICULO',
    'PROVEEDOR': 'PROVEEDOR'
})

# Convertir tipos de datos antes de hacer el merge
venta_perdida_data['Semana'] = venta_perdida_data['Semana'].astype(int)
venta_pr_data['Semana'] = venta_pr_data['Semana'].astype(int)

# Incluir todos los artículos "Vuse" en la categoría RRPS
venta_perdida_data['CATEGORIA'] = venta_perdida_data.apply(
    lambda row: 'RRPS' if 'Vuse' in row['DESC_ARTICULO'] else row['CATEGORIA'], axis=1
)

# Convertir tipos de datos antes de hacer el merge
columns_to_convert = ['PLAZA', 'DIVISION', 'CATEGORIA', 'ID_ARTICULO', 'PROVEEDOR', 'Semana']

for col in columns_to_convert:
    venta_perdida_data[col] = venta_perdida_data[col].astype(str)
    venta_pr_data[col] = venta_pr_data[col].astype(str)

# Combinar datos de venta perdida con venta pr
combined_data = pd.merge(venta_perdida_data, venta_pr_data, on=columns_to_convert, how="left")


# Renombrar proveedores y eliminar proveedor dummy
proveedores_renombrados = {
    "1822 PHILIP MORRIS MEXICO, S.A. DE C.V.": "PMI",
    "1852 BRITISH AMERICAN TOBACCO MEXICO COMERCIAL, S.A. DE C.V.": "BAT",
    "6247 MAS BODEGA Y LOGISTICA, S.A. DE C.V.": "JTI",
    "21864 ARTICUN DISTRIBUIDORA S.A. DE C.V.": "Articun",
    "2216 NUEVA DISTABAC, S.A. DE C.V.": "Nueva Distabac",
    "8976 DRUGS EXPRESS, S.A DE C.V.": "Drugs Express",
    "1 PROVEEDOR DUMMY MIGRACION": "Eliminar"
}
combined_data['PROVEEDOR'] = combined_data['PROVEEDOR'].replace(proveedores_renombrados)
combined_data = combined_data[combined_data['PROVEEDOR'] != "Eliminar"]

# Sidebar para los filtros
with st.sidebar:
    st.header("Filtros")
    proveedor = st.selectbox("Proveedor", ["Todos"] + list(combined_data['PROVEEDOR'].unique()))
    plaza = st.selectbox("Plaza", ["Todas"] + list(combined_data['PLAZA'].unique()))
    categoria = st.selectbox("Categoría", ["Todas"] + list(combined_data['CATEGORIA'].unique()))
    semana = st.selectbox("Semana", ["Todas"] + list(combined_data['Semana'].unique()))
    division = st.selectbox("División", ["Todas"] + list(combined_data['DIVISION'].unique()))
    articulo = st.text_input("Artículo")

    # Selección de vista semanal o mensual
    view = st.selectbox("Selecciona la vista", ["semanal", "mensual"])
    
def apply_filters(venta_perdida_data, venta_pr_data, proveedor, plaza, categoria, semana, division, articulo):
    # Aplicar los mismos filtros a ambos conjuntos de datos
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
    if articulo:
        venta_perdida_data = venta_perdida_data[venta_perdida_data['DESC_ARTICULO'].str.contains(articulo, case=False, na=False)]
        venta_pr_data = venta_pr_data[venta_pr_data['DESC_ARTICULO'].str.contains(articulo, case=False, na=False)]
    
    # Retornar los conjuntos de datos filtrados
    return venta_perdida_data, venta_pr_data


# Filtrar datos
filtered_venta_perdida_data, filtered_venta_pr_data = apply_filters(
    venta_perdida_data,
    venta_pr_data,
    proveedor,
    plaza,
    categoria,
    semana,
    division,
    articulo
)

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

    data['Mes'] = pd.to_datetime(data['Semana'].astype(str) + '0', format='%Y%U%w').dt.to_period('M')
    monthly_data = data.groupby(['Mes', 'PROVEEDOR', 'PLAZA', 'CATEGORIA', 'DIVISION', 'ID_ARTICULO']).agg({'VENTA_PERDIDA_PESOS': 'sum'}).reset_index()
    return monthly_data
    
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

def plot_venta_perdida_plaza(filtered_venta_perdida_data, filtered_venta_pr_data):
    fig = go.Figure()

    # Sumar la venta perdida por plaza
    venta_perdida_sum = filtered_venta_perdida_data.groupby('PLAZA')['VENTA_PERDIDA_PESOS'].sum().reset_index()

    # Sumar la venta neta total por plaza
    venta_neta_sum = filtered_venta_pr_data.groupby('PLAZA')['Venta Neta Total'].sum().reset_index()

    # Crear gráfico de barras para venta perdida
    fig.add_trace(go.Bar(
        x=venta_perdida_sum['PLAZA'], 
        y=venta_perdida_sum['VENTA_PERDIDA_PESOS'], 
        name='Venta Perdida',
        marker_color='rgb(219, 64, 82)',
        text=venta_perdida_sum['VENTA_PERDIDA_PESOS'],
        textposition='auto'
    ))

    # Crear gráfico de barras para venta neta total (en otra traza)
    fig.add_trace(go.Bar(
        x=venta_neta_sum['PLAZA'], 
        y=venta_neta_sum['Venta Neta Total'], 
        name='Venta Neta Total',
        marker_color='rgb(55, 83, 109)',
        text=venta_neta_sum['Venta Neta Total'],
        textposition='auto'
    ))

    fig.update_layout(
        barmode='overlay',  # Cambia a 'group' si prefieres las barras una al lado de la otra
        title='Comparación de Venta Perdida y Venta Neta Total por Plaza',
        xaxis_title='Plaza',
        yaxis_title='Monto (Pesos)',
        yaxis=dict(tickformat="$,d"),
        legend_title_text='Tipo de Venta'
    )

    return fig



# Function to plot top 10 artículos con mayor venta perdida
def plot_articulos_venta_perdida(data):
    if 'DESC_ARTICULO' not in data.columns:
        st.warning("La columna 'DESC_ARTICULO' no está en los datos.")
        return go.Figure()  # Retorna una figura vacía si la columna no está presente

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
        yaxis=dict(tickformat="$,d")
    )
    return fig


# Function to plot venta perdida por mercado
def plot_venta_perdida_mercado(data, view):
    fig = go.Figure()

    # Verificar si la columna 'MERCADO' existe en los datos
    if 'MERCADO' not in data.columns:
        st.warning("La columna 'MERCADO' no está en los datos.")
        return fig  # Retorna una figura vacía si la columna no está presente

    if view == "semanal":
        grouped_data = data.groupby(['Semana', 'MERCADO'])['VENTA_PERDIDA_PESOS'].sum().reset_index()
        x_title = 'Semana'
    else:
        grouped_data = data.groupby(['Mes', 'MERCADO'])['VENTA_PERDIDA_PESOS'].sum().reset_index()
        x_title = 'Mes'
    mercados = grouped_data['MERCADO'].unique()
    for mercado in mercados:
        mercado_data = grouped_data[grouped_data['MERCADO'] == mercado]
        fig.add_trace(go.Scatter(
            x=mercado_data[x_title], 
            y=mercado_data['VENTA_PERDIDA_PESOS'], 
            mode='lines+markers', 
            name=mercado
        ))
    fig.update_layout(
        title=f'Venta Perdida por {x_title} y por Mercado',
        xaxis_title=x_title,
        yaxis_title='Venta Perdida (Pesos)',
        yaxis=dict(tickformat="$,d")
    )
    return fig


# Function to plot venta perdida por semana/mes
def plot_venta_perdida(data, view):
    fig = go.Figure()
    if view == "semanal":
        grouped_data = data.groupby('Semana')['VENTA_PERDIDA_PESOS'].sum().reset_index()
        x_title = 'Semana'
    else:
        grouped_data = data.groupby('Mes')['VENTA_PERDIDA_PESOS'].sum().reset_index()
        x_title = 'Mes'
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
    fig.add_trace(go.Bar(
        x=grouped_data[x_title], 
        y=grouped_data['VENTA_PERDIDA_PESOS'], 
        name='Venta Perdida', 
        marker_color='rgb(219, 64, 82)'
    ))
    fig.add_trace(go.Scatter(
        x=grouped_data[x_title], 
        y=grouped_data['Cambio (%)'], 
        mode='lines+markers', 
        name='Cambio Porcentual', 
        line=dict(color='white'), 
        yaxis='y2'
    ))
    fig.update_layout(
        title=f'Venta Perdida por {x_title} y Cambio Porcentual',
        xaxis_title=x_title,
        yaxis=dict(title='Monto (Pesos)', tickformat="$,d"),
        yaxis2=dict(title='Cambio Porcentual (%)', overlaying='y', side='right', tickformat=".2f", showgrid=False),
        legend=dict(x=0, y=1.1, orientation='h'),
        barmode='group'
    )
    return fig

# Function to plot venta perdida por proveedor
def plot_venta_perdida_proveedor(data, selected_proveedor=None):
    grouped_data = data.groupby('PROVEEDOR')['VENTA_PERDIDA_PESOS'].sum().reset_index()
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

# Validación de columnas necesarias
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

    # Visualización de KPIs
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
        st.markdown('#### 🔝 Top 10 Artículos con Mayor Venta Perdida ')
        st.plotly_chart(plot_articulos_venta_perdida(filtered_venta_perdida_data), use_container_width=True)
    
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
