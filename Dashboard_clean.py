#!/usr/bin/env python
# coding: utf-8

# In[8]:


# app.py
import math
import streamlit as st
import matplotlib.pyplot as plt

# ----- JOUW CLASS (ongewijzigd, alleen geplakt) -----
class Bodemenergie:
    def __init__(self, oppervlakte, gasverbruik):
        self.oppervlakte = oppervlakte
        self.gasverbruik = gasverbruik
        self.koken = [0, 0]
        self.water = [0, 0]
        self.ruimteverwarming_gas_m3 = None
        self.bewoners = None

    def Gasverbruik_verwarmen(self, Elektrisch_koken, Bewoners, Zonneboiler):
        if isinstance(Elektrisch_koken, str):
            elek = Elektrisch_koken.strip().lower() in ("ja", "j", "yes", "y", "true", "waar")
        else:
            elek = bool(Elektrisch_koken)
        self.elek = elek

        if elek:
            koken = [0, 0]
        elif Bewoners <= 2:
            koken = [40, 160]
        elif Bewoners <= 4:
            koken = [70, 280]
        else:
            koken = [90, 360]

        if Bewoners == 1:
            water = [147, 658]
        elif Bewoners == 2:
            water = [265, 1258]
        elif Bewoners == 3:
            water = [350, 1964]
        elif Bewoners == 4:
            water = [430, 2469]
        elif Bewoners == 5:
            water = [456, 2768]
        else:
            water = [536, 3322]

        self.koken = koken
        self.water = water
        self.bewoners = Bewoners

        zb = str(Zonneboiler).strip().lower() in ("ja", "j", "yes", "y", "true", "waar")
        tapwater_gas = water[0] * (0.5 if zb else 1.0)
        self.ruimteverwarming_gas_m3 = max(self.gasverbruik - koken[0] - tapwater_gas, 0)
        return koken, water, self.ruimteverwarming_gas_m3

    def get_woningklasse(self):
        if self.ruimteverwarming_gas_m3 is None:
            raise RuntimeError("Roep eerst Gasverbruik_verwarmen(...) aan.")
        verhouding = self.ruimteverwarming_gas_m3 / self.oppervlakte
        if verhouding <= 7.0:
            return ["Goed – Energielabel A (EPC 0,4)", 1200, 800]
        elif verhouding <= 8.0:
            return ["Redelijk – Energielabel B (EPC 0,6)", 1400, 700]
        elif verhouding <= 9.5:
            return ["Voldoende – Energielabel C (EPC 0,8, zonder PV)", 1600, 600]
        else:
            return ["Onvoldoende – hoger dan EPC 0,8", None, None]

    def Vermogen_WP(self):
        if self.ruimteverwarming_gas_m3 is None:
            raise RuntimeError("Roep eerst Gasverbruik_verwarmen(...) aan.")
        GAS_MJ_PER_M3 = 35.17
        MJ_PER_KWH = 3.6
        CF = 0.95
        woningklasse = self.get_woningklasse()
        vollasturen = woningklasse[1] if woningklasse[1] else 1600
        Q_kWh = self.ruimteverwarming_gas_m3 * (GAS_MJ_PER_M3 / MJ_PER_KWH)
        B = (Q_kWh / vollasturen) * CF
        return B
        
    def Prijs_WP(self):
        if self.bewoners is None or self.ruimteverwarming_gas_m3 is None:
            raise RuntimeError("Roep eerst Gasverbruik_verwarmen(...) aan.")
        PcF = 1.15  # prijsfactor (montage, btw etc.)
        vermogen_kw = self.Vermogen_WP()
        if self.bewoners <= 4:
            prijs = (vermogen_kw * 600 + 6500) * PcF
        elif self.bewoners <= 6:
            prijs = (vermogen_kw * 550 + 8000) * PcF
        else:
            prijs = (vermogen_kw * 500 + 9500) * PcF
        self.prijs_wp = prijs
        self.vermogen_kw = vermogen_kw
        return prijs, vermogen_kw

    def SCOP(self, afgifte_temp):
        if afgifte_temp <= 35:
            self.scop = 5.0
        elif afgifte_temp <= 45:
            self.scop = 4.2
        elif afgifte_temp <= 55:
            self.scop = 3.6
        else:
            self.scop = 3.2
        return self.scop

    def Bodemenergie(self, regeneratie, afgifte_temp):
        vermogen_kw = self.Vermogen_WP()
        scop = self.SCOP(afgifte_temp)
        woningklasse = self.get_woningklasse()

        q_ground_kw = vermogen_kw * (1 - 1.0 / scop)
        self.q_ground_kw = q_ground_kw

        # Warmteafgifte per meter bodemlus
        if regeneratie == 0:
            E_bodem = 30
        elif regeneratie == 70:
            E_bodem = 40
        elif regeneratie == 100:
            E_bodem = 50
        else:
            E_bodem = 30 + (regeneratie / 100.0) * (50 - 30)

        Boordiepte = (q_ground_kw * 1000.0) / E_bodem
        self.Boordiepte_PVT = Boordiepte

        # Berekening benodigde PVT-panelen
        F2 = (Boordiepte * 0.4) / 20
        F4_onbelans = (woningklasse[1] - woningklasse[2]) * vermogen_kw * (3.6 / 1000) * 0.7
        F5 = F4_onbelans / 4.3
        Benodigde_panelen = math.ceil(F5 if F5 > F2 else F2)
        self.Benodigde_panelen = Benodigde_panelen

        info = {
            "vermogen_kw": vermogen_kw,
            "scop": scop,
            "q_ground_kw": q_ground_kw,
            "E_bodem": E_bodem,
            "F2": F2,
            "F4": F4_onbelans,
            "F5": F5,
            "Benodigde_panelen": Benodigde_panelen,
        }
        return Boordiepte, info
    def Boring(self, max_diepte=50, exact=False):
        if not hasattr(self, "Boordiepte_PVT"):
            raise RuntimeError("Roep eerst Bodemenergie(...) aan voordat je Boring() gebruikt.")

        aantal_boringen = max(1, math.ceil(self.Boordiepte_PVT / max_diepte))

        if exact:
            diepte_per_boring = round(self.Boordiepte_PVT / aantal_boringen, 1)
        else:
            diepte_per_boring = float(max_diepte)

        totale_geboorde_lengte = round(aantal_boringen * diepte_per_boring, 1)
        overschot = round(totale_geboorde_lengte - self.Boordiepte_PVT, 1)

        self.aantal_boringen = aantal_boringen
        self.effectieve_diepte = diepte_per_boring
        self.totale_geboorde_lengte = totale_geboorde_lengte
        self.overschot = overschot

        print(
            f"De bodemwarmtewisselaar wordt uitgevoerd in {aantal_boringen} boringen "
            f"van {diepte_per_boring} m (totaal {totale_geboorde_lengte} m, overschot {overschot} m)."
        )
        return aantal_boringen, diepte_per_boring, totale_geboorde_lengte, overschot
    

    def Investering(self):
        G1 = 10000  # HSE prijs
        G2_PVT = 1500 + self.Benodigde_panelen
        Invest = G1 + G2_PVT
        self.Invest = Invest
        return Invest

    def Elektra(self):
        vermogen_kw = self.Vermogen_WP()
        woningklasse = self.get_woningklasse()
        Elek_WP = (vermogen_kw - self.q_ground_kw) * woningklasse[1]

        if self.bewoners <= 4:
            Elek_water = self.water[1] / 3.75 + 80 + 110
        else:
            Elek_water = self.water[1] / 3.75 + 132 + 18

        vollasturen_tapwater = Elek_water / vermogen_kw
        vermogen_bronpomp = 0.068
        Elek_bronpomp = vermogen_bronpomp * (
            woningklasse[1] + woningklasse[2] + vollasturen_tapwater
        )
        Totaal_elek = Elek_WP + Elek_water + Elek_bronpomp

        N_aantalPV = (Totaal_elek / 315) - self.Benodigde_panelen
        self.Elek_WP = Elek_WP
        self.Elek_water = Elek_water
        self.Elek_bronpomp = Elek_bronpomp
        self.Totaal_elek = Totaal_elek
        self.N_aantalPV = N_aantalPV
        return Totaal_elek

    def Besparing(self, gasprijs, elekprijs, gas_af):
        O1 = self.prijs_wp + self.Invest
        N = max(0, int(round(self.N_aantalPV)))
        if N <= 5:
            prijs_per_wp = 1.54
            bereik = "4–5 panelen"
        elif N <= 8:
            prijs_per_wp = 1.18
            bereik = "6–8 panelen"
        elif N <= 16:
            prijs_per_wp = 1.00
            bereik = "10–16 panelen"
        else:
            prijs_per_wp = 0.87
            bereik = "≥18 panelen"

        Wp = 400 
        O2 = self.N_aantalPV * Wp * prijs_per_wp * 0.79
        O3_subsidie = 4200 
        O4_gasverbruik = (self.gasverbruik - self.koken[0]) * gasprijs
        O5_elek = self.Totaal_elek * elekprijs
        O6_zon = (self.N_aantalPV + self.Benodigde_panelen) * 315 * elekprijs
        O7 = 259 if gas_af == "ja" else 0

        # Voorkom delen door nul of negatieve besparing
        besparing_per_jaar = (O4_gasverbruik + (O6_zon - O5_elek) + O7)
        if besparing_per_jaar <= 0:
            Terugverdientijd = float("inf")
        else:
            Terugverdientijd = (O1 + O2 - O3_subsidie) / besparing_per_jaar

        CO2_reductie = (self.gasverbruik - self.koken[0]) * 1.884
        self.Terugverdientijd = Terugverdientijd
        self.CO2_reductie = CO2_reductie
        return Terugverdientijd, CO2_reductie
    def Grafieken(self, gasprijs, elekprijs, gas_af, jaren=20):
        """
        Bouw reeksen voor jaarlijkse besparing (€) en cumulatieve cashflow (€),
        en bereken het break-even moment (terugverdientijd).
        Voorwaarde: prijs_wp, Invest, Totaal_elek, N_aantalPV, Benodigde_panelen zijn gezet.
        (Dus roep eerst: Prijs_WP(), Investering(), Elektra())
        """
        # --- Zelfde opbouw als in Besparing(), maar zonder state te wijzigen ---
        O1 = self.prijs_wp + self.Invest

        N = max(0, int(round(self.N_aantalPV)))
        if N <= 5:
            prijs_per_wp = 1.54
        elif N <= 8:
            prijs_per_wp = 1.18
        elif N <= 16:
            prijs_per_wp = 1.00
        else:
            prijs_per_wp = 0.87

        Wp = 400
        O2 = self.N_aantalPV * Wp * prijs_per_wp * 0.79
        O3_subsidie = 4200
        O4_gasverbruik = (self.gasverbruik - self.koken[0]) * gasprijs
        O5_elek = self.Totaal_elek * elekprijs
        O6_zon = (self.N_aantalPV + self.Benodigde_panelen) * 315 * elekprijs
        O7 = 259 if gas_af == "ja" else 0

        # Upfront & yearly
        upfront = O1 + O2 - O3_subsidie
        yearly = (O4_gasverbruik + (O6_zon - O5_elek) + O7)

        # Reeksen
        years = list(range(0, jaren + 1))
        besparing_per_jaar = [0] + [yearly] * jaren
        cumul = [-upfront + yearly * t for t in years]

        # Break-even
        tvt = float("inf") if yearly <= 0 else (upfront / yearly)

        return years, besparing_per_jaar, cumul, tvt, upfront, yearly
        
        


