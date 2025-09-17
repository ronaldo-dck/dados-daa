import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import re

# ---------------------------------------
# 1) Função utilitária: adicionar hachura anos pandemia
# ---------------------------------------
def adicionar_fundo_pandemia(fig, anos=[2020,2021,2022], cor="LightSalmon", opacidade=0.3):
    for ano in anos:
        fig.add_vrect(
            x0=ano - 0.5, x1=ano + 0.5,
            fillcolor=cor,
            opacity=opacidade,
            layer="below",
            line_width=0
        )
    return fig

# ---------------------------------------
# 2) Carregar e preparar os dados
# ---------------------------------------
@st.cache_data
def load_data():
    df = pd.read_csv("saida.csv", dtype=str)
    cols_num = [
        "ano","incritos_vest","incritos_sisu","incritos_provare",
        "ingressantes_vest","ingressantes_provare","ingressantes_sisu",
        "ingressantes_geral","formados_geral","formados_min",
        "vagas","ocupação"
    ]
    for c in cols_num:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c].astype(str).str.replace(",",".").str.replace("%",""), errors="coerce")

    if "Permanencia" in df.columns:
        df["Permanencia"] = df["Permanencia"].astype(str).str.replace(",",".").str.replace("%","")
        df["Permanencia"] = pd.to_numeric(df["Permanencia"], errors="coerce")

    # Extrai só o nome do curso
    def extrair_nome_curso(texto):
        if pd.isna(texto):
            return ""
        if "Letras" in texto:
            m = re.search(r"(Letras\s*-\s*[^=\-]+)", texto)
            if m:
                return m.group(1).strip()
            return "Letras"
        m = re.search(r"Curso: ([^=\-]+)", texto)
        if m:
            return m.group(1).strip()
        texto = re.sub(r"Curso: ", "", texto)
        texto = texto.split('=')[0].split('-')[0].strip()
        return texto

    df["curso_nome_base"] = df["curso"].apply(extrair_nome_curso)

    # NOVO: Extrai grau e turno, e inclui no nome do curso
    def extrair_grau(texto):
        if pd.isna(texto):
            return ""
        m = re.search(r"(Bacharelado|Licenciatura|Tecnológico)", texto, re.IGNORECASE)
        if m:
            return m.group(1).capitalize()
        return ""

    def extrair_turno(texto):
        if pd.isna(texto):
            return ""
        m = re.search(r"(Matutino|Noturno|Vespertino|Integral)", texto, re.IGNORECASE)
        if m:
            return m.group(1).capitalize()
        return ""

    df["grau"] = df["curso"].apply(extrair_grau)
    df["turno"] = df["curso"].apply(extrair_turno)

    # Sempre inclui o campus, grau e turno no nome do curso
    def curso_nome_final(row):
        nome = row["curso_nome_base"]
        campus = row["campus"]
        grau = row["grau"]
        turno = row["turno"]
        partes = [nome]
        if grau:
            partes.append(grau)
        if turno:
            partes.append(turno)
        nome_final = " - ".join(partes)
        return f"{nome_final} ({campus})"
    df["curso_nome"] = df.apply(curso_nome_final, axis=1)

    return df

df = load_data()



series_cols = ["primeiro_ano","segundo_ano","terceiro_ano","quarto_ano","quinto_ano","sexto_ano"]

# Converte as colunas para numérico, substituindo valores inválidos por NaN
for c in series_cols:
    df[c] = pd.to_numeric(df[c], errors='coerce')

# Função para contar valores válidos (não NaN e > 0)
def contar_validos(row):
    return sum((row[series_cols] != 0) & (~row[series_cols].isna()))

# Soma de primeiro a sexto ano
df['soma_series'] = df[series_cols].sum(axis=1, skipna=True)

# Quantidade de valores válidos
df['qtd_validos'] = df.apply(contar_validos, axis=1)

# Agora você pode calcular a "Permanencia" similar ao Excel, por exemplo:
# Permanencia = soma_series / qtd_validos
# Evita divisão por zero
df['Permanencia'] = df.apply(lambda x: x['soma_series'] / (x['qtd_validos'] * x['vagas']) if (x['qtd_validos'] > 0 and x['vagas'] > 0) else -1, axis=1)


