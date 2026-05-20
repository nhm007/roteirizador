import streamlit as st
import pandas as pd
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
import math

st.set_page_config(page_title="Roteirizador", layout="wide")

st.title("🚚 Roteirizador Simples")

st.write("Faça upload de um Excel com colunas: lat, lon")

file = st.file_uploader("Enviar Excel", type=["xlsx"])

def calcular_rota(df):

    coords = list(zip(df['lat'], df['lon']))

    def dist(a, b):
        return int(math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2) * 100000)

    distance_matrix = [
        [dist(a, b) for b in coords]
        for a in coords
    ]

    manager = pywrapcp.RoutingIndexManager(len(distance_matrix), 1, 0)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        return distance_matrix[
            manager.IndexToNode(from_index)
        ][
            manager.IndexToNode(to_index)
        ]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )

    solution = routing.SolveWithParameters(search_parameters)

    rota = []
    index = routing.Start(0)

    while not routing.IsEnd(index):
        node = manager.IndexToNode(index)
        rota.append(node)
        index = solution.Value(routing.NextVar(index))

    return rota


if file:
    df = pd.read_excel(file)

    st.subheader("📊 Dados carregados")
    st.dataframe(df)

    if st.button("Gerar rota otimizada"):

        rota = calcular_rota(df)

        df_rota = df.iloc[rota].reset_index(drop=True)

        st.subheader("✅ Ordem otimizada")
        st.dataframe(df_rota)

        st.success("Rota gerada com sucesso!")
