import streamlit as st
import pandas as pd
import os

class ConsultoresApp:
    def __init__(self):
        self.TASAS_CAMBIO = [
            {"moneda": "ARS", "tasa_usd": 0.00110},
            {"moneda": "BRL", "tasa_usd": 0.20000},
            {"moneda": "USD", "tasa_usd": 1.00000},
            {"moneda": "COP", "tasa_usd": 0.00025},
            {"moneda": "MXN", "tasa_usd": 0.05882},
        ]
        self.PRECIOS_VENTA = {
            "adn_1dia_1c": 4500,    # ADN 1 día, 1 consultor
            "adn_2dias_1c": 7620,    # ADN 2 días, 1 consultor
            "adn_2dias_2c": 11900,   # ADN 2 días, 2 consultores
            "pm_fee": 600,          # Fee del PM
            "pm_costo": 280         # Costo del PM por día
        }
        self.df_consultores = self.cargar_datos_iniciales()

    def calcular_usd(self, valor_local, moneda):
        if moneda == 'USD':
            return float(valor_local)
        if float(valor_local) == 0:
            return 0
        tasa = next((t['tasa_usd'] for t in self.TASAS_CAMBIO if t['moneda'] == moneda), 1.0)
        return round(float(valor_local) * float(tasa), 2)

    def cargar_datos_iniciales(self):
        try:
            df = pd.read_csv('consultores_base.csv', encoding='utf-8')
            df['costo_dia_solo_usd'] = df.apply(
                lambda row: self.calcular_usd(row['Costo_Dia_Solo_local'], row['Moneda_acuerdo']), 
                axis=1
            )
            df['costo_dia_pareja_usd'] = df.apply(
                lambda row: self.calcular_usd(row['Costo_Dia_Pareja_local'], row['Moneda_acuerdo']), 
                axis=1
            )
            return df
        except Exception as e:
            st.error(f"Error al leer el CSV: {e}")
            return pd.DataFrame()

    def mostrar_nombre_consultor(self, consultor, pais_actual):
        """Función auxiliar para mostrar el nombre del consultor con íconos si corresponde"""
        nombre = consultor['Nombre']
        if consultor['Pais_local'] != pais_actual:
            return f"{nombre} ✈️ 🏨"
        return nombre

    def seccion_consultores(self):
        st.header("Gestión de Consultores")
        
        # Inicializar el DataFrame en la sesión si no existe
        if 'df_consultores' not in st.session_state:
            st.session_state.df_consultores = self.df_consultores.copy()
        
        # Opciones para los desplegables
        paises = ["Argentina", "Brasil", "Chile", "Uruguay", "Colombia", "México"]
        monedas = ["ARS", "BRL", "USD", "COP", "MXN"]
        
        # Tasas de Cambio
        with st.expander("Tasas de Cambio", expanded=False):
            df_tasas = pd.DataFrame(self.TASAS_CAMBIO)
            st.data_editor(
                df_tasas,
                column_config={
                    "moneda": st.column_config.SelectboxColumn("Moneda", options=monedas, required=True),
                    "tasa_usd": st.column_config.NumberColumn(
                        "1 Unidad local = X USD",
                        format="%.5f",
                        help="Cuántos USD vale 1 unidad de la moneda local"
                    )
                },
                disabled=True,
                hide_index=True,
                use_container_width=True
            )

        # Switch para alternar entre vista día/hora
        modo_hora = st.toggle('Mostrar costos por hora', value=False)
        
        if not st.session_state.df_consultores.empty:
            df_display = st.session_state.df_consultores.copy()
            
            if modo_hora:
                for col in ['Costo_Dia_Solo_local', 'Costo_Dia_Pareja_local', 'costo_dia_solo_usd', 'costo_dia_pareja_usd']:
                    df_display[col] = df_display[col] / 8

            column_config = {
                "ID_Consultor": st.column_config.NumberColumn("ID", disabled=True),
                "Nombre": st.column_config.TextColumn("Nombre"),
                "Pais_local": st.column_config.SelectboxColumn("País", options=paises),
                "Delivery": st.column_config.ListColumn("Países Habilitados"),
                "Moneda_acuerdo": st.column_config.SelectboxColumn("Moneda", options=monedas),
                "Costo_Dia_Solo_local": st.column_config.NumberColumn(
                    "Costo Solo (Local)" if modo_hora else "Costo Día Solo (Local)",
                    min_value=0
                ),
                "Costo_Dia_Pareja_local": st.column_config.NumberColumn(
                    "Costo Pareja (Local)" if modo_hora else "Costo Día Pareja (Local)",
                    min_value=0
                ),
                "costo_dia_solo_usd": st.column_config.NumberColumn(
                    "Costo Solo (USD)" if modo_hora else "Costo Día Solo (USD)",
                    disabled=True
                ),
                "costo_dia_pareja_usd": st.column_config.NumberColumn(
                    "Costo Pareja (USD)" if modo_hora else "Costo Día Pareja (USD)",
                    disabled=True
                )
            }

            edited_df = st.data_editor(
                df_display,
                column_config=column_config,
                hide_index=True,
                use_container_width=True,
                key="consultor_editor"
            )
            
            # Botón para actualizar valores
            if st.button("Actualizar valores USD"):
                # Si estamos en modo hora, multiplicar por 8 antes de actualizar
                df_to_update = edited_df.copy()
                if modo_hora:
                    df_to_update['Costo_Dia_Solo_local'] *= 8
                    df_to_update['Costo_Dia_Pareja_local'] *= 8
                
                # Recalcular valores USD
                df_to_update['costo_dia_solo_usd'] = df_to_update.apply(
                    lambda row: self.calcular_usd(row['Costo_Dia_Solo_local'], row['Moneda_acuerdo']), 
                    axis=1
                )
                df_to_update['costo_dia_pareja_usd'] = df_to_update.apply(
                    lambda row: self.calcular_usd(row['Costo_Dia_Pareja_local'], row['Moneda_acuerdo']), 
                    axis=1
                )
                
                # Actualizar el DataFrame en la sesión
                st.session_state.df_consultores = df_to_update.copy()
                self.df_consultores = df_to_update.copy()
                st.success("Valores USD actualizados correctamente")
                st.rerun()

    def seccion_rentabilidad(self):
        st.header("Análisis de Rentabilidad")
        
        # Filtros en la parte superior
        col1, col2 = st.columns(2)
        with col1:
            pais_seleccionado = st.selectbox(
                "Seleccione un país",
                ["Brasil", "Argentina", "Colombia", "México", "Chile", "Uruguay"]
            )
        
        with col2:
            tipo_workshop = st.selectbox(
                "Seleccione tipo de workshop",
                [
                    "ADN 1 Día - 1 Consultor",
                    "ADN 2 Días - 1 Consultor",
                    "ADN 2 Días - 2 Consultores"
                ]
            )
        
        # Usar el DataFrame de la sesión si existe
        df_consultores_actual = st.session_state.df_consultores if 'df_consultores' in st.session_state else self.df_consultores
        
        # Filtrar consultores habilitados para el país seleccionado
        consultores_pais = df_consultores_actual[
            df_consultores_actual['Delivery'].apply(lambda x: pais_seleccionado in x)
        ]
        
        if not consultores_pais.empty:
            st.markdown(f"## Combinaciones para {pais_seleccionado}")
            
            if tipo_workshop == "ADN 2 Días - 2 Consultores":
                # Generar todas las combinaciones posibles de 2 consultores
                n_consultores = len(consultores_pais)
                for i in range(n_consultores):
                    for j in range(i+1, n_consultores):
                        consultor1 = consultores_pais.iloc[i]
                        consultor2 = consultores_pais.iloc[j]
                        
                        with st.container():
                            nombre1 = self.mostrar_nombre_consultor(consultor1, pais_seleccionado)
                            nombre2 = self.mostrar_nombre_consultor(consultor2, pais_seleccionado)
                            st.markdown(f"{nombre1} + {nombre2}", unsafe_allow_html=True)
                            col1, col2, col3 = st.columns(3)
                            
                            # Calcular costos
                            costo_consultor1 = consultor1['costo_dia_pareja_usd'] * 2  # 2 días
                            costo_consultor2 = consultor2['costo_dia_pareja_usd'] * 2  # 2 días
                            costo_pm = self.PRECIOS_VENTA['pm_costo']  # 1 día de PM
                            costo_total = costo_consultor1 + costo_consultor2 + costo_pm
                            
                            # Ingresos
                            ingreso_consultores = self.PRECIOS_VENTA['adn_2dias_2c']
                            ingreso_pm = self.PRECIOS_VENTA['pm_fee']
                            ingreso_total = ingreso_consultores + ingreso_pm
                            
                            with col1:
                                st.markdown("##### Ingresos")
                                st.write(f"Consultores: ${ingreso_consultores:,.2f}")
                                st.write(f"PM: ${ingreso_pm:,.2f}")
                                st.markdown(f"**Total: ${ingreso_total:,.2f}**")
                            
                            with col2:
                                st.markdown("##### Costos")
                                st.write(f"{consultor1['Nombre']}: ${costo_consultor1:,.2f}")
                                st.write(f"{consultor2['Nombre']}: ${costo_consultor2:,.2f}")
                                st.write(f"PM: ${costo_pm:,.2f}")
                                st.markdown(f"**Total: ${costo_total:,.2f}**")
                            
                            with col3:
                                st.markdown("##### Rentabilidad")
                                margen = ingreso_total - costo_total
                                margen_porcentaje = (margen / ingreso_total) * 100
                                st.write(f"Margen: ${margen:,.2f}")
                                st.write(f"Margen %: {margen_porcentaje:.1f}%")
                                
                                if margen_porcentaje >= 30:
                                    st.markdown("🟢 Margen óptimo")
                                elif margen_porcentaje >= 20:
                                    st.markdown("🟡 Margen aceptable")
                                else:
                                    st.markdown("🔴 Margen bajo")
                            
                            st.markdown("---")
            
            elif tipo_workshop == "ADN 2 Días - 1 Consultor":
                for _, consultor in consultores_pais.iterrows():
                    with st.container():
                        nombre = self.mostrar_nombre_consultor(consultor, pais_seleccionado)
                        st.markdown(nombre, unsafe_allow_html=True)
                        col1, col2, col3 = st.columns(3)
                        
                        # Calcular costos
                        costo_consultor = consultor['costo_dia_solo_usd'] * 2  # 2 días
                        costo_pm = self.PRECIOS_VENTA['pm_costo']  # 1 día de PM
                        costo_total = costo_consultor + costo_pm
                        
                        # Ingresos
                        ingreso_consultores = self.PRECIOS_VENTA['adn_2dias_1c']
                        ingreso_pm = self.PRECIOS_VENTA['pm_fee']
                        ingreso_total = ingreso_consultores + ingreso_pm
                        
                        with col1:
                            st.markdown("##### Ingresos")
                            st.write(f"Consultor: ${ingreso_consultores:,.2f}")
                            st.write(f"PM: ${ingreso_pm:,.2f}")
                            st.markdown(f"**Total: ${ingreso_total:,.2f}**")
                        
                        with col2:
                            st.markdown("##### Costos")
                            st.write(f"Consultor: ${costo_consultor:,.2f}")
                            st.write(f"PM: ${costo_pm:,.2f}")
                            st.markdown(f"**Total: ${costo_total:,.2f}**")
                        
                        with col3:
                            st.markdown("##### Rentabilidad")
                            margen = ingreso_total - costo_total
                            margen_porcentaje = (margen / ingreso_total) * 100
                            st.write(f"Margen: ${margen:,.2f}")
                            st.write(f"Margen %: {margen_porcentaje:.1f}%")
                            
                            if margen_porcentaje >= 30:
                                st.markdown("🟢 Margen óptimo")
                            elif margen_porcentaje >= 20:
                                st.markdown("🟡 Margen aceptable")
                            else:
                                st.markdown("🔴 Margen bajo")
                        
                        st.markdown("---")
            
            else:  # ADN 1 Día - 1 Consultor
                for _, consultor in consultores_pais.iterrows():
                    with st.container():
                        nombre = self.mostrar_nombre_consultor(consultor, pais_seleccionado)
                        st.markdown(f"#### {nombre}")
                        col1, col2, col3 = st.columns(3)
                        
                        # Calcular costos
                        costo_consultor = consultor['costo_dia_solo_usd']  # 1 día
                        costo_total = costo_consultor  # No hay PM
                        
                        # Ingresos
                        ingreso_total = self.PRECIOS_VENTA['adn_1dia_1c']  # No hay PM
                        
                        with col1:
                            st.markdown("##### Ingresos")
                            st.write(f"Consultor: ${ingreso_total:,.2f}")
                            st.write("PM: $ 0.00")
                            st.markdown(f"**Total: ${ingreso_total:,.2f}**")
                        
                        with col2:
                            st.markdown("##### Costos")
                            st.write(f"Consultor: ${costo_consultor:,.2f}")
                            st.write("PM: $ 0.00")
                            st.markdown(f"**Total: ${costo_total:,.2f}**")
                        
                        with col3:
                            st.markdown("##### Rentabilidad")
                            margen = ingreso_total - costo_total
                            margen_porcentaje = (margen / ingreso_total) * 100
                            st.write(f"Margen: ${margen:,.2f}")
                            st.write(f"Margen %: {margen_porcentaje:.1f}%")
                            
                            if margen_porcentaje >= 60:
                                st.markdown("🟢 Margen óptimo")
                            elif margen_porcentaje >= 40:
                                st.markdown("🟡 Margen aceptable")
                            else:
                                st.markdown("🔴 Margen bajo")
                        
                        st.markdown("---")

def main():
    st.set_page_config(layout="wide")
    
    st.title("📊 ADN Mercado Libre 2025")

    # Crear tabs para navegación
    tab1, tab2 = st.tabs(["📊 Gestión de Consultores", "💰 Análisis de Rentabilidad"])

    app = ConsultoresApp()

    with tab1:
        app.seccion_consultores()

    with tab2:
        app.seccion_rentabilidad()

    # Sección "Acerca de" al final
    st.markdown("---")
    st.markdown("### ℹ️ Acerca de")
    st.markdown("Herramienta para gestión de consultores y análisis de rentabilidad de workshops")

# Llamar a main() correctamente
if __name__ == "__main__":
    main()