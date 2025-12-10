#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dashboard Financeiro em Streamlit
Versão completa com edição/exclusão de lançamentos e parcelamento automático
"""
import os
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from supabase import create_client, Client
import hashlib
from dateutil.relativedelta import relativedelta
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

# ==============================
# CONFIGURAÇÃO DO SUPABASE
# ==============================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==============================
# CONFIGURAÇÃO DE ESTILO
# ==============================
st.set_page_config(
    page_title="Dashboard Financeiro",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.main { padding-top: 0rem; }
.stMetric { padding: 10px; border-radius: 10px; text-align: center; }
</style>
""", unsafe_allow_html=True)

# ==============================
# FUNÇÕES DE BANCO
# ==============================
def login(email: str, senha: str):
    senha_hash = hashlib.sha256(senha.encode()).hexdigest()
    res = supabase.table("users").select("*").eq("email", email).eq("senha", senha_hash).execute()
    if res.data:
        return True, res.data[0]
    return False, None

def criar_usuario(nome: str, email: str, senha: str):
    senha_hash = hashlib.sha256(senha.encode()).hexdigest()
    return supabase.table("users").insert({
        "nome": nome,
        "email": email,
        "senha": senha_hash
    }).execute()

def listar_installments(user_id: str):
    res = supabase.table("installments").select("*").eq("user_id", user_id).order("data_vencimento", desc=False).execute()
    return res.data

def inserir_parcelas_futuras(user_id, tipo, descricao, valor, data_venc, parcelas, cartao):
    for num in range(1, parcelas + 1):
        venc = data_venc + relativedelta(months=num-1)
        supabase.table("installments").insert({
            "user_id": user_id,
            "tipo": tipo,
            "descricao": descricao,
            "valor": float(valor),
            "data_vencimento": venc.strftime("%Y-%m-%d"),
            "numero_parcela": parcelas,
            "parcela_atual": num,
            "cartao": cartao
        }).execute()

def update_installment(installment_id, fields: dict):
    return supabase.table("installments").update(fields).eq("id", installment_id).execute()

def delete_installment(installment_id):
    return supabase.table("installments").delete().eq("id", installment_id).execute()

# ==============================
# INICIALIZAÇÃO DE SESSÃO
# ==============================
if "user" not in st.session_state:
    st.session_state.user = None
if "edit_id" not in st.session_state:
    st.session_state.edit_id = None

# ==============================
# LOGIN / REGISTRO
# ==============================
if st.session_state.user is None:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.image("https://via.placeholder.com/200?text=Financeiro", width=100)
        st.title("💰 FinanceApp")
        tab_login, tab_registro = st.tabs(["Login", "Registrar"])
        
        with tab_login:
            email_login = st.text_input("Email", key="email_login")
            senha_login = st.text_input("Senha", type="password", key="senha_login")
            if st.button("Entrar", use_container_width=True, type="primary"):
                ok, user = login(email_login, senha_login)
                if ok:
                    st.session_state.user = user
                    st.success(f"Bem-vindo, {user['nome']}!")
                    st.experimental_rerun()
                else:
                    st.error("Email ou senha incorretos!")
        
        with tab_registro:
            nome_cad = st.text_input("Nome", key="nome_cad")
            email_cad = st.text_input("Email", key="email_cad")
            senha_cad = st.text_input("Senha", type="password", key="senha_cad")
            if st.button("Criar Conta", use_container_width=True, type="primary"):
                if nome_cad and email_cad and senha_cad:
                    criar_usuario(nome_cad, email_cad, senha_cad)
                    st.success("Conta criada com sucesso! Faça login.")
                else:
                    st.warning("Preencha todos os campos!")

