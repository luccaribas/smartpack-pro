import streamlit as st
import pandas as pd
import math

# =========================================================
# 1. SMARTPACK ENGINE (O CÉREBRO UNIVERSAL)
# =========================================================
class SmartPackBackend:
    def __init__(self, csv_path='formulas_smartpack.csv'):
        try:
            self.df = pd.read_csv(csv_path, delimiter=';', dtype={'Modelo': str})
            # Remove zeros à esquerda para padronizar (ex: 0201 -> 201)
            self.df['Modelo'] = self.df['Modelo'].str.lstrip('0')
        except FileNotFoundError:
            st.error("❌ Erro CRÍTICO: 'formulas_smartpack.csv' não encontrado.")
            st.stop()

    def get_available_models(self):
        """Retorna a lista de todos os modelos disponíveis no CSV"""
        if self.df.empty: return []
        return sorted(self.df['Modelo'].unique())

    def _get_engine_variables(self, modelo, L, W, H, d):
        modelo = str(modelo).lstrip('0')
        df_model = self.df[self.df['Modelo'] == modelo]
        
        if df_model.empty: return None

        # Calibração Dinâmica
        is_maleta = modelo.startswith('2')
        calib = {
            'C90': 0.5 if is_maleta else 1.0 * d,
            'HC90': (1.7 * d) if is_maleta else 1.0 * d,
            'Glue': 0.5 if is_maleta else 1.0 * d,
            'Slot': (d + 1.0) if is_maleta else (d + 2.0)
        }

        contexto = {
            'L': float(L), 'W': float(W), 'H': float(H), 'd': lambda: float(d),
            'dtID': 1, 'dtOD': 0, 'No': 0, 'Yes': 1, 'Flat': 0, 'Round': 1, 'fd': lambda: 0,
            'sqrt': math.sqrt, 'min': min, 'max': max, 'tan': math.tan, 'atan': math.atan,
            # Funções de Correção
            'C90x': lambda *a: calib['C90'], 'C90y': lambda *a: calib['C90'],
            'HC90x': lambda *a: calib['HC90'], 'GlueCorr': lambda *a: calib['Glue'],
            'LPCorr': lambda *a: 1.0 * d, 'GLWidth': lambda *a: 35.0,
            'LSCf': lambda *a: 1.5 * d, 'SlotWidth': lambda *a: calib['Slot'],
            'LC': lambda d_val, dt, iln, oln: (iln if dt==1 else oln) * d,
            'switch': lambda cond, *args: args[1] if cond else args[0]
        }
        
        resolvidos = {}
        # 4 Passadas para resolver dependências
        for _ in range(4):
            for _, row in df_model.iterrows():
                param = row['Parametro']
                formula = str(row['Formula'])
                if param in ['L', 'W', 'H', 'UL', 'DT']: continue
                try:
                    if formula.replace('.','',1).isdigit(): val = float(formula)
                    else: val = eval(formula.replace('^', '**'), {}, contexto)
                    contexto[param] = val
                    resolvidos[param] = val
                except: pass
        return resolvidos

    def calcular_blank(self, modelo, L, W, H, d):
        vars_eng = self._get_engine_variables(modelo, L, W, H, d)
        if not vars_eng: return 0, 0 

        # --- LÓGICA DE FAMÍLIAS ---

        # 1. Família 0427 (E-commerce e similares)
        if modelo == '427':
            Lss = vars_eng.get('Lss', L + 6*d)
            Wss = vars_eng.get('Wss', W + 2*d)
            HssY = vars_eng.get('HssY', H + 2*d)
            FH1 = HssY + (1.5 * d)
            TPH = H
            DxPI = (3 * d) + 1.0
            TIFH = TPH - DxPI
            Blank_X = TIFH + Wss + HssY + Wss + FH1
            Ear = HssY + 14.0
            PH = HssY - (0.5 * d)
            Blank_Y = Ear + PH + Lss + PH + Ear
            return Blank_Y, Blank_X

        # 2. Família 02xx (Maletas - 200, 201, 203...)
        elif modelo.startswith('2'):
            Lss = vars_eng.get('Lss', L + 1.0)
            Wss = vars_eng.get('Wss', W + 1.0)
            Hss = vars_eng.get('Hss', H + (1.7*d))
            GL = vars_eng.get('GL', 35.0)
            
            Blank_X = GL + 2*(Lss + Wss)
            
            # Ajuste de abas
            Flap_Top = Wss / 2
            Flap_Bottom = Wss / 2
            if modelo == '200': Flap_Top = 0 # Meia Maleta
            elif modelo == '203': # Abas totais
                Flap_Top = Wss - d
                Flap_Bottom = Wss - d

            Blank_Y = Flap_Top + Hss + Flap_Bottom
            return Blank_X, Blank_Y
        
        # 3. Genérico (Para as outras 180 caixas)
        # Tenta achar variáveis de blank no CSV. Se não achar, usa estimativa.
        else:
            # Tenta ler variáveis prontas se existirem no CSV
            bL = vars_eng.get('L_Blank', 0)
            bW = vars_eng.get('W_Blank', 0)
            
            # Se não achou no CSV, tenta estimativa básica de Open Blank (Seguro para orçamento)
            if bL == 0: bL = vars_eng.get('Lss', L) + vars_eng.get('Wss', W) # Fallback grosseiro
            if bW == 0: bW = vars_eng.get('Hss', H) * 2
            
            return bL, bW
            # =========================================================