# ---------------------------------------
# 3) Filtros laterais REATIVOS
# ---------------------------------------
st.sidebar.title("Filtros")

# Campus
campi = st.sidebar.multiselect(
    "Campus",
    sorted(df["campus"].dropna().unique()),
    key="campi"
)

# NOVO: Filtros de Grau e Turno
graus_opcoes = sorted(df["grau"].dropna().unique())
graus = st.sidebar.multiselect(
    "Grau",
    graus_opcoes,
    key="graus"
)

turnos_opcoes = sorted(df["turno"].dropna().unique())
turnos = st.sidebar.multiselect(
    "Turno",
    turnos_opcoes,
    key="turnos"
)

# Cursos dependentes do campus/grau/turno selecionado
df_filtro_curso = df.copy()
if campi:
    df_filtro_curso = df_filtro_curso[df_filtro_curso["campus"].isin(campi)]
if graus:
    df_filtro_curso = df_filtro_curso[df_filtro_curso["grau"].isin(graus)]
if turnos:
    df_filtro_curso = df_filtro_curso[df_filtro_curso["turno"].isin(turnos)]

cursos_opcoes = sorted(df_filtro_curso["curso_nome"].dropna().unique())

cursos = st.sidebar.multiselect(
    "Curso",
    cursos_opcoes,
    key="cursos"
)

# Anos dependentes dos filtros acima
df_filtro_ano = df_filtro_curso.copy()
if cursos:
    df_filtro_ano = df_filtro_ano[df_filtro_ano["curso_nome"].isin(cursos)]

anos_min = int(df_filtro_ano["ano"].min()) if not df_filtro_ano.empty else int(df["ano"].min())
anos_max = int(df_filtro_ano["ano"].max()) if not df_filtro_ano.empty else int(df["ano"].max())

anos = st.sidebar.slider(
    "Intervalo de Anos",
    anos_min, anos_max,
    (anos_min, anos_max),
    key="anos"
)

# Aplica os filtros reativos
df_f = df.copy()
if campi:
    df_f = df_f[df_f["campus"].isin(campi)]
if graus:
    df_f = df_f[df_f["grau"].isin(graus)]
if turnos:
    df_f = df_f[df_f["turno"].isin(turnos)]
if cursos:
    df_f = df_f[df_f["curso_nome"].isin(cursos)]
df_f = df_f[(df_f["ano"] >= anos[0]) & (df_f["ano"] <= anos[1])]

# ---------------------------------------
# 4) Tabs
# ---------------------------------------
aba1, aba2, aba3, aba4, aba5 = st.tabs([
    "📊 Visão Geral", 
    "📝 Inscrições", 
    "📂 Dados Brutos", 
    "📈 Desempenho por Turma", 
    "🎯 Desempenho de uma Turma"
])

# ---------------------- ABA 1 ----------------------
with aba1:
    st.subheader("Indicadores Gerais")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total de Ingressantes", int(df_f["ingressantes_geral"].sum(skipna=True)))
    col2.metric("Total de Formados", int(df_f["formados_geral"].sum(skipna=True)))
    permanencias_validas = df_f.loc[df_f['Permanencia'] > 0, 'Permanencia']
    col3.metric("Permanência Média (%)", f"{permanencias_validas.mean(skipna=True)*100:.1f}%")
    # NOVO: Total de vagas ofertadas
    # col4.metric("Total de Vagas Ofertadas", int(df_f["vagas"].sum(skipna=True)))

    st.subheader("Evolução de Ingressantes e Formados")
    df_plot = df_f.groupby("ano", as_index=False)[["ingressantes_geral","formados_geral"]].sum()
    fig = px.line(df_plot, x="ano", y=["ingressantes_geral","formados_geral"],
                  labels={"value":"Quantidade","variable":"Indicador"}, markers=True)
    fig = adicionar_fundo_pandemia(fig)
    st.plotly_chart(fig, use_container_width=True)

    # NOVO: Gráfico de evolução das vagas ofertadas
    st.subheader("Evolução das Vagas Ofertadas")
    df_vagas_ano = df_f.groupby("ano", as_index=False)["vagas"].sum()
    fig_vagas = px.line(df_vagas_ano, x="ano", y="vagas", markers=True,
                        labels={"vagas": "Vagas Ofertadas", "ano": "Ano"})
    fig_vagas = adicionar_fundo_pandemia(fig_vagas)
    st.plotly_chart(fig_vagas, use_container_width=True)



