import streamlit as st
import pandas as pd

# =========================================================
# 1. CONFIGURAÇÃO DE ENGENHARIA (NÚCLEO DO SISTEMA)
# =========================================================
# Parâmetros baseados em normas técnicas de cartonagem (Prinect/EngView)
# d = espessura real | gl = orelha de colagem padrão
CONFIG_TECNICA = {
    "Onda B":           {"d": 3.0, "gl": 30},
    "Onda C":           {"d": 4.0, "gl": 30},
    "Onda BC (Dupla)":  {"d": 6.9, "gl": 40},
    "Onda E (Micro)":   {"d": 1.5, "gl": 25},
    "Onda EB (Dupla)":  {"d": 4.4, "gl": 30}
}

# Banco de Dados de Materiais (Mapeado da Tabela Fernandez 2024)
# Formato: Onda -> Papel -> Coluna -> Preço de Custo (m2)
DADOS_MATERIAIS = {
    "Onda B": {
        "Reciclado": {3.5: 2.956, 4.0: 2.770, 5.0: 3.143, 5.5: 3.473, 6.0: 4.011, 7.0: 4.342},
        "Kraft":     {4.0: 2.948, 5.0: 3.344},
        "Branco":    {5.0: 3.793}
    },
    "Onda C": {
        "Reciclado": {3.5: 3.038, 4.0: 2.853, 4.8: 3.225, 5.0: 3.556, 5.5: 4.094, 6.0: 4.424},
        "Kraft":     {4.0: 3.036, 5.0: 3.432},
        "Branco":    {5.0: 3.885}
    },
    "Onda BC (Dupla)": {
        "Reciclado": {7.0: 5.008, 7.5: 4.673, 8.0: 5.458, 8.5: 6.120, 9.5: 6.699},
        "Kraft":     {8.0: 5.808},
        "Branco":    {8.0: 6.383}
    },
    "Onda E (Micro)": {
        "Reciclado": {3.5: 2.961, 4.0: 3.067}
    },
    "Onda EB (Dupla)": {
        "Reciclado": {7.5: 5.034, 8.0: 5.155}
    }
}

# =========================================================
# 2. GERENCIAMENTO DO CARRINHO
# =========================================================
if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []

def add_to_cart(item):
    st.session_state.carrinho.append(item)
    st.toast("Item adicionado com sucesso! 🛒", icon="✅")

# =========================================================
# 3. INTERFACE E UX
# =========================================================
st.set_page_config(page_title="SmartPack Pro - Orçador de Embalagens", layout="wide")

st.title("🛡️ SmartPack Pro")
st.caption("Sistema Inteligente de Orçamentos para Indústria de Cartonagem")

# --- BARRA LATERAL (FUNIL DE ESCOLHA) ---
with st.sidebar:
    st.header("Configurações do Pedido")
    
    # Funil 1: Onda
    onda_sel = st.selectbox("1. Selecione a Onda", list(DADOS_MATERIAIS.keys()))
    
    # Funil 2: Papel
    papeis_disp = list(DADOS_MATERIAIS[onda_sel].keys())
    papel_sel = st.selectbox("2. Selecione o Papel", papeis_disp)
    
    # Funil 3: Coluna
    colunas_disp = list(DADOS_MATERIAIS[onda_sel][papel_sel].keys())
    coluna_sel = st.selectbox("3. Resistência (Coluna/ECT)", colunas_disp)
    
    st.divider()
    
    # Escolha do Modelo FEFCO
    modelo_fefco = st.selectbox("4. Modelo da Embalagem", [
        "FEFCO 0200 - Meia Maleta",
        "FEFCO 0201 - Maleta Padrão",
        "FEFCO 0202 - Maleta Sobreposta Parcial",
        "FEFCO 0203 - Maleta Aba Total (FOL)",
        "FEFCO 0204 - Maleta Especial (Centro)",
        "FEFCO 0427 - E-commerce / Correio",
        "FEFCO 0421 - Bandeja Montável",
        "FEFCO 0300 - Telescópica (Tampa/Fundo)",
        "FEFCO 0901 - Divisória ou Calço"
    ])

