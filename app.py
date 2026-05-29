
import streamlit as st
import pandas as pd

st.set_page_config(page_title="EPR Commercial Engine V1.2.1", layout="wide")

tab1, tab2, tab3 = st.tabs(["Targets & Metal Liability", "Pricing + Gold Fulfilment", "Recycler Fungibility"])

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
gold_fulfilment_pct = st.sidebar.slider("Gold Fulfilment %", 0, 100, 100, 5)
uploaded = st.sidebar.file_uploader("Upload Sales Data", type=["xlsx"])

gold_factor = gold_fulfilment_pct / 100
shortfall = 1 - gold_factor

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

    for c in ["Cu MT","Fe MT","Al MT","Au KG"]:
        out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0)

    with tab1:
        st.subheader("Targets & Metal Liability")
        st.dataframe(out, use_container_width=True)

    with tab2:

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

            orig_cu = float(r["Cu MT"])
            orig_fe = float(r["Fe MT"])
            orig_al = float(r["Al MT"])
            orig_au = float(r["Au KG"])

            if gold_fulfilment_pct < 100 and orig_au > 0:

                adj_cu = orig_cu * (1 + shortfall)
                adj_al = orig_al * (1 + shortfall)
                adj_fe = orig_fe
                adj_au = orig_au * gold_factor

            else:

                adj_cu = orig_cu
                adj_fe = orig_fe
                adj_al = orig_al
                adj_au = orig_au

            metal_min_original=(float(r["Cu MT"])*1000*562)+(float(r["Fe MT"])*1000*30)+(float(r["Al MT"])*1000*136)+(float(r["Au KG"])*1000*772)
            metal_max_original=(float(r["Cu MT"])*1000*1875)+(float(r["Fe MT"])*1000*101)+(float(r["Al MT"])*1000*456)+(float(r["Au KG"])*1000*2575)

            metal_min_adjusted=(adj_cu*1000*562)+(adj_fe*1000*30)+(adj_al*1000*136)+(adj_au*1000*772)
            metal_max_adjusted=(adj_cu*1000*1875)+(adj_fe*1000*101)+(adj_al*1000*456)+(adj_au*1000*2575)

            pricing_rows.append({
                "EEE Category":cat,
                "Gold Fulfilment %":gold_fulfilment_pct,
                "Gold Shortfall %":round(shortfall*100,0),
                "Metal Min ₹/kg Original": round(metal_min_original/target_kg,2) if target_kg else 0,
                "Metal Max ₹/kg Original": round(metal_max_original/target_kg,2) if target_kg else 0,
                "Metal Min ₹/kg Adjusted": round(metal_min_adjusted/target_kg,2) if target_kg else 0,
                "Metal Max ₹/kg Adjusted": round(metal_max_adjusted/target_kg,2) if target_kg else 0,
                "Original Cu MT":round(orig_cu,4),
                "Original Fe MT":round(orig_fe,4),
                "Original Al MT":round(orig_al,4),
                "Original Au KG":round(orig_au,4),
                "Adjusted Cu MT":round(adj_cu,4),
                "Adjusted Fe MT":round(adj_fe,4),
                "Adjusted Al MT":round(adj_al,4),
                "Adjusted Au KG":round(adj_au,4),
                "Metal Min ₹ Original":round(metal_min_original,2),
                "Metal Min ₹ Adjusted":round(metal_min_adjusted,2),
                "Metal Max ₹ Original":round(metal_max_original,2),
                "Category Min ₹/kg": cmin,
                "Category Max ₹/kg": cmax,
                "Category Min Total ₹": round(target_kg*cmin,2),
                "Category Max Total ₹": round(target_kg*cmax,2),
                "Metal Max ₹ Adjusted":round(metal_max_adjusted,2)
            })

        price_df = pd.DataFrame(pricing_rows)

        st.dataframe(price_df, use_container_width=True)

        st.subheader("Totals")

        st.write({
            "Metal Min Total Original": round(price_df["Metal Min ₹ Original"].sum(),2),
            "Metal Min Total Adjusted": round(price_df["Metal Min ₹ Adjusted"].sum(),2),
            "Metal Max Total Original": round(price_df["Metal Max ₹ Original"].sum(),2),
            "Metal Max Total Adjusted": round(price_df["Metal Max ₹ Adjusted"].sum(),2)
        })


    
    with tab3:

        st.subheader("Recycler Fungibility Engine V1.5")

        proposal_df = out[["EEE Category","Target MT"]].copy()
        proposal_df["Proposal Rate ₹/kg"] = 0.0

        proposal_df = st.data_editor(
            proposal_df,
            use_container_width=True,
            key="proposal_rates_v15"
        )

        proposal_df["Brand Revenue ₹"] = (
            proposal_df["Target MT"] * 1000 *
            proposal_df["Proposal Rate ₹/kg"]
        )

        brand_revenue = proposal_df["Brand Revenue ₹"].sum()

        recycler_cost = st.number_input(
            "Recycler Processing Cost (₹/kg)",
            min_value=0.0,
            value=25.0
        )

        extraction = pd.read_excel(
            "EPR_Master_Data.xlsx",
            sheet_name=2,
            header=1
        )
        extraction.columns = extraction.columns.str.strip()

        category_options = sorted(
            extraction["Helper Column"].dropna().astype(str).unique().tolist()
        )

        selected_categories = st.multiselect(
            "Recycler Categories",
            category_options
        )

        if selected_categories:

            split_df = pd.DataFrame({
                "Category": selected_categories,
                "Split %": [0.0]*len(selected_categories)
            })

            split_df = st.data_editor(split_df, use_container_width=True)

            if round(float(split_df["Split %"].sum()),2) == 100:

                total_cu = float(out["Cu MT"].sum())
                total_fe = float(out["Fe MT"].sum())
                total_al = float(out["Al MT"].sum())
                total_au = float(out["Au KG"].sum())

                wcu=wfe=wal=wau=0

                for _,r in split_df.iterrows():
                    wt=float(r["Split %"])/100
                    m=extraction[
                        extraction["Helper Column"].astype(str).str.strip()
                        == str(r["Category"]).strip()
                    ]

                    if len(m):
                        wcu += wt*float(m.iloc[0]["Cu (%)"] or 0)
                        wfe += wt*float(m.iloc[0]["Fe (%)"] or 0)
                        wal += wt*float(m.iloc[0]["Al (%)"] or 0)
                        wau += wt*float(m.iloc[0]["Au (%)"] or 0)

                req_cu = total_cu/wcu if wcu else 0
                req_fe = total_fe/wfe if wfe else 0
                req_al = total_al/wal if wal else 0
                req_au = total_au/(wau*1000) if wau else 0

                vals = {
                    "Cu": req_cu,
                    "Fe": req_fe,
                    "Al": req_al,
                    "Au": req_au
                }

                binding_metal = max(vals, key=vals.get)
                binding_qty = vals[binding_metal]

                generated_cu = binding_qty*wcu
                generated_fe = binding_qty*wfe
                generated_al = binding_qty*wal
                generated_au = binding_qty*wau*1000

                surplus_cu = max(0, generated_cu-total_cu)
                surplus_fe = max(0, generated_fe-total_fe)
                surplus_al = max(0, generated_al-total_al)
                surplus_au = max(0, generated_au-total_au)

                surplus_revenue = (
                    surplus_cu*1000*562 +
                    surplus_fe*1000*30 +
                    surplus_al*1000*136 +
                    surplus_au*772
                )

                recycler_cost_total = binding_qty*1000*recycler_cost

                st.dataframe(proposal_df, use_container_width=True)

                st.write({
                    "Binding Metal": binding_metal,
                    "Binding Quantity MT": round(binding_qty,2),
                    "Weighted Cu %": round(wcu,6),
                    "Weighted Fe %": round(wfe,6),
                    "Weighted Al %": round(wal,6),
                    "Weighted Au %": round(wau,6)
                })

                allocation_df = split_df.copy()

                allocation_df["Required Collection MT"] = (
                    binding_qty *
                    allocation_df["Split %"] / 100
                )

                st.subheader("Recycler Collection Requirement")

                st.dataframe(
                    allocation_df,
                    use_container_width=True
                )

                st.dataframe(pd.DataFrame({
                    "Metal":["Cu","Fe","Al","Au"],
                    "Target":[total_cu,total_fe,total_al,total_au],
                    "Generated":[generated_cu,generated_fe,generated_al,generated_au],
                    "Surplus":[surplus_cu,surplus_fe,surplus_al,surplus_au]
                }))

                st.write({
                    "Brand Revenue ₹": round(brand_revenue,2),
                    "Surplus Revenue ₹": round(surplus_revenue,2),
                    "Recycler Cost ₹": round(recycler_cost_total,2),
                    "Gross Margin ₹": round(
                        brand_revenue + surplus_revenue - recycler_cost_total,2
                    )
                })
            else:
                st.error("Split % must total 100")