##############################################################

    st.subheader("Taxa de Ocupação ao longo dos anos (%)")
    
    # Calcula a média da permanência por ano, ignorando valores <= 0
    df_permanencia = (
        df_f[df_f["Permanencia"] > 0]
        .groupby("ano", as_index=False)["Permanencia"]
        .mean()
    )
    # st.dataframe(df_f)
    # st.dataframe(df_permanencia)
    
    # Multiplica somente a coluna Permanencia por 100
    df_permanencia["Permanencia"] = df_permanencia["Permanencia"] * 100
    
    # Gráfico de linha
    fig2 = px.line(
        df_permanencia,
        x="ano",
        y="Permanencia",
        markers=True,
        labels={"Permanencia": "Ocupação (%)", "ano": "Ano"}
    )
    
    # Adiciona hachura anos pandemia
    fig2 = adicionar_fundo_pandemia(fig2)
    
    # Eixo y começando em 0, topo automático, formatação inteira
    fig2.update_yaxes(range=[0, 120], tickformat=".0f")
    
    st.plotly_chart(fig2, use_container_width=True)


    st.subheader("Distribuição de Ingressantes por Tipo de Ingresso")
    tipos = ["ingressantes_vest","ingressantes_sisu","ingressantes_provare"]
    df_tipo = df_f[tipos].sum().reset_index()
    df_tipo.columns = ["Tipo","Quantidade"]
    fig3 = px.pie(df_tipo, values="Quantidade", names="Tipo", hole=0.3)
    st.plotly_chart(fig3, use_container_width=True)

    # NOVO: Gráfico de ocupação por curso se nenhum ou mais de um curso estiver selecionado
    if not cursos or len(cursos) > 1:
        st.subheader("Ocupação por Curso (período filtrado)")
        df_ocup_curso = (
            df_f[df_f["Permanencia"] > 0]
            .groupby("curso_nome", as_index=False)["Permanencia"]
            .mean()
        )
        df_ocup_curso["Permanencia"] = df_ocup_curso["Permanencia"] * 100
        df_ocup_curso = df_ocup_curso.sort_values("Permanencia", ascending=True)
        fig_ocup_curso = px.bar(
            df_ocup_curso,
            x="Permanencia",
            y="curso_nome",
            orientation="h",
            labels={"Permanencia": "Ocupação (%)", "curso_nome": "Curso"},
            text="Permanencia"
        )
        fig_ocup_curso.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_ocup_curso, use_container_width=True)

# ---------------------- ABA 2 ----------------------
with aba2:
    st.subheader("Inscrições dos Processos Seletivos")
    df_insc = df_f.groupby("ano", as_index=False)[["incritos_vest","incritos_sisu","incritos_provare"]].sum()
    fig4 = px.line(df_insc, x="ano", y=["incritos_vest","incritos_sisu","incritos_provare"],
                   labels={"value":"Inscritos","variable":"Processo Seletivo"}, markers=True)
    fig4 = adicionar_fundo_pandemia(fig4)
    st.plotly_chart(fig4, use_container_width=True)

    st.subheader("Total de Inscritos por Processo (período filtrado)")
    df_total_insc = df_f[["incritos_vest","incritos_sisu","incritos_provare"]].sum().reset_index()
    df_total_insc.columns = ["Processo","Total de Inscritos"]
    fig5 = px.bar(df_total_insc, x="Processo", y="Total de Inscritos", text="Total de Inscritos")
    st.plotly_chart(fig5, use_container_width=True)

    # st.subheader("Relação Ingressantes x Inscritos (%)")
    # df_rel = df_f.groupby("ano", as_index=False).agg({
    #     "incritos_vest":"sum","ingressantes_vest":"sum",
    #     "incritos_sisu":"sum","ingressantes_sisu":"sum",
    #     "incritos_provare":"sum","ingressantes_provare":"sum",
    # })
    # for p in ["vest","sisu","provare"]:
    #     # Agora: ingressantes / inscritos
    #     df_rel[f"rel_{p}"] = 100 * df_rel[f"ingressantes_{p}"] / df_rel[f"incritos_{p}"]
    # fig6 = px.line(df_rel, x="ano", y=["rel_vest","rel_sisu","rel_provare"],
    #                labels={"value":"Ingressantes / Inscritos (%)","variable":"Processo"}, markers=True)
    # fig6 = adicionar_fundo_pandemia(fig6)
    # st.plotly_chart(fig6, use_container_width=True)

    st.subheader("Inscritos no Vestibular por Curso")
    df_vest_curso = df_f.groupby("curso_nome", as_index=False)["incritos_vest"].sum()
    df_vest_curso = df_vest_curso.sort_values("incritos_vest", ascending=True)
    fig7 = px.bar(df_vest_curso, x="incritos_vest", y="curso_nome", orientation="h",
                  labels={"incritos_vest": "Inscritos no Vestibular", "curso_nome": "Curso"},
                  text="incritos_vest")
    fig7.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig7, use_container_width=True)

    # st.subheader("Relação Inscritos por Vaga")
    df_rel_vest_vagas = df_f.groupby("curso_nome", as_index=False)[["incritos_vest","vagas","ano"]].agg({
        "incritos_vest": "sum",
        "vagas": "sum",
        "ano": "min"  # pega o menor ano do filtro para cada curso
    })
    # Aplica a regra: dobra inscritos_por_vaga para anos >= 2014
    def concorrencia_corrigida(row):
        if row["ano"] >= 2014:
            return 2 * (row["incritos_vest"] / row["vagas"]) if row["vagas"] > 0 else 0
        else:
            return (row["incritos_vest"] / row["vagas"]) if row["vagas"] > 0 else 0
    df_rel_vest_vagas["inscritos_por_vaga"] = df_rel_vest_vagas.apply(concorrencia_corrigida, axis=1)
    df_rel_vest_vagas = df_rel_vest_vagas.sort_values("inscritos_por_vaga", ascending=True)
    fig8 = px.bar(df_rel_vest_vagas, x="inscritos_por_vaga", y="curso_nome", orientation="h",
                  labels={"inscritos_por_vaga": "Inscritos por Vaga", "curso_nome": "Curso"},
                 text="inscritos_por_vaga")
    fig8.update_layout(yaxis={'categoryorder':'total ascending'})
    fig8 = adicionar_fundo_pandemia(fig8)
    # st.plotly_chart(fig8, use_container_width=True) 

    # NOVO: Vagas ofertadas no vestibular e concorrência (inscritos por vaga)
    st.subheader("Vagas Ofertadas no Vestibular e Concorrência por Curso")

    # Calcula vagas do vestibular conforme regra: até 2013 = vagas, a partir de 2014 = vagas * 0.5
    df_f["vagas_vest"] = df_f.apply(lambda row: row["vagas"] if row["ano"] < 2014 else row["vagas"] * 0.5, axis=1)

    # Agrupa por curso
    df_vest = df_f.groupby("curso_nome", as_index=False).agg({
        "incritos_vest": "sum",
        "vagas_vest": "sum"
    })
    df_vest["concorrencia_vest"] = df_vest.apply(
        lambda row: row["incritos_vest"] / row["vagas_vest"] if row["vagas_vest"] > 0 else 0, axis=1
    )

    # Ordena por concorrência
    df_vest = df_vest.sort_values("concorrencia_vest", ascending=True)

    # Gráfico de barras duplo: vagas ofertadas (barra), concorrência (linha)
    import plotly.graph_objects as go
    fig_vest = go.Figure()
    fig_vest.add_trace(go.Bar(
        x=df_vest["concorrencia_vest"],
        y=df_vest["curso_nome"],
        orientation="h",
        name="Concorrência (Inscritos por Vaga)",
        marker_color="orange",
        text=df_vest["concorrencia_vest"].round(2),
        textposition="outside"
    ))
    fig_vest.add_trace(go.Bar(
        x=df_vest["vagas_vest"],
        y=df_vest["curso_nome"],
        orientation="h",
        name="Vagas Vestibular",
        marker_color="blue",
        text=df_vest["vagas_vest"].astype(int),
        textposition="inside"
    ))
    fig_vest.update_layout(
        barmode="group",
        xaxis_title="Quantidade",
        yaxis_title="Curso",
        legend_title="Legenda"
    )
    st.plotly_chart(fig_vest, use_container_width=True)

# ---------------------- ABA 3 ----------------------
with aba3:
    st.subheader("Dados Filtrados")
    st.dataframe(df_f, use_container_width=True)

# ---------------------- ABA 4 ----------------------
with aba4:
    series_cols = ["primeiro_ano","segundo_ano","terceiro_ano","quarto_ano","quinto_ano","sexto_ano"]
    aux = df_f[df_f["curso_nome"].isin(cursos)]
    df_series = aux.groupby(["ano", "curso_nome"])[series_cols].sum().reset_index()

    st.subheader("Evolução das Séries ao Longo dos Anos (Todas as Séries)")
    df_series_melt = df_series.melt(id_vars=["ano", "curso_nome"], value_vars=series_cols,
                                    var_name="Série", value_name="Alunos")
    fig_series_all = px.line(df_series_melt, x="ano", y="Alunos", color="Série",
                             line_dash="curso_nome", labels={"Alunos": "Quantidade de Alunos",
                                                             "ano": "Ano de Ingresso", "Série": "Série"},
                             markers=True)
    fig_series_all = adicionar_fundo_pandemia(fig_series_all)
    st.plotly_chart(fig_series_all, use_container_width=True)

    # NOVO: Gráfico de barras de formados_geral e formados_min
    st.subheader("Quantidade de Formados Geral e em Tempo Mínimo")
    df_formados = aux.groupby(["ano", "curso_nome"], as_index=False)[["formados_geral", "formados_min"]].sum()

    # Gráfico: barra de formados_geral (fundo), barra de formados_min (sobreposta)
    fig_formados = go.Figure()
    fig_formados.add_trace(go.Bar(
        x=df_formados["ano"],
        y=df_formados["formados_geral"],
        name="Formados Geral",
        marker_color="lightblue",
        text=df_formados["formados_geral"],
        textposition="outside",
    ))
    fig_formados.add_trace(go.Bar(
        x=df_formados["ano"],
        y=df_formados["formados_min"],
        name="Formados em Tempo Mínimo",
        marker_color="blue",
        text=df_formados["formados_min"],
        textposition="inside",
    ))
    fig_formados.update_layout(
        barmode="overlay",
        xaxis_title="Ano",
        yaxis_title="Quantidade",
        legend_title="Tipo de Formado"
    )
    
    fig_formados = adicionar_fundo_pandemia(fig_formados)
    st.plotly_chart(fig_formados, use_container_width=True)

