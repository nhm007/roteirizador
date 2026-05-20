import streamlit as st
import pandas as pd
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
import math
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Roteirizador PRO", layout="wide")

st.title("🚀 Roteirizador PRO")

file = st.file_uploader("Enviar Excel", type=["xlsx"])

if "resultado" not in st.session_state:
    st.session_state.resultado = None

# distancia haversine (km)
def haversine(a, b):
    R = 6371
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    x = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(x))


def calcular_rota(df, inicio):
    coords = list(zip(df['lat'], df['lon']))
    matrix = [[int(haversine(a,b)*1000) for b in coords] for a in coords]

    manager = pywrapcp.RoutingIndexManager(len(matrix), 1, inicio)
    routing = pywrapcp.RoutingModel(manager)

    def callback(i,j):
        return matrix[manager.IndexToNode(i)][manager.IndexToNode(j)]

    transit = routing.RegisterTransitCallback(callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit)

    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.AUTOMATIC
    params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    params.time_limit.seconds = 5

    solution = routing.SolveWithParameters(params)

    rota = []
    idx = routing.Start(0)
    while not routing.IsEnd(idx):
        rota.append(manager.IndexToNode(idx))
        idx = solution.Value(routing.NextVar(idx))

    return rota


if file:
    df = pd.read_excel(file)
    df.columns = df.columns.str.lower()

    df['lat'] = pd.to_numeric(df['lat'].astype(str).str.replace(',', '.'), errors='coerce')
    df['lon'] = pd.to_numeric(df['lon'].astype(str).str.replace(',', '.'), errors='coerce')

    df = df.dropna(subset=['lat','lon'])

    if df.empty:
        st.error("Arquivo inválido")
        st.stop()

    st.dataframe(df)

    inicio = st.number_input("Ponto inicial (linha)", min_value=0, max_value=len(df)-1, value=0)

    col1, col2 = st.columns(2)
    if col1.button("Gerar rota"):
        rota = calcular_rota(df, inicio)
        res = df.iloc[rota].reset_index(drop=True)

        # calcular distância e tempo
        distancias = [0]
        tempo = [0]

        for i in range(1, len(res)):
            d = haversine((res.loc[i-1,'lat'], res.loc[i-1,'lon']), (res.loc[i,'lat'], res.loc[i,'lon']))
            distancias.append(round(d,2))
            tempo.append(round(d/60*60,2))  # 60km/h -> minutos

        res['dist_km'] = distancias
        res['tempo_min'] = tempo

        st.session_state.resultado = res

    if col2.button("Nova rota"):
        st.session_state.resultado = None


if st.session_state.resultado is not None:
    resultado = st.session_state.resultado

    st.subheader("Resultado")
    st.dataframe(resultado)

    # download excel
    excel = resultado.to_excel(index=False, engine='openpyxl')

    st.download_button("📥 Baixar Excel", data=excel, file_name="rota.xlsx")

    centro = [resultado['lat'].mean(), resultado['lon'].mean()]
    mapa = folium.Map(location=centro, zoom_start=7)

    pontos = []
    for i,row in resultado.iterrows():
        lat,lon = row['lat'], row['lon']
        pontos.append((lat,lon))
        folium.Marker([lat,lon], tooltip=f"Parada {i+1}").add_to(mapa)

    folium.PolyLine(pontos).add_to(mapa)

    st_folium(mapa, width=800, height=500)
