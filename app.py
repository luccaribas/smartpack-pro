import streamlit as st
import pandas as pd
import math
import os

# =========================================================
# 1. SMARTPACK PRECISION ENGINE (V13 - COMPONENT SCAN)
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

    def _resolve_formulas(self, modelo, L, W, H, d):
        modelo = str(modelo).lstrip('0')
        if self.df.empty: return None
        df_model = self.df[self.df['Modelo'] == modelo]
        if df_model.empty: return None

        # Calibração Baseada em Perfil (Prinect Profile)
        # Tubulares usam fator de 1.7d na altura (compensação de vinco grosso)
        fam = modelo[0]
        is_tubular = fam in ['2','5','6','7']
        k = {'C90': 0.5, 'HC90': 1.7*d, 'Glue': 0.5, 'Slot': d+1.0} if is_tubular else {'C90': 1.0*d, 'HC90': 1.0*d, 'Glue': 1.0*d, 'Slot': d+2.0}
        
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
        # Resolve todas as variáveis possíveis
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

    def calcular_blank_exato(self, modelo, L, W, H, d):
        vars_eng = self._resolve_formulas(modelo, L, W, H, d)
        if not vars_eng: return 0, 0, "Modelo Inexistente"

        # Dimensões Base
        Lss = vars_eng.get('Lss', L + d)
        Wss = vars_eng.get('Wss', W + d)
        Hss = vars_eng.get('Hss', H + (1.7*d if modelo[0] in ['2','5','7'] else d))

        # --- LÓGICA DE SOMA DE COMPONENTES (IMPLANTANDO A LÓGICA PRINECT) ---
        
        # 1. BLANK X (LARGURA DA CHAPA)
        # Se tiver aba de cola (GL), é soma linear.
        has_GL = 'GL' in vars_eng or 'GLWidth' in str(self.df[self.df['Modelo']==modelo]['Formula'].values)
        if has_GL:
            GL = vars_eng.get('GL', 35.0)
            # Fatores de correção de dobra (Crease Setback)
            # Prinect desconta material em cada dobra de 180 graus
            setback = 0
            if modelo.startswith('7'): setback = 2.0 * d # Correção específica para Fundo Auto
            
            Blank_X = GL + 2*(Lss + Wss) - setback
        else:
            # Tabuleiros: Procura variáveis de aba lateral
            # Se tiver PH (Panel Height), soma.
            Wall_H = vars_eng.get('Hss', H)
            # Tenta pegar L_Blank direto se existir
            Blank_X = vars_eng.get('L_Blank', Lss + 2*Wall_H)

        # 2. BLANK Y (COMPRIMENTO DA CHAPA)
        # Aqui está o segredo da 711. Precisamos somar as partes verticais.
        
        # Procura componentes específicos de Fundo Automático
        # G = Glue Area (Fundo), F = Floor (Fundo), O = Overlap
        top_flap = vars_eng.get('FH', Wss/2) # Aba Topo Padrão
        
        if modelo.startswith('7'): # Crash Lock
             # Tenta construir o fundo somando componentes
             # Geralmente fundo auto é complexo. Se não acharmos as vars, usamos a regra geométrica.
             # Regra Geométrica Fundo Auto: Metade da largura + ~30mm de transpasse de cola
             crash_bottom = (Wss / 2) + 30 + (d * 2) 
             
             # Se o CSV tiver a variável específica 'Ext' ou 'O', usamos ela
             if 'Ext' in vars_eng: crash_bottom = (Wss / 2) + vars_eng['Ext']
             elif 'G' in vars_eng: crash_bottom = vars_eng['G'] + vars_eng.get('F', Wss/2)

             Blank_Y = top_flap + Hss + crash_bottom
             
        elif modelo.startswith('2'): # Maletas
             bottom_flap = vars_eng.get('FH_B', top_flap)
             
             # Correção Snap Lock (0215)
             if modelo == '215':
                 bottom_flap = (Wss / 2) + (Wss / 3) # Travamento consome mais
                 
             Blank_Y = top_flap + Hss + bottom_flap
             
        elif modelo == '427': # E-commerce
            # Fórmula Gold Validada
            HssY = vars_eng.get('HssY', H + 2*d)
            Blank_Y = (HssY + 14.0)*2 + (HssY - 0.5*d)*2 + Lss
            # Recalcula X para garantir
            FH1 = HssY + (1.5 * d)
            Blank_X = (H - ((3 * d) + 1.0)) + Wss + HssY + Wss + FH1
            return Blank_Y, Blank_X, "E-commerce (Gold)"
            
        else:
            # Genérico
            Blank_Y = Wss + 2*vars_eng.get('Hss', H)

        return Blank_X, Blank_Y, f"Cálculo Estrutural ({'Tubular' if has_GL else 'Plano'})"

# =========================================================
# 2. INTERFACE
# =========================================================
st.set_page_config(page_title="SmartPack Precision", layout="wide")

@st.cache_resource
def load_engine_v13():
    return SmartPackBackend('formulas_smartpack.csv')

engine = load_engine_v13()
if 'carrinho' not in st.session_state: st.session_state.carrinho = []

@st.cache_data
def load_prices_safe():
    arquivos = [f for f in os.listdir() if 'materiais' in f.lower() and 'csv' in f.lower()]
    if arquivos:
        try:
            df = pd.read_csv(arquivos[0], sep=';')
            if len(df.columns) < 2: df = pd.read_csv(arquivos[0], sep=',')
            return df
        except: pass
    return pd.DataFrame({
        'Onda': ['B', 'C', 'BC'], 'Papel': ['Padrão', 'Reforçado', 'Duplo'],
        'Gramatura': [380, 440, 700], 'Espessura': [3.0, 4.0, 6.9],
        'Coluna': [4.0, 5.5, 8.0], 'Preco_m2': [2.77, 3.88, 5.45]
    })

df_materiais = load_prices_safe()

st.title("🏭 SmartPack Precision (V13)")

with st.sidebar:
    st.header("1. Material")
    onda = st.selectbox("Onda", df_materiais['Onda'].unique())
    df_o = df_materiais[df_materiais['Onda'] == onda]
    papel = st.selectbox("Papel", df_o['Papel'].unique())
    df_p = df_o[df_o['Papel'] == papel]
    coluna = st.selectbox("Resistência", df_p['Coluna'].unique())
    
    mat = df_p[df_p['Coluna'] == coluna].iloc[0]
    d_real = float(mat['Espessura'])
    preco = float(mat['Preco_m2'])
    
    st.divider()
    st.header("2. Modelo")
    modelos = engine.get_available_models()
    tops = ['201', '427', '200', '711', '215']
    lista = [m for m in tops if m in modelos] + [m for m in modelos if m not in tops]
    modelo = st.selectbox("Código FEFCO", lista, format_func=lambda x: f"{x.zfill(4)}")
    
    # Dica visual para o usuário
    if modelo == '711':
        st.caption("ℹ️ Nota: A 0711 possui fundo automático. O blank considera o transpasse de cola e dobras.")

col1, col2 = st.columns([1, 2])
with col1:
    st.subheader("Medidas (mm)")
    L = st.number_input("Comprimento", value=300)
    W = st.number_input("Largura", value=200)
    H = st.number_input("Altura", value=100)
    qtd = st.number_input("Quantidade", value=500, step=100)

bL, bW, perfil = engine.calcular_blank_exato(modelo, L, W, H, d_real)
area = (bL * bW) / 1_000_000
total = (area * preco) * 2.0 * qtd

with col2:
    st.subheader("Resultado")
    st.success(f"Motor: **{perfil}**")
    
    c1, c2 = st.columns(2)
    c1.metric("Largura Chapa", f"{bL:.1f} mm")
    c2.metric("Compr. Chapa", f"{bW:.1f} mm")
    
    st.info(f"Consumo: {area:.4f} m² | Pedido: R$ {total:,.2f}")
    
    if st.button("🛒 Adicionar"):
        st.session_state.carrinho.append({"Modelo": modelo, "Total": total})
