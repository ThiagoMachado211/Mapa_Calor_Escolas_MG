import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
import matplotlib.colors as mcolors
from branca.element import MacroElement
from jinja2 import Template


# =====================================================================================
# Função para converter nota em cor
def nota_para_cor(valor):
    if pd.isna(valor) or valor < 0:
        return "#999999"
    valor = max(0, min(1000, valor))

    if valor <= 500:
        # Interpola de vermelho escuro (#8B0000) → vermelho claro (#FFA07A)
        frac = valor / 500
        r = 139 + frac * (255 - 139)
        g = 0 + frac * (160 - 0)
        b = 0 + frac * (122 - 0)
    else:
        # Interpola de azul claro (#ADD8E6) → azul escuro (#00008B)
        frac = (valor - 500) / 500
        r = 173 - frac * (173 - 0)
        g = 216 - frac * (216 - 0)
        b = 230 - frac * (230 - 139)

    return mcolors.to_hex((r / 255, g / 255, b / 255))
# =====================================================================================


# =====================================================================================
# Carregamento e limpeza dos dados
@st.cache_data
def carregar_dados():
    df = pd.read_csv("Dados_ENEM_2024_MG - Dados_Tratados.csv")

    # Padronização dos nomes de colunas
    df.columns = df.columns.str.strip().str.upper()
    renomear = {
        "ESCOLA": "ESCOLA",
        "CIÊNCIAS HUMANAS": "CH",
        "LINGUAGENS E CÓDIGOS": "LC",
        "CIÊNCIAS DA NATUREZA": "CN",
        "MATEMÁTICA": "MT",
        "REDAÇÃO": "REDACAO",
        "MÉDIA GERAL": "MEDIA",
        "LATITUDE": "LAT",
        "LONGITUDE": "LON",
        "REGIONAL": "REGIONAL"
    }
    for original, novo in renomear.items():
        for col in df.columns:
            if col.strip().upper() == original:
                df.rename(columns={col: novo}, inplace=True)

    colunas_notas = ["CH", "LC", "CN", "MT", "REDACAO", "MEDIA"]
    for col in colunas_notas + ["LAT", "LON"]:
        df[col] = df[col].astype(str).str.replace(",", ".").str.strip()
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["REGIONAL"] = df["REGIONAL"].astype(str).str.strip().str.upper()
    df["ESCOLA"] = df["ESCOLA"].astype(str).str.upper().str.strip()

    df = df.dropna(subset=colunas_notas + ["LAT", "LON", "REGIONAL", "ESCOLA"])

    return df, colunas_notas

# Carrega os dados
df, colunas_notas = carregar_dados()
# =====================================================================================



# === Sidebar ===
st.sidebar.title("Filtros")
opcoes_regionais = ["Todas"] + sorted(df["REGIONAL"].unique())
regional = st.sidebar.selectbox("Selecione a Regional:", opcoes_regionais)

nomes_indicadores = {
    "Ciências Humanas": "CH",
    "Linguagens e Códigos": "LC",
    "Ciências da Natureza": "CN",
    "Matemática": "MT",
    "Redação": "REDACAO",
    "Média Geral": "MEDIA"
}
indicador_nome = st.sidebar.selectbox("Área do conhecimento:", list(nomes_indicadores.keys()))
indicador = nomes_indicadores[indicador_nome]

# === Filtro de dados ===
df_filtrado = df.copy() if regional == "Todas" else df[df["REGIONAL"] == regional]
df_filtrado = df_filtrado.dropna(subset=[indicador])

# === Mapa ===
st.subheader(f"Mapa de Calor e Escolas – {indicador_nome} – {regional}")
mapa = folium.Map(location=[-19.9, -43.9], zoom_start=10, tiles="CartoDB positron")

# === Heatmap ===
heat_data = [
    [row["LAT"], row["LON"], row[indicador]]
    for _, row in df_filtrado.iterrows()
]
#HeatMap(heat_data, radius=12, blur=15).add_to(mapa)

# === Marcadores com pop-up ===
for _, row in df_filtrado.iterrows():
    popup_html = f"""
    <b>{row['ESCOLA']}</b><br>
    Ciências Humanas: {row['CH']:.2f}<br>
    Linguagens: {row['LC']:.2f}<br>
    Ciências da Natureza: {row['CN']:.2f}<br>
    Matemática: {row['MT']:.2f}<br>
    Redação: {row['REDACAO']:.2f}<br>
    Média Geral: <b>{row['MEDIA']:.2f}</b>
    """
    cor = nota_para_cor(row[indicador])
    folium.CircleMarker(
        location=[row["LAT"], row["LON"]],
        radius=6,
        color=None,
        fill=True,
        fill_color=cor,
        fill_opacity=1.0,
        popup=folium.Popup(popup_html, max_width=300)
    ).add_to(mapa)

# === Barra de cor no topo ===
color_bar = MacroElement()
color_bar._template = Template("""
{% macro html(this, kwargs) %}
<div style="
    position: fixed;
    top: 75px;
    left: 50%;
    transform: translateX(-50%);
    width: 360px;
    height: 20px;
    z-index:9999;
    border: 1px solid #999;
    background: linear-gradient(to right,
        #8B0000 0%,      /* vermelho escuro */
        #FFA07A 49.9%,   /* vermelho claro */
        #ADD8E6 50.1%,   /* azul claro */
        #00008B 100%);   /* azul escuro */
">
</div>
<div style="
    position: fixed;
    top: 100px;
    left: 50%;
    transform: translateX(-50%);
    width: 360px;
    font-size: 12px;
    color: black;
    z-index: 9999;">
    <div style="display: flex; justify-content: space-between;">
        <span>0</span>
        <span>500</span>
        <span>1000</span>
    </div>
</div>
{% endmacro %}
""")


mapa.get_root().add_child(color_bar)

# === Exibe mapa ===
st_data = st_folium(mapa, width=800, height=600)

# === Tabela com dados ===
st.markdown("### Tabela de Escolas e Desempenho")
st.dataframe(df_filtrado[["ESCOLA", "CH", "LC", "CN", "MT", "REDACAO", "MEDIA", "LAT", "LON"]])