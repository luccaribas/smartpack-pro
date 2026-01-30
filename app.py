import streamlit as st
import pandas as pd
import math
import os

# =========================================================
# 1. ENGINE DE PRECISÃO (MAPEAMENTO DE TOPOLOGIA)
# =========================================================
class SmartPackBackend:
    def __init__(self, csv_path='formulas_smartpack.csv'):
        if os.path.exists(csv_path):
            try:
                self.df = pd.read_csv(csv_path, delimiter=';', dtype={'Modelo': str})
                self.df['Modelo'] = self.df['Modelo'].str.lstrip('0')
            except: self.df = pd.DataFrame()
        else: self.df = pd.DataFrame()

    def get_available_models(self):
        if self.df.empty: return []
        return sorted(self.df['Modelo'].unique())

    def _get_engine_variables(self, modelo, L, W, H, d):
        # ... (Mantém a lógica de leitura e cálculo de Lss/Wss/Hss) ...
        # (Para economizar espaço aqui, a lógica interna é a mesma da V9, focada em ler as variáveis)
        modelo = str(modelo).lstrip('0')
        if self.df.empty: return None
        df_model = self.df[self.df['Modelo'] == modelo]
        if df_model.empty: return None

        # Calibração de K-Factors (Ajuste Fino de Dobra)
        fam = modelo[0]
        k = {'C90': 0.5, 'HC90': 1.7*d, 'Glue': 0.5, 'Slot': d+1.0} if fam in ['2','5','6','7'] else {'C90': 1.0*d, 'HC90': 1.0*d, 'Glue': 1.0*d, 'Slot': d+2.0}
        
        contexto = {
            'L': float(L), 'W': float(W), 'H': float(H), 'd': lambda: float(d),
            'dtID': 1, 'dtOD': 0, 'No': 0, 'Yes': 1, 'Flat': 0, 'Round': 1, 'fd': lambda: 0,
            'sqrt': math.sqrt, 'min': min, 'max': max, 'tan': math.tan, 'atan': math.atan,
            'C90x': lambda *a: k['C90'], 'C90y': lambda *a: k['C90'], 'HC90x': lambda *a: k['HC90'], 
            'GlueCorr': lambda *a: k['Glue'], 'LPCorr': lambda *a: 1.0*d, 'GLWidth': lambda *a: 35.0,
            'LSCf': lambda *a: 1.5*d, 'SlotWidth': lambda *a: k['Slot'],
            'LC': lambda d_val, dt, iln, oln: (iln if dt==1 else oln) * d,
            'switch': lambda cond, *args: args[1] if cond else args[0]
        }
        
        resolvidos = {}
        for _ in range(5):
            for _, row in df_model.iterrows():
                try:
                    param = row['Parametro']
                    formula = str(row['Formula'])
                    if param in ['L', 'W', 'H']: continue
                    if formula.replace('.','',1).isdigit(): val = float(formula)
                    else: val = eval(formula.replace('^', '**'), {}, contexto)
                    contexto[param] = val
                    resolvidos[param] = val
                except: pass
        return resolvidos

    def calcular_blank(self, modelo, L, W, H, d):
        vars_eng = self._get_engine_variables(modelo, L, W, H, d)
        if not vars_eng: return 0, 0, "Erro: Modelo não encontrado"

        # Recupera dimensões exatas de vinco (Score-to-Score)
        # Se o CSV falhar, usa fallback seguro
        Lss = vars_eng.get('Lss', L + d)
        Wss = vars_eng.get('Wss', W + d)
        Hss = vars_eng.get('Hss', H + (1.7*d if modelo[0] in ['2','5','7'] else d))
        
        # --- LÓGICA DE TOPOLOGIA AVANÇADA (A MÁGICA DA PRECISÃO) ---
        
        # FAMÍLIA 02xx (Maletas e Tubos)
        if modelo.startswith('2'):
            GL = vars_eng.get('GL', 35.0)
            Blank_X = GL + 2*(Lss + Wss)
            
            # Altura varia conforme o fechamento do fundo
            if modelo in ['200']: # Meia Maleta
                Blank_Y = Hss + (Wss * 0.5) 
                return Blank_X, Blank_Y, "Maleta Aberta (HSC)"
            elif modelo in ['215', '216', '217']: # Fundo Snap-Lock (Complexo)
                # Fundo precisa de travamento (aprox 75% da largura)
                Blank_Y = (Wss * 0.5) + Hss + (Wss * 0.75)
                return Blank_X, Blank_Y, "Fundo Snap-Lock (Travamento)"
            else: # 201, 202, 203 (Padrão)
                Blank_Y = Hss + Wss # (0.5 Topo + 0.5 Fundo = 1.0 W)
                return Blank_X, Blank_Y, "Maleta Padrão (RSC)"

        # FAMÍLIA 07xx (Coladas / Fundo Automático)
        elif modelo.startswith('7'):
            GL = vars_eng.get('GL', 35.0)
            Blank_X = GL + 2*(Lss + Wss)
            
            # Fundo Automático consome muito papel para dobrar
            # Regra de Ouro: Fundo = 0.75 * W + Sangria
            Blank_Y = (Wss * 0.5) + Hss + (Wss * 0.8) 
            return Blank_X, Blank_Y, "Fundo Automático (Crash Lock)"

        # FAMÍLIA 04xx (Envoltórios e E-commerce)
        elif modelo.startswith('4'):
            if modelo == '427' or modelo == '426': # E-commerce Clássico
                # Geometria Gold
                HssY = vars_eng.get('HssY', H + 2*d)
                FH1 = HssY + (1.5 * d)
                TIFH = H - ((3 * d) + 1.0)
                Blank_X = TIFH + Wss + HssY + Wss + FH1
                PH = HssY - (0.5 * d)
                Ear = HssY + 14.0
                Blank_Y = Ear + PH + Lss + PH + Ear
                return Blank_Y, Blank_X, "E-commerce (Sedex)"
            else:
                # Envelopes Genéricos (Cruz)
                # Base + 2 Paredes + Tampa + Abas
                Blank_X = Lss + (2.5 * Hss)
                Blank_Y = Wss + (3.0 * Hss)
                return Blank_X, Blank_Y, "Corte e Vinco (Envelope)"

        # FAMÍLIA 03xx (Telescópio / Tampa e Fundo)
        elif modelo.startswith('3'):
            # Calcula o blank de UMA peça (Fundo).
            # Se for tampa+fundo, o preço final deve considerar 2x peças ou 2x área.
            # Aqui calculamos a peça base (Fundo)
            Blank_X = Lss + (2 * Hss)
            Blank_Y = Wss + (2 * Hss)
            return Blank_X, Blank_Y, "Tabuleiro (Telescópio)"

        # PADRÃO GENÉRICO (Segurança)
        else:
            return Lss + 2*Hss, Wss + 2*Hss, "Genérico Estimado"

