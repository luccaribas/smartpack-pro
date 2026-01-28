import streamlit as st
import pandas as pd

# --- BANCO DE DADOS FERNANDEZ ---
PRECOS = {
    "FK1L-B": {"m2": 2.633, "gram": 360, "onda": "B", "min": 250},
    "FK2-B": {"m2": 2.801, "gram": 380, "onda": "B", "min": 250},
    "FK2-BC": {"m2": 4.864, "gram": 660, "onda": "BC", "min": 250},
    "KMK-BC": {"m2": 5.387, "gram": 660, "onda": "BC", "min": 300},
    "BMC-BC": {"m2": 6.543, "gram": 690, "onda": "BC", "min": 300}
}

st.set_page_config(page_title="New Age - Sistema de Orçamentos", layout="wide")

if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []

st.title("📦 Sistema de Orçamentos New Age")
st.markdown("Configure suas embalagens e monte seu orçamento detalhado.")

# --- 1. CONFIGURAÇÃO DO ITEM ---
with st.expander("📝 Configurar Nova Embalagem", expanded=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        modelo = st.selectbox("Modelo FEFCO", ["0201", "0200", "0427", "0426", "0901", "0903"])
        chapa = st.selectbox("Qualidade", list(PRECOS.keys()))
    with col2:
        L = st.number_input("Comp. (L) mm", value=300)
        W = st.number_input("Larg. (W) mm", value=200)
        H = st.number_input("Alt. (H) mm", value=50)
    with col3:
        qtd = st.number_input("Quantidade", value=500, step=100)

    # --- LÓGICA TÉCNICA (Prinect + Refile) ---
    info = PRECOS[chapa]
    d = 3.0 if info['onda'] == "B" else 6.5
    refile = 30 if modelo.startswith("04") else 0 # Regra de Refile New Age
    
    # Fórmulas de Geometria Extraídas dos .evr
    if modelo.startswith("02"):
        bL, bW = (2*L + 2*W + 50), (H + W + d)
    elif modelo.startswith("04"):
        bL, bW = (L + 4*H + 6*d), (2*W + 3*H + 20)
    else:
        bL, bW = L, W
    
    # Dimensões Finais da Chapa (Com Refile)
    chapa_aberta_final = f"{bL + refile:.0f} x {bW + refile:.0f} mm"
    area_m2 = ((bL + refile) * (bW + refile)) / 1_000_000
    
    # Financeiro (Fator 100)
    preco_unit = (area_m2 * info['m2']) * 2.0
    peso_item = (area_m2 * info['gram'] * qtd) / 1000

    # Preview Técnico
    st.info(f"📐 **Especificação Técnica:** Chapa aberta de **{chapa_aberta_final}** (Área: {area_m2:.3f} m²)")

    if st.button("➕ Adicionar ao Carrinho"):
        item = {
            "Modelo": modelo,
            "Medidas Internas": f"{L}x{W}x{H}",
            "Chapa Aberta": chapa_aberta_final,
            "Qualidade": chapa,
            "Qtd": qtd,
            "Unitário": f"R$ {preco_unit:.2f}",
            "Subtotal": round(preco_unit * qtd, 2),
            "Peso (kg)": round(peso_item, 2)
        }
        st.session_state.carrinho.append(item)
        st.toast("Item adicionado!")

# --- 2. CARRINHO DE COMPRAS ---
st.divider()
st.header("🛒 Resumo do Orçamento")

if st.session_state.carrinho:
    df = pd.DataFrame(st.session_state.carrinho)
    st.dataframe(df, use_container_width=True) # Dataframe interativo
    
    total_valor = df["Subtotal"].sum()
    total_peso = df["Peso (kg)"].sum()
    
    res1, res2, res3 = st.columns(3)
    res1.metric("Investimento Total", f"R$ {total_valor:.2f}")
    res2.metric("Peso Total do Pedido", f"{total_peso:.1f} kg")
    
    with res3:
        if st.button("🗑️ Esvaziar Carrinho"):
            st.session_state.carrinho = []
            st.rerun()

    # Validação Global de Mínimos
    if total_peso < 250:
        st.warning("⚠️ O peso total está abaixo do mínimo padrão (250kg). Sujeito a alteração de preço.")
    else:
        st.success("✅ Pedido com peso ideal para produção.")
else:
    st.write("Seu carrinho ainda está vazio.")
