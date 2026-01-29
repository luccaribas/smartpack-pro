import streamlit as st
import pandas as pd

# =========================================================
# 1. PARÂMETROS TÉCNICOS (ENGENHARIA OCULTA)
# =========================================================
CONFIG_TECNICA = {
    "Onda B":           {"d": 3.0, "gl": 30},
    "Onda C":           {"d": 4.0, "gl": 30},
    "Onda BC (Dupla)":  {"d": 6.9, "gl": 40},
    "Onda E (Micro)":   {"d": 1.5, "gl": 25},
    "Onda EB (Dupla)":  {"d": 4.4, "gl": 30}
}

# Banco de Dados de Preços (Fernandez 2024 - Filtrado por Categoria)
MATERIAIS = {
    "Onda B": {
        "Papel Padrão (Reciclado)": {3.5: 2.956, 4.0: 2.770, 5.0: 3.143, 6.0: 4.011, 7.0: 4.342},
        "Papel Premium (Kraft)": {4.0: 2.948, 5.0: 3.344},
        "Papel Branco": {5.0: 3.793}
    },
    "Onda C": {
        "Papel Padrão (Reciclado)": {3.5: 3.038, 4.0: 2.853, 4.8: 3.225, 5.5: 4.094, 6.0: 4.424},
        "Papel Premium (Kraft)": {4.0: 3.036, 5.0: 3.432},
        "Papel Branco": {5.0: 3.885}
    },
    "Onda BC (Dupla)": {
        "Papel Padrão (Reciclado)": {7.0: 5.008, 7.5: 4.673, 8.0: 5.458, 9.5: 6.699},
        "Papel Premium (Kraft)": {8.0: 5.808},
        "Papel Branco": {8.0: 6.383}
    }
}

# Inicialização do Carrinho
if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []

def add_to_cart(item):
    st.session_state.carrinho.append(item)
    st.toast("Item adicionado ao carrinho! 🛒", icon="✅")

# =========================================================
# 2. INTERFACE SMARTPACK PRO (FOCO NO CLIENTE)
# =========================================================
st.set_page_config(page_title="SmartPack Pro - Orçamentos", layout="wide")
st.title("🛡️ SmartPack Pro")
st.caption("Sistema de Orçamentos de Embalagens de Alta Precisão")

with st.sidebar:
    st.header("Configure sua Caixa")
    onda_sel = st.selectbox("1. Selecione a Onda", list(MATERIAIS.keys()))
    papel_sel = st.selectbox("2. Selecione o Papel", list(MATERIAIS[onda_sel].keys()))
    
    colunas = list(MATERIAIS[onda_sel][papel_sel].keys())
    coluna_sel = st.selectbox("3. Resistência (Coluna)", colunas)
    
    st.divider()
    modelo = st.selectbox("4. Modelo da Caixa", [
        "FEFCO 0427 - Corte e Vinco (Correio)",
        "FEFCO 0201 - Maleta Padrão",
        "FEFCO 0200 - Meia Maleta"
    ])

# Recuperação de Dados
d = CONFIG_TECNICA[onda_sel]["d"]
gl = CONFIG_TECNICA[onda_sel]["gl"]
preco_m2_base = MATERIAIS[onda_sel][papel_sel][coluna_sel]

# Entrada de Medidas
st.subheader("Medidas Internas (mm)")
c1, c2, c3, c4 = st.columns(4)
L = c1.number_input("Comprimento (L)", value=300)
W = c2.number_input("Largura (W)", value=200)
H = c3.number_input("Altura (H)", value=30)
qtd = c4.number_input("Quantidade", value=500, step=100)

# =========================================================
# 3. MOTOR GEOMÉTRICO CALIBRADO (PRINECT LOGIC)
# =========================================================
if "0427" in modelo:
    # Parametrização para bater 556x528 com 300x200x30 BC
    bL = L + (4 * H) + (19.7 * d) 
    bW = (2 * W) + (3 * H) + (5.5 * d)
elif "0201" in modelo:
    bL = (2 * L) + (2 * W) + (4 * d) + gl
    bW = H + W + (2 * d)
else: # 0200
    bL = (2 * L) + (2 * W) + (4 * d) + gl
    bW = H + (W / 2) + (2 * d)

# Cálculos Financeiros
area_m2 = (bL * bW) / 1_000_000
valor_unit = (area_m2 * preco_m2_base) * 2.0 # Fator 100

# --- RESULTADOS ---
st.divider()
r1, r2, r3 = st.columns(3)
with r1:
    st.metric("Venda Unitária", f"R$ {valor_unit:.2f}")
    st.write(f"Valor Total: R$ {valor_unit * qtd:,.2f}")
with r2:
    st.info(f"**Chapa Aberta (Blank):**\n\n**{bL:.0f} x {bW:.0f} mm**")
with r3:
    if st.button("➕ ADICIONAR AO CARRINHO", type="primary", use_container_width=True):
        add_to_cart({
            "Modelo": modelo,
            "Medidas": f"{L}x{W}x{H}",
            "Onda": onda_sel,
            "Resistência": f"{coluna_sel} Kgf",
            "Qtd": qtd,
            "Unit.": f"R$ {valor_unit:.2f}",
            "Subtotal": valor_unit * qtd
        })

if st.session_state.carrinho:
    st.markdown("---")
    st.subheader("🛒 Resumo do Orçamento")
    df_carrinho = pd.DataFrame(st.session_state.carrinho)
    st.dataframe(df_carrinho, use_container_width=True, hide_index=True)
    
    total_orcamento = df_carrinho["Subtotal"].sum()
    st.markdown(f"## **Total Geral: R$ {total_orcamento:,.2f}**")
    
    if st.button("Limpar Carrinho"):
        st.session_state.carrinho = []
        st.rerun()