# ==============================
# DASHBOARD PRINCIPAL
# ==============================
else:
    user = st.session_state.user
    col_title, col_logout = st.columns([0.9,0.1])
    with col_title:
        st.title(f"💰 Dashboard Financeiro - {user['nome']}")
    with col_logout:
        if st.button("Sair"):
            st.session_state.user = None
            st.experimental_rerun()
    st.divider()
    
    # ==============================
    # SIDEBAR
    # ==============================
    with st.sidebar:
        st.header("🔍 Filtros")
        dados = listar_installments(user["id"])
        if dados:
            df = pd.DataFrame(dados)
            df["data_vencimento"] = pd.to_datetime(df["data_vencimento"])
            df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0.0)
            df["ano"] = df["data_vencimento"].dt.strftime("%Y")
            df["mes_num"] = df["data_vencimento"].dt.strftime("%m")
            df["mes_nome"] = df["data_vencimento"].dt.strftime("%B")
            
            anos = sorted(df["ano"].unique(), reverse=True)
            ano_sel = st.selectbox("Ano:", anos, index=0)
            meses_disponiveis = sorted(df[df["ano"]==ano_sel]["mes_num"].unique())
            mes_sel = st.multiselect("Mês:", meses_disponiveis, default=meses_disponiveis)
            tipos = sorted(df["tipo"].dropna().unique())
            tipo_sel = st.multiselect("Tipo:", tipos, default=tipos)
            cartoes = sorted(df["cartao"].fillna("").unique())
            cartao_sel = st.multiselect("Cartão:", cartoes, default=cartoes)
            
            df_filtrado = df[
                (df["ano"]==ano_sel) &
                (df["mes_num"].isin(mes_sel)) &
                (df["tipo"].isin(tipo_sel)) &
                (df["cartao"].isin(cartao_sel))
            ]

    # ==============================
    # MENU PRINCIPAL
    # ==============================
    menu = st.sidebar.selectbox("Menu", ["Dashboard", "Gerenciar Lançamentos", "Novo Lançamento"])

    # ==============================
    # NOVO LANÇAMENTO
    # ==============================
    if menu == "Novo Lançamento":
        st.subheader("➕ Novo Lançamento")
        with st.form("form_novo_lancamento"):
            tipo_novo = st.selectbox(
                "Tipo:", ["Mercado","Alimentação","Saude","Transporte","Carro","Casa","Emprestimo","Roupa","Lazer"]
            )
            desc_novo = st.text_input("Descrição")
            valor_novo = st.number_input("Valor", min_value=0.0, step=0.01)
            data_novo = st.date_input("Data de Vencimento")
            parcelas_novo = st.number_input("Parcelas", min_value=1, value=1)
            cartao_novo = st.text_input("Cartão")
            submitted = st.form_submit_button("Adicionar")
            if submitted:
                inserir_parcelas_futuras(
                    user["id"], tipo_novo, desc_novo, valor_novo,
                    datetime.combine(data_novo, datetime.min.time()), int(parcelas_novo), cartao_novo
                )
                st.success("Lançamento adicionado!")
                st.experimental_rerun()

    # ==============================
    # DASHBOARD
    # ==============================
    elif menu == "Dashboard":
        if not df_filtrado.empty:
            total_geral = df["valor"].sum()
            total_filtrado = df_filtrado["valor"].sum()
            media = df_filtrado["valor"].mean()
            num_transacoes = len(df_filtrado)
            total_parceladas_valor = df_filtrado[df_filtrado["numero_parcela"]>1]["valor"].sum()
            perc_parceladas_valor = (total_parceladas_valor / total_filtrado * 100) if total_filtrado>0 else 0
            
            kpi_cols = st.columns(5)
            kpi_cols[0].metric("💵 Total Geral", f"R$ {total_geral:,.2f}")
            kpi_cols[1].metric("📊 Total Filtrado", f"R$ {total_filtrado:,.2f}")
            kpi_cols[2].metric("📈 Média", f"R$ {media:,.2f}")
            kpi_cols[3].metric("📋 Transações", num_transacoes)
            kpi_cols[4].metric("📦 % Parceladas", f"{perc_parceladas_valor:.2f}%")
            st.divider()
            
            # Donut
            st.subheader("💧 Gastos por Tipo (Donut)")
            df_tipo = df_filtrado.groupby("tipo")["valor"].sum().reset_index()
            fig_pie = px.pie(df_tipo, names="tipo", values="valor", hole=0.4,
                             color_discrete_sequence=px.colors.qualitative.Pastel,
                             hover_data={"valor": ":.2f"})
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
            
            # Gastos por mês
            st.subheader("📅 Gastos por Mês")
            df_mes = df.groupby(df["data_vencimento"].dt.to_period("M"))["valor"].sum().reset_index()
            df_mes.columns = ["mes", "valor"]
            df_mes["mes"] = df_mes["mes"].astype(str)
            fig_bar = px.bar(df_mes, x="mes", y="valor", color="mes", color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_bar.update_layout(showlegend=False, xaxis_title="Mês", yaxis_title="R$")
            st.plotly_chart(fig_bar, use_container_width=True)
            
            # Gastos Mensais por Tipo (Ano Selecionado)
            st.subheader("📊 Gastos Mensais por Tipo (Ano Selecionado)")
            df_mes_tipo = df[df["ano"]==ano_sel].groupby([df["data_vencimento"].dt.to_period("M"), "tipo"])["valor"].sum().reset_index()
            df_mes_tipo["mes_ano"] = df_mes_tipo["data_vencimento"].dt.strftime("%B de %Y")
            df_mes_tipo.sort_values("data_vencimento", inplace=True)
            fig_stacked_tipo = px.bar(
                df_mes_tipo,
                x="mes_ano",
                y="valor",
                color="tipo",
                text=df_mes_tipo["tipo"] + ": R$" + df_mes_tipo["valor"].map(lambda x: f"{x:,.2f}"),
                barmode="stack",
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_stacked_tipo.update_layout(xaxis_title="Mês", yaxis_title="R$", legend_title="Tipo de Gasto", height=450)
            st.plotly_chart(fig_stacked_tipo, use_container_width=True)
            
            # Tabela detalhada
            st.subheader("📋 Detalhamento")
            df_tabela = df_filtrado[["tipo","descricao","valor","data_vencimento","cartao","parcela_atual","numero_parcela"]].copy()
            df_tabela["data_vencimento"] = df_tabela["data_vencimento"].dt.strftime("%d/%m/%Y")
            df_tabela["parcela"] = df_tabela["parcela_atual"].astype(str)+"/"+df_tabela["numero_parcela"].astype(str)
            df_tabela = df_tabela[["tipo","descricao","valor","data_vencimento","cartao","parcela"]]
            df_tabela["valor"] = df_tabela["valor"].apply(lambda x:f"R$ {x:,.2f}")
            st.dataframe(df_tabela, use_container_width=True, hide_index=True)

    # ==============================
    # GERENCIAR LANÇAMENTOS
    # ==============================
    elif menu == "Gerenciar Lançamentos":
        st.subheader("📝 Gerenciar Lançamentos")
        dados = listar_installments(user["id"])
        if dados:
            df_manage = pd.DataFrame(dados)
            df_manage["data_vencimento"] = pd.to_datetime(df_manage["data_vencimento"])
            df_manage["valor"] = pd.to_numeric(df_manage["valor"], errors="coerce").fillna(0.0)
            df_manage["parcela"] = df_manage["parcela_atual"].astype(str)+"/"+df_manage["numero_parcela"].astype(str)

            gb = GridOptionsBuilder.from_dataframe(df_manage)
            gb.configure_selection(selection_mode="single", use_checkbox=False)
            gb.configure_columns(["descricao","tipo","valor","data_vencimento","cartao","parcela"], editable=False)
            grid_options = gb.build()
            grid_response = AgGrid(
                df_manage,
                gridOptions=grid_options,
                update_mode=GridUpdateMode.SELECTION_CHANGED,
                height=400,
                allow_unsafe_jscode=True
            )

            selected = grid_response['selected_rows']
            if selected and len(selected) > 0:
                selected_id = selected[0]['id']
                st.write("Você selecionou:", selected[0]['descricao'])
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✏️ Editar"):
                        st.session_state.edit_id = selected_id
                        st.experimental_rerun()
                with col2:
                    if st.button("🗑️ Excluir"):
                        delete_installment(selected_id)
                        st.success("Lançamento excluído!")
                        st.experimental_rerun()

            # Tela de edição
            if st.session_state.edit_id:
                edit_id = st.session_state.edit_id
                row = df_manage[df_manage["id"]==edit_id].iloc[0]
                st.subheader("✏️ Editar Lançamento")
                with st.form("form_editar"):
                    tipo_edit = st.selectbox("Tipo", ["Mercado","Alimentação","Saude","Transporte","Carro","Casa","Emprestimo","Roupa","Lazer"],
                                             index=["Mercado","Alimentação","Saude","Transporte","Carro","Casa","Emprestimo","Roupa","Lazer"].index(row["tipo"]))
                    desc_edit = st.text_input("Descrição", value=row["descricao"])
                    valor_edit = st.number_input("Valor", value=row["valor"])
                    data_edit = st.date_input("Data de Vencimento", value=row["data_vencimento"])
                    parcelas_edit = st.number_input("Parcelas", min_value=1, value=row["numero_parcela"])
                    cartao_edit = st.text_input("Cartão", value=row["cartao"])
                    submitted_edit = st.form_submit_button("Salvar Alterações")
                    if submitted_edit:
                        update_installment(edit_id, {
                            "tipo": tipo_edit,
                            "descricao": desc_edit,
                            "valor": float(valor_edit),
                            "data_vencimento": data_edit.strftime("%Y-%m-%d"),
                            "numero_parcela": parcelas_edit,
                            "cartao": cartao_edit
                        })
                        # Se aumentar parcelas, adicionar as faltantes
                        if parcelas_edit > row["numero_parcela"]:
                            parcelas_faltantes = parcelas_edit - row["numero_parcela"]
                            primeira_nova = row["parcela_atual"] + 1
                            for n in range(parcelas_faltantes):
                                nova_data = datetime.combine(data_edit, datetime.min.time()) + relativedelta(months=primeira_nova+n-1)
                                supabase.table("installments").insert({
                                    "user_id": user["id"],
                                    "tipo": tipo_edit,
                                    "descricao": desc_edit,
                                    "valor": float(valor_edit),
                                    "data_vencimento": nova_data.strftime("%Y-%m-%d"),
                                    "numero_parcela": parcelas_edit,
                                    "parcela_atual": primeira_nova+n,
                                    "cartao": cartao_edit
                                }).execute()
                        st.success("Lançamento atualizado!")
                        st.session_state.edit_id = None
                        st.experimental_rerun()
