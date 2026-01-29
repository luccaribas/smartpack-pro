import streamlit as st
import pandas as pd

# =========================================================
# 1. PARÂMETROS TÉCNICOS E GANHOS (PARAMETRIZAÇÃO)
# =========================================================
# d = Espessura | gl = Orelha de Cola | g_vinc = Fator de Ganho por Vinco
CONFIG_TECNICA = {
    "Onda E (Micro)":   {"d": 1.5, "gl": 25, "g_vinc": 1.0},
    "Onda B":           {"d": 3.0, "gl": 30, "g_vinc": 1.0},
    "Onda C":           {"d": 4.0, "gl": 30, "g_vinc": 1.0},
    "Onda EB (Dupla)":  {"d": 4.4, "gl": 30, "g_vinc": 1.2},
    "Onda BC (Dupla)":  {"d": 6.9, "gl": 40, "g_vinc": 1.5}
}

# Banco de Dados Fernandez 2024 (31 Opções Organizadas)
MATERIAIS = {
    "Onda B": {
        "Reciclado": {3.5: 2.956, 4.0: 2.770, 5.0: 3.143, 5.5: 3.473, 6.0: 4.011, 7.0: 4.342},
        "Kraft": {4.0: 2.948, 5.0: 3.344},
        "Branco": {4.5: 3.793}
    },
    "Onda C": {
        "Reciclado": {3.3: 3.038, 3.8: 2.853, 4.8: 3.225, 5.3: 3.556, 6.0: 4.094, 7.0: 4.424},
        "Kraft": {4.0: 3.036, 5.0: 3.432},
        "Branco": {4.5: 3.885}
    },
    "Onda BC (Dupla)": {
        "Reciclado": {6.5: 4.673, 7.0: 5.127, 8.0: 5.458, 9.0: 6.120, 10.0: 6.699},
        "Kraft": {7.0: 5.324, 8.0: 5.808},
        "Branco": {7.5: 6.383}
    },
    "Onda E (Micro)": {
        "Reciclado": {4.0: 2.961, 4.5: 3.067}
    },
    "Onda EB (Dupla)": {
        "Reciclado": {6.5: 5.034, 7.0: 5.155}
    }
}

# =========================================================
# 2. SISTEMA DE CARRINHO
# =========================================================
if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []

def add_to_cart(item):
    st.session_state.carrinho.append(item)
    st.toast("Item adicionado ao orçamento! 🛒")

# =========================================================
# 3. INTERFACE SMARTPACK PRO
# =========================================================
st.set_page_config(page_title="SmartPack Pro - Orçador Técnico", layout="wide")
st.title("🛡️ SmartPack Pro")
st.caption("Solução Profissional para Indústria de Papelão Ondulado")

with st.sidebar:
    st.header("1. Material")
    onda = st.selectbox("Onda", list(MATERIAIS.keys()))
    papel = st.selectbox("Papel", list(MATERIAIS[onda].keys()))
    coluna = st.selectbox("Coluna (ECT)", list(MATERIAIS[onda][papel].keys()))
    
    st.header("2. Modelo FEFCO")
    modelo = st.selectbox("Modelo", [
        "0200 - Meia Maleta", "0201 - Maleta Padrão", "0202 - Aba Sobreposta", 
        "0203 - Aba Total (FOL)", "0204 - Maleta Especial", "0427 - Correio/Ecommerce",
        "0421 - Bandeja Montável", "0300 - Tampa e Fundo", "0901 - Divisória"
    ])

# Parâmetros de Ajuste (Ganhos)
d = CONFIG_TECNICA[onda]["d"]
gl = CONFIG_TECNICA[onda]["gl"]
g = CONFIG_TECNICA[onda]["g_vinc"]
preco_m2 = MATERIAIS[onda][papel][coluna]

# Entrada de Medidas
st.subheader("Medidas Internas e Quantidade")
c1, c2, c3, c4 = st.columns(4)
L = c1.number_input("Comprimento (mm)", value=300)
W = c2.number_input("Largura (mm)", value=200)
H = c3.number_input("Altura (mm)", value=150)
qtd = c4.number_input("Quantidade", value=500, step=100)

# =========================================================
# 4. MOTOR DE CÁLCULO PARAMETRIZADO
# =========================================================
# Aplicando ganhos de vinco conforme padrão Prinect (PCI90)
if "0201" in modelo or "0200" in modelo or "0203" in modelo:
    # Comprimento: 4 painéis + 4 vincos + Orelha
    # Cada vinco adiciona d*g de ganho na chapa aberta
    bL = (2 * L) + (2 * W) + (4 * d * g) + gl
    
    if "0200" in modelo:
        bW = H + (W / 2) + (2 * d * g)
    elif "0203" in modelo:
        bW = H + (2 * W) + (2 * d * g)
    else: # 0201
        bW = H + W + (2 * d * g)

elif "0427" in modelo:
    bL = L + (4 * H) + (6 * d * g)
    bW = (2 * W) + (3 * H) + 20

elif "0901" in modelo:
    bL, bW = L, W

else:
    bL, bW = (2 * L) + (2 * W) + gl, H + W + d

area_m2 = (bL * bW) / 1_000_000
valor_unit = (area_m2 * preco_m2) * 2.0  # Fator 100

# =========================================================
# 5. RESULTADOS E CARRINHO
# =========================================================
st.divider()
r1, r2, r3 = st.columns(3)
with r1:
    st.metric("Venda Unitária", f"R$ {valor_unit:.2f}")
    st.write(f"Custo Material: R$ {area_m2 * preco_m2:.2f}")
with r2:
    st.info(f"**Chapa Aberta:**\n\n{bL:.0f} x {bW:.0f} mm")
    st.write(f"Ganho Aplicado: {d * g:.1f} mm por dobra")
with r3:
    if st.button("➕ ADICIONAR AO CARRINHO", type="primary"):
        add_to_cart({"Modelo": modelo, "Dimensões": f"{L}x{W}x{H}", "Material": f"{onda} {papel}", "Coluna": coluna, "Qtd": qtd, "Total": valor_unit * qtd})

if st.session_state.carrinho:
    st.markdown("### 🛒 Orçamento Consolidado")
    df = pd.DataFrame(st.session_state.carrinho)
    st.table(df)
    st.subheader(f"Total Geral: R$ {df['Total'].sum():,.2f}")
    if st.button("Limpar Carrinho"):
        st.session_state.carrinho = []
        st.rerun()
