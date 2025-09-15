import pandas as pd
import streamlit as st
import plotly.express as px
import re

# ---------------------------------------
# 1) Carregar e preparar os dados
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
        # Padroniza cursos de Letras: separa subcursos
        if "Letras" in texto:
            # Tenta capturar "Letras - Português/Inglês", "Letras - Espanhol", etc.
            m = re.search(r"(Letras\s*-\s*[^=\-]+)", texto)
            if m:
                return m.group(1).strip()
            # Se não encontrar subcurso, retorna apenas "Letras"
            return "Letras"
        m = re.search(r"Curso: ([^=\-]+)", texto)
        if m:
            return m.group(1).strip()
        # Se não tiver 'Curso:', tenta pegar até o primeiro '=' ou '-'
        texto = re.sub(r"Curso: ", "", texto)
        texto = texto.split('=')[0].split('-')[0].strip()
        return texto

    df["curso_nome_base"] = df["curso"].apply(extrair_nome_curso)
    curso_counts = df.groupby("curso_nome_base")["campus"].nunique()
    def curso_nome_final(row):
        nome = row["curso_nome_base"]
        campus = row["campus"]
        if curso_counts[nome] > 1:
            return f"{nome} ({campus})"
        return nome
    df["curso_nome"] = df.apply(curso_nome_final, axis=1)

    return df

df = load_data()

# ---------------------------------------
# 2) Filtros laterais
# ---------------------------------------
st.sidebar.title("Filtros")
campi = st.sidebar.multiselect("Campus", sorted(df["campus"].dropna().unique()))
cursos = st.sidebar.multiselect("Curso", sorted(df["curso_nome"].dropna().unique()))
anos = st.sidebar.slider(
    "Intervalo de Anos",
    int(df["ano"].min()), int(df["ano"].max()),
    (int(df["ano"].min()), int(df["ano"].max()))
)

df_f = df.copy()
if campi: df_f = df_f[df_f["campus"].isin(campi)]
if cursos: df_f = df_f[df_f["curso_nome"].isin(cursos)]
df_f = df_f[(df_f["ano"] >= anos[0]) & (df_f["ano"] <= anos[1])]

# ---------------------------------------
# 3) Tabs
# ---------------------------------------
aba1, aba2, aba3, aba4 = st.tabs(["📊 Visão Geral", "📝 Inscrições", "📂 Dados Brutos", "📈 Desempenho por Turma"])

# ---------------------- ABA 1 ----------------------
with aba1:
    st.subheader("Indicadores Gerais")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total de Ingressantes", int(df_f["ingressantes_geral"].sum(skipna=True)))
    col2.metric("Total de Formados", int(df_f["formados_geral"].sum(skipna=True)))
    col3.metric("Permanência Média (%)", f"{df_f['Permanencia'].mean(skipna=True):.1f}%")

    st.subheader("Evolução de Ingressantes e Formados")
    df_plot = df_f.groupby("ano", as_index=False)[["ingressantes_geral","formados_geral"]].sum()
    fig = px.line(df_plot, x="ano", y=["ingressantes_geral","formados_geral"],
                  labels={"value":"Quantidade","variable":"Indicador"}, markers=True)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Taxa de Permanência ao longo dos anos (%)")
    fig2 = px.line(
        df_f.groupby("ano", as_index=False)["Permanencia"].mean(),
        x="ano", y="Permanencia", markers=True
    )
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Distribuição de Ingressantes por Tipo de Ingresso")
    tipos = ["ingressantes_vest","ingressantes_sisu","ingressantes_provare"]
    df_tipo = df_f[tipos].sum().reset_index()
    df_tipo.columns = ["Tipo","Quantidade"]
    fig3 = px.pie(df_tipo, values="Quantidade", names="Tipo", hole=0.3)
    st.plotly_chart(fig3, use_container_width=True)

