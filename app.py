import streamlit as st
import pandas as pd
import math
import os

# =========================================================
# 1. SMARTPACK V15 - DYNAMIC BUILDER (A LÓGICA HEIDELBERG)
# =========================================================
class SmartPackBackend:
    def __init__(self, csv_path='formulas_smartpack.csv'):
        if os.path.exists(csv_path):
            try:
                # 'on_bad_lines' ignora linhas quebradas para não travar
                self.df = pd.read_csv(csv_path, delimiter=';', dtype={'Modelo': str}, on_bad_lines='skip')
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

        # --- TRADUTOR DE FUNÇÕES (BASEADO NO SEU MANUAL) ---
        fam = modelo[0]
        is_tubular = fam in ['2','5','6','7']
        
        # Fatores K (Calibrados para Onda B/C)
        k = {'C90': 0.5, 'HC90': 1.7*d, 'Glue': 0.5, 'Slot': d+1.0} if is_tubular else {'C90': 1.0*d, 'HC90': 1.0*d, 'Glue': 1.0*d, 'Slot': d+2.0}
        
        contexto = {
            # Variáveis do Usuário
            'L': float(L), 'W': float(W), 'H': float(H), 'd': lambda: float(d),
            
            # Constantes Prinect (Flags)
            'dtID': 1, 'dtOD': 0, 'No': 0, 'Yes': 1, 'Flat': 0, 'Round': 1, 
            'fd': lambda: 0, 'DT': 1, 'UL': 1,
            
            # Matemática
            'sqrt': math.sqrt, 'min': min, 'max': max, 'tan': math.tan, 'atan': math.atan,
            
            # Funções de Engenharia (Mapeadas do Manual)
            'C90x': lambda *a: k['C90'],       
            'C90y': lambda *a: k['C90'],       
            'HC90x': lambda *a: k['HC90'],     
            'GlueCorr': lambda *a: k['Glue'],  
            'LPCorr': lambda *a: 0.0,          
            'GLWidth': lambda *a: 35.0,        
            'SlotWidth': lambda *a: k['Slot'],
            'O90y': lambda *a: d,     # Outer 90 Correction (Geralmente 1 espessura)
            'I90y': lambda *a: d,     # Inner 90 Correction
            'DC0y': lambda *a: 0,     # Distance Correction
            'Wlc': 0.0, 'LSC': 0.0    # Correções finas de camada
        }
        
        resolvidos = {}
        # 5 Passadas para resolver dependências (Ex: PH1 depende de PH que depende de W)
        for _ in range(5):
            for _, row in df_model.iterrows():
                try:
                    param = row['Parametro']
                    formula = str(row['Formula']).strip().replace('=', '')
                    if param in ['L', 'W', 'H']: continue
                    
                    if formula.replace('.','',1).isdigit(): val = float(formula)
                    else: val = eval(formula.replace('^', '**'), {}, contexto)
                    
                    contexto[param] = val
                    resolvidos[param] = val
                except: 
                    if param not in contexto: contexto[param] = 0.0
        return resolvidos

    def calcular_blank_exato(self, modelo, L, W, H, d):
        vars_eng = self._resolve_formulas(modelo, L, W, H, d)
        if not vars_eng: return 0, 0, "Modelo Inexistente"

        # Dimensões Base de Vinco
        Lss = vars_eng.get('Lss', L + d)
        Wss = vars_eng.get('Wss', W + d)
        Hss = vars_eng.get('Hss', H + (1.7*d if modelo[0] in ['2','5','7'] else d))

        # --- LÓGICA DE MONTAGEM DINÂMICA (A SOLUÇÃO REAL) ---
        # Não usamos 'IF 711', usamos 'O QUE TEM NA CAIXA?'

        # 1. Eixo X (Largura Total da Chapa)
        has_GL = 'GL' in vars_eng or 'GLWidth' in str(self.df[self.df['Modelo']==modelo]['Formula'].values)
        
        if has_GL:
            GL = vars_eng.get('GL', 35.0)
            # Desconto de dobra (Setback) para tubulares
            setback = 2.0 * d if modelo.startswith('7') else 0
            Blank_X = GL + 2*(Lss + Wss) - setback
        else:
            # Tabuleiros: Procura por variáveis de largura total
            if 'L_Blank' in vars_eng: Blank_X = vars_eng['L_Blank']
            elif 'FlatWidth' in vars_eng: Blank_X = vars_eng['FlatWidth']
            else:
                # Reconstrói: Base + 2x Paredes + Abas laterais (se houver)
                Wall_H = vars_eng.get('Hss', H)
                Blank_X = Lss + 2*Wall_H

        # 2. Eixo Y (Comprimento Total da Chapa)
        # AQUI ESTÁ A MÁGICA DA 0711
        # O programa soma TUDO o que achar de componente vertical.
        
        Blank_Y = Hss # Começa com a altura do corpo

        # Procura Aba Superior (Top Flap)
        if 'FH' in vars_eng: Blank_Y += vars_eng['FH']
        elif 'Top' in vars_eng: Blank_Y += vars_eng['Top']
        elif modelo.startswith('2'): Blank_Y += Wss/2 # Fallback RSC
        
        # Procura Aba Inferior (Bottom Flap) OU Estrutura Complexa
        found_bottom = False
        
        # Prioridade 1: Variáveis de Fundo Complexo (0711, 09xx)
        # PH1 e PH2 são partes de fundos automáticos ou snap-lock
        if 'PH1' in vars_eng: 
            Blank_Y += vars_eng['PH1']
            found_bottom = True
        if 'PH2' in vars_eng: 
            Blank_Y += vars_eng['PH2']
            found_bottom = True
            
        # Prioridade 2: Aba de Fundo Padrão
        if not found_bottom:
            if 'FH_B' in vars_eng: Blank_Y += vars_eng['FH_B']
            elif 'Bottom' in vars_eng: Blank_Y += vars_eng['Bottom']
            elif 'FH' in vars_eng: Blank_Y += vars_eng['FH'] # Simetria
            elif modelo.startswith('2'): Blank_Y += Wss/2 # Fallback RSC

        # Ajuste Final para E-commerce (0427) que foge à regra tubular
        if modelo == '427':
            HssY = vars_eng.get('HssY', H + 2*d)
            Blank_Y = (HssY + 14.0)*2 + (HssY - 0.5*d)*2 + Lss
            # Recalcula X preciso
            FH1 = HssY + (1.5 * d)
            Blank_X = (H - ((3 * d) + 1.0)) + Wss + HssY + Wss + FH1
            return Blank_Y, Blank_X, "E-commerce (Gold)"

        return Blank_X, Blank_Y, f"Dinâmico ({'Tubular' if has_GL else 'Plano'})"

# =========================================================
# 2. INTERFACE
# =========================================================
st.set_page_config(page_title="SmartPack V15", layout="wide")

@st.cache_resource
def load_engine_v15():
    return SmartPackBackend('formulas_smartpack.csv')

engine = load_engine_v15()
if 'carrinho' not in st.session_state: st.session_state.carrinho = []

@st.cache_data
def load_prices_safe():
    try:
        arquivos = [f for f in os.listdir() if 'materiais' in f.lower() and 'csv' in f.lower()]
        if arquivos:
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

st.title("🏭 SmartPack V15 - Dynamic Builder")

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
    
    st.info(f"Consumo: {area:.4f} m² | Total: R$ {total:,.2f}")
    
    if st.button("🛒 Adicionar"):
        st.session_state.carrinho.append({"Modelo": modelo, "Total": total})
