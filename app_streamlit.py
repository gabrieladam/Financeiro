# ==============================
# TABELA DETALHADA COM EDITAR/EXCLUIR
# ==============================
st.subheader("📋 Detalhamento")
for idx, row in df_filtrado.iterrows():
    cols = st.columns([2,3,1.5,2,2,1,1])
    cols[0].write(row["tipo"])
    cols[1].write(row["descricao"])
    cols[2].write(f"R$ {row['valor']:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.'))
    cols[3].write(row["data_vencimento"].strftime("%d/%m/%Y"))
    cols[4].write(row["cartao"])
    cols[5].write(f"{row['parcela_atual']}/{row['numero_parcela']}")
    
    # Botão de editar
    if cols[6].button("✏️", key=f"edit_{row['id']}"):
        st.session_state.edit_id = row["id"]
    
    # Botão de excluir
    if cols[6].button("🗑️", key=f"del_{row['id']}"):
        delete_installment(row["id"])
        st.success("Lançamento excluído!")
        st.experimental_rerun()

# Formulário de edição fora do loop, se houver item selecionado
if "edit_id" in st.session_state:
    row_edit = df_filtrado[df_filtrado["id"] == st.session_state.edit_id].iloc[0]
    with st.form("form_edit"):
        tipo_edit = st.selectbox("Tipo", tipos, index=tipos.index(row_edit["tipo"]))
        desc_edit = st.text_input("Descrição", value=row_edit["descricao"])
        valor_edit = st.number_input("Valor", min_value=0.0, value=row_edit["valor"], step=0.01)
        data_edit = st.date_input("Data de Vencimento", value=row_edit["data_vencimento"])
        parcelas_edit = st.number_input("Parcelas", min_value=1, value=row_edit["numero_parcela"])
        cartao_edit = st.text_input("Cartão", value=row_edit["cartao"])
        submitted_edit = st.form_submit_button("Salvar")
        if submitted_edit:
            update_installment(row_edit["id"], {
                "tipo": tipo_edit,
                "descricao": desc_edit,
                "valor": valor_edit,
                "data_vencimento": data_edit.strftime("%Y-%m-%d"),
                "numero_parcela": parcelas_edit,
                "cartao": cartao_edit
            })
            st.success("Lançamento atualizado!")
            del st.session_state.edit_id
            st.experimental_rerun()