# ----- STREAMLIT UI -----
st.set_page_config(page_title="Bodemenergie Dashboard", layout="wide")
st.title(" Bodemenergie – rekenmodel dashboard")

with st.sidebar:
    st.header("Invoer – woning & gebruik")
    oppervlakte = st.number_input("Oppervlakte (m²)", min_value=20, max_value=1000, value=110)
    gasverbruik = st.number_input("Jaarlijks gasverbruik (m³)", min_value=0, max_value=10000, value=1200)
    bewoners = st.number_input("Aantal bewoners", min_value=1, max_value=12, value=4)
    elektrisch_koken = st.checkbox("Elektrisch koken (ja)", value=True)
    zonneboiler = st.checkbox("Zonneboiler aanwezig (ja)", value=True)

    st.header("Boorconfiguratie")
    max_diepte_boring = st.slider("Max. diepte per boring (m)", min_value=40, max_value=60, value=50, step=10)


    st.header("Invoer – systeem")
    afgifte_temp = st.selectbox("Afgiftetemperatuur (°C)", [30, 35, 40, 45, 50, 55], index=1)
    regeneratie = st.slider("Regeneratiebron (% PVT e.d.)", min_value=0, max_value=100, value=70, step=5)

    st.header("Prijzen & tarief")
    gasprijs = st.number_input("Gasprijs (€/m³)", min_value=0.0, value=1.45, step=0.01)
    elekprijs = st.number_input("Stroomprijs (€/kWh)", min_value=0.0, value=0.40, step=0.01)
    gas_af = st.selectbox("Gasaansluiting opzeggen?", ["ja", "nee"], index=0)