# =========================================================
# 2. APP CONFIG & AUTO-DIAGNOSE
# =========================================================
st.set_page_config(page_title="SmartPack Enterprise", layout="wide")

@st.cache_resource
def load_engine_v10():
    return SmartPackBackend('formulas_smartpack.csv')

engine = load_engine_v10()

if 'carrinho' not in st.session_state: st.session_state.carrinho = []

st.title("🏭 SmartPack Enterprise (V10)")

# --- LEITURA INTELIGENTE DE PREÇOS ---
@st.cache_data
def load_prices_safe():
    arquivos = [f for f in os.listdir() if 'materiais' in f.lower() and 'csv' in f.lower()]
    if arquivos:
        try:
            df = pd.read_csv(arquivos[0], sep=';')
            if len(df.columns) < 2: df = pd.read_csv(arquivos[0], sep=',')
            return df, "Conectado"
        except: pass
    
    # Fallback Padrão
    return pd.DataFrame({
        'Onda': ['B', 'C', 'BC', 'E'],
        'Papel': ['Padrão', 'Padrão', 'Reforçado', 'Micro'],
        'Gramatura': [380, 400, 700, 300],
        'Espessura': [3.0, 4.0, 6.9, 1.5],
        'Coluna': [4.0, 4.5, 8.0, 3.5],
        'Preco_m2': [2.77, 2.85, 5.45, 2.50]
    }), "Modo Demonstração"

df_materiais, status_bd = load_prices_safe()

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("⚙️ Parâmetros")
    st.caption(f"Status BD: {status_bd}")
    
    ondas = df_materiais['Onda'].unique()
    onda_sel = st.selectbox("1. Onda", ondas)
    
    df_onda = df_materiais[df_materiais['Onda'] == onda_sel]
    papel_sel = st.selectbox("2. Papel", df_onda['Papel'].unique())
    
    df_final = df_onda[df_onda['Papel'] == papel_sel]
    coluna_sel = st.selectbox("3. Resistência", df_final['Coluna'].unique())
    
    mat_row = df_final[df_final['Coluna'] == coluna_sel].iloc[0]
    esp_real = float(mat_row['Espessura'])
    preco_base = float(mat_row['Preco_m2'])
    
    st.divider()
    modelos = engine.get_available_models()
    populares = ['201', '427', '200', '711', '215'] # Top 5 de Venda
    lista = [m for m in populares if m in modelos] + [m for m in modelos if m not in populares]
    modelo_visual = st.selectbox("Modelo FEFCO", lista, format_func=lambda x: f"{x.zfill(4)}")

# --- CÁLCULO E RESULTADO ---
col1, col2 = st.columns([1, 2])
with col1:
    st.subheader("Dimensões (Internas)")
    L = st.number_input("Comp. (mm)", value=300)
    W = st.number_input("Larg. (mm)", value=200)
    H = st.number_input("Alt. (mm)", value=100)
    qtd = st.number_input("Qtd.", value=1000, step=100)

bL, bW, perfil = engine.calcular_blank(modelo_visual, L, W, H, esp_real)
area = (bL * bW) / 1_000_000
total = (area * preco_base) * 2.0 * qtd

with col2:
    st.subheader("Resultado")
    st.success(f"Logica Aplicada: **{perfil}**")
    
    c1, c2 = st.columns(2)
    c1.metric("Blank Calculado", f"{bL:.0f} x {bW:.0f} mm")
    c2.metric("Valor Total", f"R$ {total:,.2f}")
    
    st.info(f"Consumo de Papel: {area:.4f} m²/caixa")
    
    if st.button("🛒 Adicionar Pedido"):
        st.session_state.carrinho.append({"Modelo": modelo_visual, "Total": total})
        st.toast("Adicionado!")

if st.session_state.carrinho:
    st.dataframe(pd.DataFrame(st.session_state.carrinho))