# 2. CONFIGURAÇÕES E DADOS
# =========================================================
st.set_page_config(page_title="SmartPack Pro", layout="wide")

# --- CORREÇÃO DO ERRO DE CACHE ---
# Mudamos o nome da função para 'load_engine_v3' para forçar
# o Streamlit a esquecer a versão antiga e carregar a nova.
@st.cache_resource
def load_engine_v3():
    return SmartPackBackend('formulas_smartpack.csv')

engine = load_engine_v3()



# Materiais e Preços (Mantidos do seu código original)
CONFIG_TECNICA = {
    "Onda B": {"d": 3.0}, "Onda C": {"d": 4.0},
    "Onda BC (Dupla)": {"d": 6.9}, "Onda E (Micro)": {"d": 1.5},
    "Onda EB (Dupla)": {"d": 4.4}
}
MATERIAIS = {
    "Onda B": {"Papel Padrão (Reciclado)": {3.5: 2.956, 4.0: 2.770, 5.0: 3.143}, "Papel Branco": {5.0: 3.793}},
    "Onda C": {"Papel Padrão (Reciclado)": {3.5: 3.038, 4.0: 2.853, 6.0: 4.424}, "Papel Branco": {5.0: 3.885}},
    "Onda BC (Dupla)": {"Papel Padrão (Reciclado)": {7.0: 5.008, 9.5: 6.699}, "Papel Branco": {8.0: 6.383}}
}

if 'carrinho' not in st.session_state: st.session_state.carrinho = []
def add_to_cart(item):
    st.session_state.carrinho.append(item)
    st.toast("Adicionado! 🛒", icon="✅")

# =========================================================
# 3. INTERFACE DINÂMICA
# =========================================================
st.title("🛡️ SmartPack Pro")
st.caption(f"📚 Biblioteca de Engenharia: {len(engine.get_available_models())} modelos carregados.")

with st.sidebar:
    st.header("1. Material")
    onda_sel = st.selectbox("Onda", list(MATERIAIS.keys()))
    papel_sel = st.selectbox("Papel", list(MATERIAIS[onda_sel].keys()))
    coluna_sel = st.selectbox("Resistência", list(MATERIAIS[onda_sel][papel_sel].keys()))
    
    st.divider()
    st.header("2. Modelo")
    
    # --- MUDANÇA PRINCIPAL AQUI ---
    # Carrega TODOS os modelos do CSV dinamicamente
    modelos_disponiveis = engine.get_available_models()
    
    # Formata para ficar bonito no menu (ex: "FEFCO 0201")
    modelo_visual = st.selectbox(
        "Selecione o Código FEFCO",
        modelos_disponiveis,
        format_func=lambda x: f"FEFCO {x.zfill(4)}" # Adiciona zeros (201 -> FEFCO 0201)
    )
    codigo_modelo = modelo_visual # O valor real já é o código (ex: "201")

espessura_d = CONFIG_TECNICA[onda_sel]["d"]
preco_m2_base = MATERIAIS[onda_sel][papel_sel][coluna_sel]

col1, col2 = st.columns([1, 2])
with col1:
    st.subheader("Medidas")
    L = st.number_input("Comprimento (mm)", value=300)
    W = st.number_input("Largura (mm)", value=200)
    H = st.number_input("Altura (mm)", value=100)
    qtd = st.number_input("Quantidade", value=500, step=100)

# =========================================================
# 4. CÁLCULO E RESULTADO
# =========================================================
bL, bW = engine.calcular_blank(codigo_modelo, L, W, H, espessura_d)

# Tratamento para modelos desconhecidos (zerados)
if bL == 0 or bW == 0:
    st.warning(f"⚠️ O modelo {codigo_modelo} não possui geometria mapeada ainda. Usando estimativa.")
    # Estimativa de segurança para não travar venda
    bL = (2*L) + (2*W) + 50
    bW = H + W + 50

area_m2 = (bL * bW) / 1_000_000
valor_unit = (area_m2 * preco_m2_base) * 2.0 # Margem

with col2:
    st.subheader("Orçamento")
    c1, c2, c3 = st.columns(3)
    c1.metric("Unitário", f"R$ {valor_unit:.2f}")
    c2.metric("Total", f"R$ {valor_unit * qtd:,.2f}")
    c3.metric("Consumo Papel", f"{area_m2:.3f} m²")
    
    st.info(f"**Engenharia:** FEFCO {codigo_modelo.zfill(4)} | Blank: {bL:.0f}x{bW:.0f} mm")
    
    if st.button("➕ ADICIONAR AO CARRINHO", type="primary", use_container_width=True):
        add_to_cart({
            "Modelo": f"FEFCO {codigo_modelo}",
            "Medidas": f"{L}x{W}x{H}",
            "Material": f"{onda_sel}",
            "Total": valor_unit * qtd
        })

if st.session_state.carrinho:
    st.markdown("---")
    st.subheader("🛒 Carrinho")
    st.dataframe(pd.DataFrame(st.session_state.carrinho), use_container_width=True, hide_index=True)