# ---------------------- ABA 2 ----------------------
with aba2:
    st.subheader("Inscrições dos Processos Seletivos")

    # Gráfico de linhas: evolução de inscritos por processo
    df_insc = df_f.groupby("ano", as_index=False)[
        ["incritos_vest","incritos_sisu","incritos_provare"]
    ].sum()
    fig4 = px.line(
        df_insc,
        x="ano",
        y=["incritos_vest","incritos_sisu","incritos_provare"],
        labels={"value":"Inscritos","variable":"Processo Seletivo"},
        markers=True
    )
    st.plotly_chart(fig4, use_container_width=True)

    st.subheader("Total de Inscritos por Processo (período filtrado)")
    df_total_insc = df_f[["incritos_vest","incritos_sisu","incritos_provare"]].sum().reset_index()
    df_total_insc.columns = ["Processo","Total de Inscritos"]
    fig5 = px.bar(df_total_insc, x="Processo", y="Total de Inscritos", text="Total de Inscritos")
    st.plotly_chart(fig5, use_container_width=True)

    st.subheader("Relação Inscritos x Ingressantes (%)")
    df_rel = df_f.groupby("ano", as_index=False).agg({
        "incritos_vest":"sum","ingressantes_vest":"sum",
        "incritos_sisu":"sum","ingressantes_sisu":"sum",
        "incritos_provare":"sum","ingressantes_provare":"sum",
    })
    for p in ["vest","sisu","provare"]:
        df_rel[f"rel_{p}"] = 100 * df_rel[f"incritos_{p}"] / df_rel[f"ingressantes_{p}"]
    fig6 = px.line(
        df_rel,
        x="ano",
        y=["rel_vest","rel_sisu","rel_provare"],
        labels={"value":"Inscritos / Ingressantes (%)","variable":"Processo"},
        markers=True
    )
    st.plotly_chart(fig6, use_container_width=True)

    # 🔹 NOVO: Gráfico de barras horizontais – inscritos no vestibular por curso
    st.subheader("Inscritos no Vestibular por Curso")
    if len(df_f["ano"].unique()) > 1:
        df_vest_curso = (
            df_f.groupby("curso_nome", as_index=False)["incritos_vest"]
            .sum()
            .sort_values("incritos_vest", ascending=True)
        )
        fig7 = px.bar(
            df_vest_curso,
            x="incritos_vest",
            y="curso_nome",
            orientation="h",
            labels={"incritos_vest": "Inscritos no Vestibular", "curso_nome": "Curso"},
            text="incritos_vest"
        )
        fig7.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig7, use_container_width=True)
    else:
        df_vest_curso = (
            df_f.groupby("curso_nome", as_index=False)["incritos_vest"]
            .sum()
            .sort_values("incritos_vest", ascending=False)
        )
        fig7 = px.bar(
            df_vest_curso,
            x="curso_nome",
            y="incritos_vest",
            orientation="v",
            labels={"incritos_vest": "Inscritos no Vestibular", "curso_nome": "Curso"},
            text="incritos_vest"
        )
        fig7.update_layout(xaxis={'categoryorder':'total descending'})
        st.plotly_chart(fig7, use_container_width=True)

    st.subheader("Relação Inscritos no Vestibular por Vaga (por Curso)")
    if len(df_f["ano"].unique()) > 1:
        df_rel_vest_vagas = (
            df_f.groupby("curso_nome", as_index=False)[["incritos_vest","vagas"]]
            .sum()
        )
        df_rel_vest_vagas["inscritos_por_vaga"] = df_rel_vest_vagas["incritos_vest"] / df_rel_vest_vagas["vagas"]
        df_rel_vest_vagas = df_rel_vest_vagas.sort_values("inscritos_por_vaga", ascending=True)
        fig8 = px.bar(
            df_rel_vest_vagas,
            x="inscritos_por_vaga",
            y="curso_nome",
            orientation="h",
            labels={"inscritos_por_vaga": "Inscritos por Vaga", "curso_nome": "Curso"},
            text="inscritos_por_vaga"
        )
        fig8.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig8, use_container_width=True)
    else:
        df_rel_vest_vagas = (
            df_f.groupby("curso_nome", as_index=False)[["incritos_vest","vagas"]]
            .sum()
        )
        df_rel_vest_vagas["inscritos_por_vaga"] = df_rel_vest_vagas["incritos_vest"] / df_rel_vest_vagas["vagas"]
        df_rel_vest_vagas = df_rel_vest_vagas.sort_values("inscritos_por_vaga", ascending=False)
        fig8 = px.bar(
            df_rel_vest_vagas,
            x="curso_nome",
            y="inscritos_por_vaga",
            orientation="v",
            labels={"inscritos_por_vaga": "Inscritos por Vaga", "curso_nome": "Curso"},
            text="inscritos_por_vaga"
        )
        fig8.update_layout(xaxis={'categoryorder':'total descending'})
        st.plotly_chart(fig8, use_container_width=True)

# ---------------------- ABA 3 ----------------------
with aba3:
    st.subheader("Dados Filtrados")
    st.dataframe(df_f)

# ---------------------- ABA 4 ----------------------
with aba4:
    st.subheader("Desempenho dos Formados por Turma")
    series_cols = ["primeiro_ano","segundo_ano","terceiro_ano","quarto_ano","quinto_ano","sexto_ano"]
    df_series = df_f.groupby(["ano", "curso_nome"])[series_cols].sum().reset_index()
    st.dataframe(df_series, use_container_width=True)

    # Gráfico único: evolução de todas as séries ao longo dos anos
    st.subheader("Evolução das Séries ao Longo dos Anos (Todas as Séries)")
    df_series_melt = df_series.melt(id_vars=["ano", "curso_nome"], value_vars=series_cols, var_name="Série", value_name="Alunos")
    fig_series_all = px.line(
        df_series_melt,
        x="ano",
        y="Alunos",
        color="Série",
        line_dash="curso_nome",
        labels={"Alunos": "Quantidade de Alunos", "ano": "Ano de Ingresso", "Série": "Série"},
        markers=True
    )
    st.plotly_chart(fig_series_all, use_container_width=True)

    # Gráfico comparando formados_geral e formados_min ao longo dos anos
    st.subheader("Formados Geral x Formados Min por Turma")
    df_formados = df_f.groupby(["ano", "curso_nome"], as_index=False)[["formados_geral","formados_min"]].sum()
    fig_formados = px.line(
        df_formados,
        x="ano",
        y=["formados_geral","formados_min"],
        color="curso_nome",
        labels={"value": "Quantidade de Formados", "ano": "Ano de Ingresso", "curso_nome": "Curso", "variable": "Indicador"},
        markers=True
    )
    st.plotly_chart(fig_formados, use_container_width=True)

    # NOVO: Tabela de taxa de permanência por turma (ano/curso)
    st.subheader("Taxa de Permanência por Turma")
    df_perm_turma = df_f.groupby(["ano", "curso_nome"], as_index=False)["Permanencia"].mean()
    df_perm_turma["Permanencia (%)"] = df_perm_turma["Permanencia"].round(1)
    st.dataframe(df_perm_turma[["ano", "curso_nome", "Permanencia (%)"]], use_container_width=True)
    fig_formados = px.line(
        df_formados,
        x="ano",
        y=["formados_geral","formados_min"],
        color="curso_nome",
        labels={"value": "Quantidade de Formados", "ano": "Ano de Ingresso", "curso_nome": "Curso", "variable": "Indicador"},
        markers=True
    )
    st.plotly_chart(fig_formados, use_container_width=True)