col1, col2 = st.columns([1,1])

# Berekenen
try:
    b = Bodemenergie(oppervlakte, gasverbruik)
    koken, water, rv = b.Gasverbruik_verwarmen(elektrisch_koken, int(bewoners), zonneboiler)
    boordiepte, info = b.Bodemenergie(regeneratie, afgifte_temp)
    aantal_boringen, diepte_per_boring, totale_geboorde_lengte, overschot = b.Boring(max_diepte=max_diepte_boring, exact=False)
    prijs_wp, vermogen_kw = b.Prijs_WP()
    investering = b.Investering()
    totaal_elek = b.Elektra()
    tvt, co2 = b.Besparing(gasprijs, elekprijs, gas_af)
    years, besparing_jr, cumul, tvt_calc, upfront, yearly = b.Grafieken(gasprijs, elekprijs, gas_af, jaren=20)


    with col1:
        st.subheader(" Woningprofiel & belasting")
        woningklasse = b.get_woningklasse()
        st.metric("Woningklasse", woningklasse[0])
        st.write(f"• Gas voor ruimteverwarming: **{rv:.0f} m³/jaar**")
        st.write(f"• Koken (gas): **{koken[0]} m³/jaar**  | Tapwater (gas-eq.): **{water[0]} m³/jaar**")

        st.subheader("Warmtepomp & bron")
        st.metric("Benodigd WP-vermogen", f"{vermogen_kw:.2f} kW")
        st.write(f"SCOP (afgifte {afgifte_temp}°C): **{info['scop']:.1f}**")
        st.metric("Benodigde boordiepte", f"{boordiepte:.1f} m")
        st.write(f"Warmte uit bodem q_ground: **{info['q_ground_kw']:.2f} kW**")
        st.write(f"E_bodem aanname: **{info['E_bodem']:.0f} W/m**")
        
        st.subheader("Boorplan")
        st.metric("Aantal boringen", f"{aantal_boringen}")
        st.write(f"Diepte per boring: **{diepte_per_boring} m** (max {max_diepte_boring} m)")
        st.write(f"Totale geboorde lengte: **{totale_geboorde_lengte} m**")
        if overschot > 0:
            st.caption(f"Behoefte ≈ {b.Boordiepte_PVT:.1f} m → overschot **{overschot} m** door afronding op max-diepte.")
        dieptes = list(range(40, 61))
        boringen = [math.ceil(b.Boordiepte_PVT / d) for d in dieptes]
        fig, ax = plt.subplots()
        ax.plot(dieptes, boringen, marker='o')
        ax.axvline(max_diepte_boring, linestyle='--')  # markeer huidige keuze
        ax.set_xlabel("Max. diepte per boring (m)")
        ax.set_ylabel("Aantal boringen (st.)")
        ax.set_title("Aantal boringen vs. max. diepte per boring")
        ax.grid(True, which="both", linewidth=0.5, alpha=0.5)
        st.pyplot(fig)
        st.caption(
            f"Totale benodigde boordiepte ≈ {b.Boordiepte_PVT:.1f} m. "
            f"Bij max {max_diepte_boring} m per boring → {aantal_boringen} boringen van ca. {diepte_per_boring} m."
        )
        


    with col2:
        st.subheader("Kosten & energie")
        st.write(f"Warmtepompprijs (incl. factor): **€{prijs_wp:,.0f}**")
        st.write(f"Investering HSE + PVT: **€{investering:,.0f}**")
        st.write(f"Elektra WP: **{b.Elek_WP:.0f} kWh/jaar**, Tapwater: **{b.Elek_water:.0f} kWh/jaar**, Bronpomp: **{b.Elek_bronpomp:.0f} kWh/jaar**")
        st.metric("Totaal elektriciteit", f"{totaal_elek:.0f} kWh/jaar")

        st.subheader("PV / PVT")
        st.write(f"Benodigde PVT-panelen voor balans: **{b.Benodigde_panelen} st**")
        st.write(f"Extra PV naast PVT (modeluitkomst): **{b.N_aantalPV:.0f} st**")

        st.subheader("Besparing & duurzaamheid")
        if tvt == float('inf'):
            st.metric("Terugverdientijd", "Niet haalbaar bij huidige aannames")
        else:
            st.metric("Terugverdientijd", f"{tvt:.1f} jaar")
        st.metric("CO₂-reductie", f"{co2/1000:.2f} ton/jaar")
        st.subheader("📈 Financieel verloop")
        fig1, ax1 = plt.subplots()
        ax1.plot(years, cumul)
        ax1.axhline(0, linestyle='--')
        if tvt_calc != float('inf'):
            ax1.axvline(tvt_calc, linestyle='--')
            ax1.set_title(f"Cumulatieve cashflow (break-even ≈ {tvt_calc:.1f} jaar)")
        else:
            ax1.set_title("Cumulatieve cashflow (break-even niet haalbaar)")
        ax1.set_xlabel("Jaar")
        ax1.set_ylabel("Cumulatieve cashflow (€)")
        ax1.grid(True, which="both", linewidth=0.5, alpha=0.5)
        st.pyplot(fig1)
        fig2, ax2 = plt.subplots()
        ax2.plot(years[1:], besparing_jr[1:], marker='o')
        ax2.set_title("Jaarlijkse besparing")
        ax2.set_xlabel("Jaar")
        ax2.set_ylabel("Besparing per jaar (€)")
        ax2.grid(True, which="both", linewidth=0.5, alpha=0.5)
        st.pyplot(fig2)
        st.caption(
            f"Upfront investeringen ≈ €{upfront:,.0f}. "
            f"Jaarlijkse besparing ≈ €{yearly:,.0f}. "
        + (f"Break-even rond jaar {tvt_calc:.1f}." if tvt_calc != float('inf') else "Break-even wordt niet bereikt bij huidige aannames.")
        )

        
        

    with st.expander("Model-details (F2 / F4 / F5)"):
        st.json({k: (round(v,3) if isinstance(v,(int,float)) else v) for k,v in info.items()})

except Exception as e:
    st.error(f"Er ging iets mis: {e}")
    st.stop()


# In[ ]:




