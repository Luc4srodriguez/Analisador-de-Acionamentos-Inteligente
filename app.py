import streamlit as st
import pandas as pd
import io
import re
import plotly.express as px

st.set_page_config(page_title="Analisador de Acionamentos", layout="wide")
st.title("📊 Analisador de Acionamentos Inteligente")

uploaded_file = st.file_uploader("📎 Envie sua planilha (apenas CSV)", type=["csv"])

def converter_para_segundos(valor):
    try:
        if pd.isna(valor) or not isinstance(valor, str) or ":" not in valor:
            return None
        h, m, s = map(int, valor.strip().split(":"))
        return h * 3600 + m * 60 + s
    except:
        return None

def converter_para_minutos(valor):
    try:
        if pd.isna(valor) or not isinstance(valor, str) or ":" not in valor:
            return None
        h, m, s = map(int, valor.strip().split(":"))
        return h * 60 + m + s / 60
    except:
        return None

def formatar_tempo_segundos(segundos):
    if segundos is None:
        return "00:00"
    minutos = int(segundos // 60)
    seg = int(segundos % 60)
    return f"{minutos:02}:{seg:02}"

def formatar_tempo_minutos(minutos_total):
    if minutos_total is None:
        return "00:00"
    minutos = int(minutos_total)
    seg = int(round((minutos_total - minutos) * 60))
    return f"{minutos:02}:{seg:02}"

def formatar_com_espacos(df):
    colunas = df.columns.tolist()
    larguras = []
    for c in colunas:
        max_larg = max(df[c].astype(str).map(len).max(), len(c))
        larguras.append(max_larg)

    linhas = []
    linha_header = ""
    for c, l in zip(colunas, larguras):
        linha_header += c.ljust(l + 2)
    linhas.append(linha_header)

    for idx, row in df.iterrows():
        linha = ""
        for c, l in zip(colunas, larguras):
            valor = str(row[c]) if pd.notna(row[c]) else ""
            linha += valor.ljust(l + 2)
        linhas.append(linha)

    return "\n".join(linhas)

def linha_valida_em_colunas(row, colunas):
    for c in colunas:
        cell = row.get(c, None)
        if isinstance(cell, str):
            if re.search(r'\w', cell):
                return True
        elif pd.notna(cell):
            return True
    return False

def definir_turno(data_hora_str):
    try:
        if pd.isna(data_hora_str):
            return "Outro"
        dt = pd.to_datetime(data_hora_str)
        hora = dt.hour
        if 7 <= hora <= 12:
            return "Manhã"
        elif 13 <= hora <= 17:
            return "Tarde"
        else:
            return "Outro"
    except:
        return "Outro"

def mostrar_tabela_grafico(df, col_name, title, emoji, cor, mostrar_todos=False):
    if col_name not in df.columns:
        return

    top_vals = df[col_name].value_counts()
    if not mostrar_todos:
        top_vals = top_vals.head(5)
    top_vals = top_vals.reset_index()
    top_vals.columns = [col_name, "count"]
    total_validos = df[col_name].dropna().shape[0]

    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader(f"{emoji} {title}")
        st.markdown(f"**Total de linhas válidas: {total_validos}**")
        st.dataframe(top_vals.set_index(col_name), use_container_width=True)

    with col2:
        fig = px.bar(
            top_vals,
            x=col_name,
            y="count",
            labels={col_name: title, "count": "Atendimentos"},
            text="count",
            title=title
        )
        fig.update_traces(textposition='outside', marker_color=cor)
        fig.update_layout(xaxis_tickangle=0, yaxis=dict(tickformat="d"), margin=dict(t=50))
        st.plotly_chart(fig, use_container_width=True)

if uploaded_file:
    try:
        content = uploaded_file.read()
        df = pd.read_csv(io.BytesIO(content), encoding="utf-8", sep=None, engine="python", on_bad_lines='skip')

        df.columns = df.columns.str.strip()
        df = df.dropna(how="all")

        colunas_necessarias = [
            "name", "group_attendants_name", "client_name", "services_catalog_name",
            "services_catalog_area_name", "services_catalog_item_name", "ticket_title",
            "duration", "waiting_time", "responsible", "rating", "created_at"
        ]

        df = df[df.apply(lambda row: linha_valida_em_colunas(row, colunas_necessarias), axis=1)]
        df = df[[col for col in colunas_necessarias if col in df.columns]]

        st.success("✅ Arquivo CSV carregado e limpo com sucesso!")

        texto_alinhado = formatar_com_espacos(df.head(20))
        st.code(texto_alinhado, language="plaintext")

        st.markdown("## 📌 Métricas Geradas Automaticamente")

        # Conversão de tempos
        df["tempo_espera_segundos"] = df["waiting_time"].apply(converter_para_segundos)
        df["duracao_minutos"] = df["duration"].apply(converter_para_minutos)
        df["rating"] = pd.to_numeric(df["rating"], errors="coerce")

        # Definir turno
        if "created_at" in df.columns:
            df["turno"] = df["created_at"].apply(definir_turno)

            st.subheader("⏰ Distribuição de Atendimentos por Turno")
            turno_counts = df["turno"].value_counts().reset_index()
            turno_counts.columns = ["turno", "count"]
            total_turno_validos = df["turno"].dropna().shape[0]

            col1, col2 = st.columns([1, 2])
            with col1:
                st.markdown(f"**Total de linhas válidas: {total_turno_validos}**")
                st.dataframe(turno_counts.set_index("turno"), use_container_width=True)
            with col2:
                fig_turno = px.bar(
                    turno_counts,
                    x="turno",
                    y="count",
                    labels={"turno": "Turno", "count": "Atendimentos"},
                    text="count",
                    title="Atendimentos por Turno (Manhã/Tarde/Outro)"
                )
                fig_turno.update_traces(textposition='outside', marker_color='mediumseagreen')
                fig_turno.update_layout(xaxis_tickangle=0, yaxis=dict(tickformat="d"), margin=dict(t=50))
                st.plotly_chart(fig_turno, use_container_width=True)

        # Mostrar os gráficos/tabelas principais
        mostrar_tabela_grafico(df, "client_name", "Clientes que Mais Acionaram", "👤", "lightgreen")
        mostrar_tabela_grafico(df, "services_catalog_name", "Catálogos de Serviços Mais Usados", "📦", "orange")
        mostrar_tabela_grafico(df, "services_catalog_item_name", "Itens do Catálogo de Serviço", "🔧", "salmon")
        mostrar_tabela_grafico(df, "ticket_title", "Títulos de Tickets", "📌", "purple")
        mostrar_tabela_grafico(df, "responsible", "Responsáveis com Mais Atendimentos", "🙋", "skyblue", mostrar_todos=True)

        # Nova: Média de avaliação por responsável
        if "responsible" in df.columns and "rating" in df.columns:
            media_por_responsavel = df.groupby("responsible")["rating"].mean().reset_index()
            media_por_responsavel = media_por_responsavel.dropna().sort_values(by="rating", ascending=False)

            st.subheader("🌟 Média de Avaliação por Responsável")
            col1, col2 = st.columns([1, 2])
            with col1:
                st.markdown(f"**Total de responsáveis com avaliação:** {media_por_responsavel.shape[0]}")
                st.dataframe(media_por_responsavel.set_index("responsible"), use_container_width=True)

            with col2:
                fig_responsavel_rating = px.bar(
                    media_por_responsavel,
                    x="responsible",
                    y="rating",
                    labels={"responsible": "Responsável", "rating": "Média de Avaliação"},
                    text=media_por_responsavel["rating"].round(2),
                    title="Média de Avaliação por Responsável"
                )
                fig_responsavel_rating.update_traces(textposition="outside", marker_color="gold")
                fig_responsavel_rating.update_layout(xaxis_tickangle=0, yaxis=dict(tickformat=".2f"))
                st.plotly_chart(fig_responsavel_rating, use_container_width=True)

        # Estatísticas finais
        st.markdown("## 📉 Estatísticas Finais")

        st.subheader("⏱️ Média Tempo de Espera (em segundos)")
        media_espera = df["tempo_espera_segundos"].dropna().mean()
        if pd.notna(media_espera):
            st.write(f"{formatar_tempo_segundos(media_espera)} segundos")
        else:
            st.write("Sem dados válidos")

        st.subheader("🕒 Média de Duração (em minutos)")
        media_duracao = df["duracao_minutos"].dropna().mean()
        if pd.notna(media_duracao):
            st.write(f"{formatar_tempo_minutos(media_duracao)} minutos")
        else:
            st.write("Sem dados válidos")

        st.subheader("⭐ Média de Avaliação (Rating)")
        media_rating = df["rating"].dropna().mean()
        if pd.notna(media_rating):
            st.write(f"{media_rating:.2f}")
        else:
            st.write("Sem dados válidos")

    except Exception as e:
        st.error(f"❌ Erro ao processar o arquivo CSV: {e}")
