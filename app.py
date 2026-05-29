
import streamlit as st
import pandas as pd

st.set_page_config(page_title="EPR Commercial Engine V1.1", layout="wide")

tab1, tab2 = st.tabs(["Targets & Metal Liability", "Pricing"])

SCHEDULE_III = {
    "2023-24": 0.60, "2024-25": 0.60,
    "2025-26": 0.70, "2026-27": 0.70,
    "2027-28": 0.80, "2028-29": 0.80
}

SCHEDULE_IV = {
    "2023-24": ("2021-22", 0.15),
    "2024-25": ("2022-23", 0.20),
    "2025-26": ("2023-24", 0.20),
    "2026-27": ("2024-25", 0.20),
    "2027-28": ("2025-26", 0.20),
    "2028-29": ("2026-27", 0.20)
}

gold_obligation = {
    "2023-24":0.20,"2024-25":0.30,"2025-26":0.45,
    "2026-27":0.60,"2027-28":0.80,"2028-29":1.00
}

fy = st.sidebar.selectbox("Compliance Year", list(SCHEDULE_III.keys()))
uploaded = st.sidebar.file_uploader("Upload Sales Data", type=["xlsx"])

def build_output():
    sales = pd.read_excel(uploaded)
    extraction = pd.read_excel("EPR_Master_Data.xlsx", sheet_name=2, header=1)
    extraction.columns = extraction.columns.str.strip()

    rows = []
    for _, row in sales.iterrows():
        category = str(row.get("EEE Category","")).strip()

        try:
            lifespan = int(row.get("Lifespan",0))
        except:
            lifespan = 0

        sales_years=[]
        for c in sales.columns:
            if "-" in str(c):
                try:
                    if float(row[c]) > 0:
                        sales_years.append(c)
                except:
                    pass

        if not sales_years:
            continue

        first_year = sales_years[0]
        years_active = int(fy[:4]) - int(first_year[:4])

        if years_active >= lifespan:
            pct = SCHEDULE_III[fy]
            ref_start = int(fy[:4]) - lifespan
            ref_year = f"{ref_start}-{str(ref_start+1)[-2:]}"
        else:
            ref_year, pct = SCHEDULE_IV[fy]

        sales_value = float(row.get(ref_year,0) or 0)
        target_mt = sales_value * pct

        match = extraction[
            extraction["Helper Column"].astype(str).str.strip() == category
        ]

        au=cu=fe=al=0.0
        if len(match):
            try: au=float(match.iloc[0]["Au (%)"] or 0)
            except: pass
            try: cu=float(match.iloc[0]["Cu (%)"] or 0)
            except: pass
            try: fe=float(match.iloc[0]["Fe (%)"] or 0)
            except: pass
            try: al=float(match.iloc[0]["Al (%)"] or 0)
            except: pass

        rows.append({
            "EEE Category":category,
            "Target MT":target_mt,
            "Cu MT":target_mt*cu,
            "Fe MT":target_mt*fe,
            "Al MT":target_mt*al,
            "Au KG":target_mt*au*1000*gold_obligation[fy]
        })

    return pd.DataFrame(rows)

if uploaded:
    out = build_output()

    # FIX 1
    for c in ["Cu MT","Fe MT","Al MT","Au KG"]:
        out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0)

    with tab1:
        st.subheader("Targets & Metal Liability")
        st.dataframe(out, use_container_width=True)

    with tab2:
        st.subheader("Pricing")

        category_rates = {
            "ITEW": (34,112),
            "CEEW": (22,74),
            "LSEEW": (23,76),
            "TLSEW": (23,76),
            "EETW": (25,82),
            "MDW": (41,135),
            "LIW": (41,136)
        }

        METAL_MIN = {"Au":772,"Cu":562,"Fe":30,"Al":136}
        METAL_MAX = {"Au":2575,"Cu":1875,"Fe":101,"Al":456}

        pricing_rows=[]

        for _,r in out.iterrows():
            cat=r["EEE Category"]

            prefix=''
            for p in category_rates:
                if cat.startswith(p):
                    prefix=p
                    break

            cmin,cmax = category_rates.get(prefix,(0,0))

            target_kg=float(r["Target MT"])*1000

            cat_min_val=target_kg*cmin
            cat_max_val=target_kg*cmax

            metal_min_val=(float(r["Cu MT"])*1000*METAL_MIN["Cu"]) + \
                          (float(r["Fe MT"])*1000*METAL_MIN["Fe"]) + \
                          (float(r["Al MT"])*1000*METAL_MIN["Al"]) + \
                          (float(r["Au KG"])*1000*METAL_MIN["Au"])

            metal_max_val=(float(r["Cu MT"])*1000*METAL_MAX["Cu"]) + \
                          (float(r["Fe MT"])*1000*METAL_MAX["Fe"]) + \
                          (float(r["Al MT"])*1000*METAL_MAX["Al"]) + \
                          (float(r["Au KG"])*1000*METAL_MAX["Au"])

            metal_min_rate = round(metal_min_val/target_kg,2) if target_kg else 0
            metal_max_rate = round(metal_max_val/target_kg,2) if target_kg else 0

            pricing_rows.append({
                "EEE Category":cat,
                "Cat Min ₹/kg":cmin,
                "Cat Max ₹/kg":cmax,
                "Metal Min ₹/kg":metal_min_rate,
                "Metal Max ₹/kg":metal_max_rate,
                "Preferred Min Basis":"Category" if cmin < metal_min_rate else "Metal",
                "Preferred Max Basis":"Category" if cmax < metal_max_rate else "Metal",
                "Category Min ₹":round(cat_min_val,2),
                "Category Max ₹":round(cat_max_val,2),
                "Metal Min ₹":round(metal_min_val,2),
                "Metal Max ₹":round(metal_max_val,2)
            })

        price_df = pd.DataFrame(pricing_rows)

        st.dataframe(price_df, use_container_width=True)

        st.subheader("Totals")
        st.write({
            "Category Min Total": round(price_df["Category Min ₹"].sum(),2),
            "Category Max Total": round(price_df["Category Max ₹"].sum(),2),
            "Metal Min Total": round(price_df["Metal Min ₹"].sum(),2),
            "Metal Max Total": round(price_df["Metal Max ₹"].sum(),2)
        })