# ---------------------- ABA 5 ----------------------
with aba5:
    st.subheader("Acompanhamento de uma Turma")
    st.text("Selecione o curso e o ano de ingresso para ver a evolução da turma ao longo dos anos.")

    # Seleção do curso
    cursos_disponiveis = sorted(df["curso_nome"].dropna().unique())
    if cursos_disponiveis:
        curso_turma = st.selectbox("Curso", cursos_disponiveis, key="turma_curso")
    else:
        st.warning("Não há cursos disponíveis.")
        curso_turma = None

    turma_df = pd.DataFrame()  # Inicializa vazio

    if curso_turma:
        # Seleção do ano de ingresso
        anos_disponiveis = df[df["curso_nome"] == curso_turma]["ano"].dropna().unique()
        anos_disponiveis = sorted([int(a) for a in anos_disponiveis], reverse=True)
        if anos_disponiveis:
            ano_ingresso = st.selectbox("Ano de ingresso", anos_disponiveis, key="turma_ano")
            turma_df = df[(df["curso_nome"] == curso_turma) & (df["ano"] >= ano_ingresso)]
        else:
            st.warning(f"Não há anos disponíveis para o curso {curso_turma}")
            ano_ingresso = None

    if turma_df.empty:
        st.warning("Não há dados para essa combinação de curso e ano.")
    else:
        anos_curso = 6  # padrão
        st.write(f"Duração mínima estimada do curso: **{anos_curso} anos**")

        series_map = {
            "primeiro_ano": 1,
            "segundo_ano": 2,
            "terceiro_ano": 3,
            "quarto_ano": 4,
            "quinto_ano": 5,
            "sexto_ano": 6,
        }

        evolucao = []
        ano_formatura = ano_ingresso - 1
        for i in range(anos_curso):
            col_nome = list(series_map.keys())[i]
            ano_corrente = ano_ingresso + i
            valor = df[(df["curso_nome"] == curso_turma) & (df["ano"] == ano_corrente)][col_nome].sum()
            if valor == 0:
                continue
            ano_formatura += 1
            evolucao.append({
                "Ano civil": ano_corrente,
                "Ano da turma": i + 1,
                "Matriculados": valor,
                "Formados tempo mínimo": 0
            })

        # Formados ao final do curso
        formados_total = df[(df["curso_nome"] == curso_turma) & (df["ano"] == ano_formatura)]["formados_geral"].sum()
        formados_minimo = df[(df["curso_nome"] == curso_turma) & (df["ano"] == ano_formatura)]["formados_min"].sum()
        evolucao.append({
            "Ano civil": ano_formatura,
            "Ano da turma": "Formados",
            "Matriculados": formados_total,
            "Formados tempo mínimo": formados_minimo
        })

        if formados_total == 0:
            st.warning(f"A turma de {curso_turma} do ano {ano_ingresso} ainda não atingiu o tempo mínimo de formação.\nOu se formará este ano")

        df_evolucao = pd.DataFrame(evolucao)
        df_evolucao["Matriculados"] = pd.to_numeric(df_evolucao["Matriculados"], errors="coerce").fillna(0)
        df_evolucao["Formados tempo mínimo"] = pd.to_numeric(df_evolucao["Formados tempo mínimo"], errors="coerce").fillna(0)
        st.dataframe(df_evolucao, use_container_width=True)

        # Gráfico misto linha + barras
        df_linha = df_evolucao[df_evolucao["Ano da turma"] != "Formados"]
        df_barra = df_evolucao[df_evolucao["Ano da turma"] == "Formados"]

        fig_turma = go.Figure()
        if not df_linha.empty:
            fig_turma.add_trace(go.Scatter(
                x=df_linha["Ano civil"],
                y=df_linha["Matriculados"],
                mode="lines+markers+text",
                text=df_linha["Matriculados"],
                textposition="top center",
                name="Matriculados"
            ))
        if not df_barra.empty:
            fig_turma.add_trace(go.Bar(
                x=df_barra["Ano civil"],
                y=df_barra["Matriculados"],
                text=df_barra["Matriculados"],
                textposition="outside",
                name="Formados total",
                marker_color="lightblue"
            ))
            fig_turma.add_trace(go.Bar(
                x=df_barra["Ano civil"],
                y=df_barra["Formados tempo mínimo"],
                text=df_barra["Formados tempo mínimo"],
                textposition="inside",
                name="Formados em tempo mínimo",
                marker_color="blue"
            ))

        y_max = max(
            df_evolucao["Matriculados"].max() if not df_evolucao["Matriculados"].empty else 0,
            df_evolucao["Formados tempo mínimo"].max() if not df_evolucao["Formados tempo mínimo"].empty else 0
        ) * 1.1

        fig_turma.update_layout(
            barmode="overlay",
            yaxis=dict(range=[0, y_max]),
            xaxis_title="Ano",
            yaxis_title="Alunos",
            legend_title="Legenda"
        )

        # Adiciona hachura anos pandemia
        fig_turma = adicionar_fundo_pandemia(fig_turma)
        st.plotly_chart(fig_turma, use_container_width=True)