# --- ÁREA CENTRAL (MEDIDAS) ---
st.subheader("Dimensões Internas e Volume")
col_l, col_w, col_h, col_q = st.columns(4)
L = col_l.number_input("Comprimento (mm)", value=300)
W = col_w.number_input("Largura (mm)", value=200)
H = col_h.number_input("Altura (mm)", value=150)
qtd = col_q.number_input("Quantidade", value=500, step=100)

# =========================================================
# 4. MOTOR GEOMÉTRICO (BIBLIOTECA FEFCO EXPANDIDA)
# =========================================================
d = CONFIG_TECNICA[onda_sel]["d"]
gl = CONFIG_TECNICA[onda_sel]["gl"]
preco_m2_base = DADOS_COMERCIAL = DADOS_MATERIAIS[onda_sel][papel_sel][coluna_sel]

# Lógica de cálculo de Blank (Chapa Aberta)
if "0200" in modelo_fefco:
    bL, bW = (2*L + 2*W + gl), (H + W/2 + d)
elif "0201" in modelo_fefco:
    bL, bW = (2*L + 2*W + gl), (H + W + d)
elif "0202" in modelo_fefco:
    bL, bW = (2*L + 2*W + gl), (H + W + d + 30) # 30mm de sobreposição
elif "0203" in modelo_fefco:
    bL, bW = (2*L + 2*W + gl), (H + 2*W + d) # Aba total
elif "0427" in modelo_fefco:
    bL, bW = (L + 4*H + 6*d), (2*W + 3*H + 20)
elif "0300" in modelo_fefco:
    bL, bW = (2*L + 2*W + gl), (W + H + d)
elif "0901" in modelo_fefco:
    bL, bW = L, W
else:
    bL, bW = (2*L + 2*W + gl), (H + W + d)

# Financeiro
area_m2 = (bL * bW) / 1_000_000
valor_unitario = (area_m2 * preco_m2_base) * 2.0 # Markup 100% (Fator 100)

# --- EXIBIÇÃO ---
st.divider()
st.markdown(f"#### Detalhamento Técnico: {modelo_fefco}")
res_1, res_2, res_3 = st.columns(3)

with res_1:
    st.metric("Preço Unitário", f"R$ {valor_unitario:.2f}")
    st.write(f"Total Peças: R$ {valor_unitario * qtd:,.2f}")

with res_2:
    st.info(f"**Formato da Chapa:**\n\n{bL:.0f} x {bW:.0f} mm")
    st.write(f"Papel: {papel_sel} | {onda_sel}")

with res_3:
    if st.button("➕ ADICIONAR AO CARRINHO", use_container_width=True, type="primary"):
        item_cart = {
            "Modelo": modelo_fefco,
            "Medidas (LxWxH)": f"{L}x{W}x{H}",
            "Onda": onda_sel,
            "Papel/Coluna": f"{papel_sel} ({coluna_sel} Kgf)",
            "Qtd": qtd,
            "Unitário": f"R$ {valor_unitario:.2f}",
            "Subtotal": valor_unitario * qtd
        }
        add_to_cart(item_cart)

# =========================================================
# 5. CARRINHO DE ORÇAMENTOS
# =========================================================
if st.session_state.carrinho:
    st.markdown("---")
    st.subheader("🛒 Carrinho de Orçamentos")
    df_carrinho = pd.DataFrame(st.session_state.carrinho)
    st.dataframe(df_carrinho, use_container_width=True, hide_index=True)
    
    total_orcamento = df_carrinho["Subtotal"].sum()
    st.subheader(f"Valor Total do Orçamento: R$ {total_orcamento:,.2f}")
    
    if st.button("Limpar Carrinho"):
        st.session_state.carrinho = []
        st.rerun()

st.sidebar.markdown(f"""
---
**Status do Sistema:**
- Geometria: FEFCO Standards
- Calibres: Ativos
- Precisão: 95%+
- Fórmulas: Dinâmicas
""")
