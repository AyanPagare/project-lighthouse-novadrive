import os
from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Lighthouse | NovaDrive Supply Network Intelligence",
    page_icon="🔭",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_FILE = BASE_DIR / "data" / "NovaDrive_CRO_Dashboard_v6.xlsx"

# -----------------------------
# Theme / helpers
# -----------------------------
st.markdown("""
<style>
.block-container {padding-top: 1.2rem; padding-bottom: 2rem;}
[data-testid="stMetricValue"] {font-size: 1.65rem;}
.small-muted {color:#6b7280;font-size:0.85rem;}
.section-title {font-size:1.25rem;font-weight:700;margin-top:0.6rem;margin-bottom:0.4rem;}
.alert-card {padding:14px 16px;border:1px solid #e5e7eb;border-radius:12px;background:#fafafa;margin-bottom:10px;}
.badge {display:inline-block;padding:3px 8px;border-radius:999px;background:#eef2ff;font-size:0.78rem;font-weight:600;margin-right:5px;}
</style>
""", unsafe_allow_html=True)


def clean_df(df):
    df = df.copy()
    df = df.dropna(axis=0, how="all").dropna(axis=1, how="all")
    if len(df) == 0:
        return df
    # Most workbook sheets have their header in row 0. Some presentation sheets contain title rows.
    df.columns = [str(c).strip() for c in df.columns]
    return df


@st.cache_data(show_spinner=False)
def load_workbook(path):
    xls = pd.ExcelFile(path)
    return {sheet: clean_df(pd.read_excel(path, sheet_name=sheet)) for sheet in xls.sheet_names}


def find_col(df, names):
    lookup = {str(c).strip().lower(): c for c in df.columns}
    for n in names:
        if n.lower() in lookup:
            return lookup[n.lower()]
    return None


def parse_pct(v):
    if pd.isna(v):
        return None
    if isinstance(v, str):
        s = v.strip().replace('%', '')
        try:
            return float(s) / 100 if '%' in str(v) else float(s)
        except Exception:
            return None
    return float(v) if abs(float(v)) <= 1 else float(v) / 100


def fmt_num(v, digits=1):
    if pd.isna(v):
        return "—"
    return f"{float(v):,.{digits}f}"


def tier_order(v):
    return {"Tier-1": 1, "Tier-2": 2, "Tier-3": 3}.get(str(v), 9)


def unique_semicolon(value):
    if pd.isna(value) or not str(value).strip():
        return []
    return [x.strip() for x in str(value).split(';') if x.strip()]


def network_nodes(network):
    nodes = []
    for _, r in network.iterrows():
        for side, col in [("From", "From Entity"), ("To", "To Entity")]:
            if col in network.columns and pd.notna(r[col]):
                nodes.append(r[col])
    return sorted(set(nodes))


# -----------------------------
# Load data
# -----------------------------
if "uploaded_file" not in st.session_state:
    st.session_state.uploaded_file = None

with st.sidebar:
    st.title("🔭 Lighthouse")
    st.caption("NovaDrive Supply Network Intelligence")
    uploaded = st.file_uploader("Optional: upload the NovaDrive workbook", type=["xlsx"])
    if uploaded is not None:
        st.session_state.uploaded_file = uploaded

if st.session_state.uploaded_file is not None:
    source = st.session_state.uploaded_file
    sheets = {s: clean_df(pd.read_excel(source, sheet_name=s)) for s in pd.ExcelFile(source).sheet_names}
else:
    if not DEFAULT_FILE.exists():
        st.error("Workbook not found. Put NovaDrive_CRO_Dashboard_v6.xlsx inside data/ or upload it from the sidebar.")
        st.stop()
    sheets = load_workbook(str(DEFAULT_FILE))

network = sheets.get("Network Master", pd.DataFrame())
risk = sheets.get("Risk Engine", pd.DataFrame())
criticality = sheets.get("Network Criticality", pd.DataFrame())
events = sheets.get("Event Intelligence", pd.DataFrame())
alts = sheets.get("Alternate Suppliers", pd.DataFrame())
product_map = sheets.get("Product-Component Map", pd.DataFrame())
product_exposure = sheets.get("Product Network Exposure", pd.DataFrame())
unresolved = sheets.get("Unresolved", pd.DataFrame())
ownership = sheets.get("Ownership", pd.DataFrame())
excluded = sheets.get("Excluded & Notes", pd.DataFrame())
methodology = sheets.get("Methodology", pd.DataFrame())
qa = sheets.get("Model QA", pd.DataFrame())

# -----------------------------
# Sidebar navigation
# -----------------------------
pages = [
    "CRO Command Center",
    "Supply Network",
    "Product Exposure",
    "Risk Intelligence",
    "Event Radar",
    "Alternate Sourcing",
    "Evidence & Methodology",
]
page = st.sidebar.radio("Navigate", pages)

# Global filters
st.sidebar.divider()
products_available = sorted(set(product_map["Product ID"].dropna().astype(str))) if "Product ID" in product_map else ["P1", "P2", "P3"]
product_filter = st.sidebar.multiselect("Product scope", products_available, default=products_available)
if "Tier" in network.columns:
    tier_filter = st.sidebar.multiselect("Network tiers", ["Tier-1", "Tier-2", "Tier-3"], default=["Tier-1", "Tier-2", "Tier-3"])
else:
    tier_filter = ["Tier-1", "Tier-2", "Tier-3"]

n = network.copy()
if "Tier" in n.columns:
    n = n[n["Tier"].isin(tier_filter)]
if "NovaDrive Product(s)" in n.columns and product_filter:
    n = n[n["NovaDrive Product(s)"].astype(str).apply(lambda x: any(p in x for p in product_filter))]

# -----------------------------
# Header
# -----------------------------
st.title("Project Lighthouse")
st.caption("CRO decision-support layer for NovaDrive's multi-tier supply network")

# -----------------------------
# Page: Command Center
# -----------------------------
if page == "CRO Command Center":
    confirmed = int(len(network[network.get("Relationship Status", pd.Series(dtype=str)).astype(str).str.lower().eq("confirmed")])) if not network.empty else 0
    tiers = {t: int((network["Tier"] == t).sum()) for t in ["Tier-1", "Tier-2", "Tier-3"]} if "Tier" in network else {}
    high_events = int(events[events["Management Status"].astype(str).str.upper().isin(["HIGH PRIORITY", "ESCALATE"])].shape[0]) if not events.empty and "Management Status" in events else 0
    shared = 0
    if "Shared Upstream Dependency?" in criticality.columns:
        shared = int(criticality[criticality["Shared Upstream Dependency?"].astype(str).str.lower().eq("yes")].shape[0])

    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Confirmed links", confirmed)
    c2.metric("Tier-1 relationships", tiers.get("Tier-1",0))
    c3.metric("Tier-2 relationships", tiers.get("Tier-2",0))
    c4.metric("Tier-3 relationships", tiers.get("Tier-3",0))
    c5.metric("Shared upstream nodes", shared)

    st.divider()
    left,right = st.columns([1.55,1])
    with left:
        st.subheader("Management priorities")
        if not risk.empty and "Decision Priority" in risk.columns:
            r = risk.copy()
            r["Decision Priority"] = pd.to_numeric(r["Decision Priority"], errors="coerce")
            r = r.sort_values("Decision Priority", ascending=False).head(10)
            cols = [c for c in ["Legal Name","Tier","Supplier Risk","Network Criticality","Decision Priority","Network Role"] if c in r.columns]
            st.dataframe(r[cols], use_container_width=True, hide_index=True)
        else:
            st.info("Risk Engine sheet is unavailable.")
    with right:
        st.subheader("Event radar")
        if not events.empty:
            ev = events.copy()
            status_order = {"HIGH PRIORITY":0,"WATCH":1,"DUPLICATE":2,"SUPPRESSED":3}
            ev["_o"] = ev["Management Status"].map(status_order).fillna(9)
            ev = ev.sort_values(["_o","Effective"] if "Effective" in ev.columns else ["_o"])
            for _, row in ev.head(5).iterrows():
                st.markdown(f"**{row.get('Event ID','')} · {row.get('Management Status','')}** — {row.get('Event','')}")
                st.caption(str(row.get("Why It Matters","")))
        else:
            st.info("No event data.")

    st.divider()
    st.subheader("Network concentration signals")
    if not criticality.empty:
        show = criticality.copy()
        show["Decision Priority"] = pd.to_numeric(show.get("Decision Priority"), errors="coerce")
        show = show.sort_values("Decision Priority", ascending=False).head(12)
        fig = px.scatter(
            show, x="Network Criticality", y="Supplier Risk", size="Decision Priority",
            hover_name="Node", color="Tier", text=None,
            labels={"Network Criticality":"Network criticality", "Supplier Risk":"Supplier risk"},
        )
        fig.update_layout(height=470, margin=dict(l=10,r=10,t=30,b=10), legend_title_text="Tier")
        st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# Page: Network
# -----------------------------
elif page == "Supply Network":
    st.subheader("Supply Network Explorer")
    st.caption("Only relationships marked Confirmed in Network Master are treated as the operating network. Ownership, exclusions and hypotheses are kept separate.")

    if n.empty:
        st.warning("No network rows match the selected filters.")
    else:
        # Edge table
        st.dataframe(n, use_container_width=True, hide_index=True)

        st.subheader("Interactive network graph")
        gdf = n.copy()
        nodes = {}
        edges = []
        for _, row in gdf.iterrows():
            a,b = str(row["From Entity"]),str(row["To Entity"])
            tier = str(row.get("Tier",""))
            nodes.setdefault(a, {"tier":"Root" if a == "NovaDrive Technologies" else "Unknown"})
            nodes.setdefault(b, {"tier":tier})
            edges.append((a,b,tier,str(row.get("Component / Input",""))))
        # layered coordinates
        layer_y = {"Root":0,"Tier-1":-1,"Tier-2":-2,"Tier-3":-3,"Unknown":-2}
        by_tier = {}
        for name, meta in nodes.items():
            by_tier.setdefault(meta["tier"], []).append(name)
        pos={}
        for tier, names in by_tier.items():
            names=sorted(names)
            for i,name in enumerate(names):
                pos[name]=((i-(len(names)-1)/2)*1.7, layer_y.get(tier,-2))
        edge_x=[]; edge_y=[]
        for a,b,_,_ in edges:
            edge_x += [pos[a][0],pos[b][0],None]
            edge_y += [pos[a][1],pos[b][1],None]
        fig=go.Figure()
        fig.add_trace(go.Scatter(x=edge_x,y=edge_y,mode="lines",line=dict(width=1),hoverinfo="none",showlegend=False))
        color_map={"Root":"NovaDrive","Tier-1":"Tier-1","Tier-2":"Tier-2","Tier-3":"Tier-3","Unknown":"Unknown"}
        for tier,names in by_tier.items():
            xs=[pos[x][0] for x in names]; ys=[pos[x][1] for x in names]
            fig.add_trace(go.Scatter(x=xs,y=ys,mode="markers+text",text=names,textposition="top center",marker=dict(size=15),name=color_map.get(tier,tier),hovertext=names,hoverinfo="text"))
        fig.update_layout(height=650, xaxis=dict(visible=False), yaxis=dict(visible=False), margin=dict(l=10,r=10,t=10,b=10), hovermode="closest")
        st.plotly_chart(fig,use_container_width=True)

        st.subheader("Node drill-down")
        all_nodes=network_nodes(network)
        selected=st.selectbox("Select a supplier / node", [x for x in all_nodes if x != "NovaDrive Technologies"])
        rows=network[(network["From Entity"].astype(str)==selected)|(network["To Entity"].astype(str)==selected)]
        if not rows.empty:
            st.dataframe(rows,use_container_width=True,hide_index=True)
        if not risk.empty and "Legal Name" in risk.columns:
            rr=risk[risk["Legal Name"].astype(str)==selected]
            if not rr.empty:
                st.dataframe(rr.T.rename(columns={rr.index[0]:"Value"}),use_container_width=True)

# -----------------------------
# Page: Product Exposure
# -----------------------------
elif page == "Product Exposure":
    st.subheader("Product Exposure")
    p = st.selectbox("Product", product_filter or products_available)
    pm = product_map[product_map["Product ID"].astype(str)==p] if not product_map.empty else pd.DataFrame()
    pe = product_exposure[product_exposure["Product ID"].astype(str)==p] if not product_exposure.empty else pd.DataFrame()

    if not pm.empty:
        row=pm.iloc[0]
        c1,c2,c3 = st.columns(3)
        c1.metric("Annual revenue", f"${float(row['Annual Revenue (USD m)']):,.0f}m")
        c2.metric("Weekly units", f"{float(row['Weekly Units']):,.0f}")
        c3.metric("Components in scope", int(pm["Component ID"].nunique()))
        st.info(f"Manufacturing footprint: {row.get('Primary Manufacturing Footprint','—')}")
        st.dataframe(pm,use_container_width=True,hide_index=True)

    if not pe.empty:
        st.subheader("Confirmed network exposure")
        st.dataframe(pe,use_container_width=True,hide_index=True)
        if "Tier-1 Allocation" in pe.columns:
            chart=pe.copy()
            chart["Tier-1 Allocation"] = pd.to_numeric(chart["Tier-1 Allocation"],errors="coerce")*100
            fig=px.bar(chart,x="Component ID",y="Tier-1 Allocation",color="Tier-1 Supplier",text="Tier-1 Allocation",labels={"Tier-1 Allocation":"Tier-1 allocation (%)"})
            fig.update_layout(height=400,yaxis_range=[0,100])
            st.plotly_chart(fig,use_container_width=True)
    st.caption("Important: a supplier reaching a product does not mean it carries 100% of the product's revenue. Product revenue is context; disclosed supplier allocation is used where available.")

# -----------------------------
# Page: Risk
# -----------------------------
elif page == "Risk Intelligence":
    st.subheader("Risk Intelligence")
    st.caption("Supplier risk, network criticality and evidence/data confidence are intentionally kept as separate concepts.")
    if risk.empty:
        st.error("Risk Engine sheet unavailable.")
    else:
        r=risk.copy()
        for c in ["Supplier Risk","Network Criticality","Decision Priority","Evidence/Data Confidence"]:
            if c in r.columns: r[c]=pd.to_numeric(r[c],errors="coerce")
        min_priority,max_priority=st.slider("Decision-priority range",0,100,(0,100))
        rr=r[(r["Decision Priority"]>=min_priority)&(r["Decision Priority"]<=max_priority)]
        cols=[c for c in ["Legal Name","Tier","Products Exposed","Components Exposed","Supplier Risk","Network Criticality","Decision Priority","Evidence/Data Confidence","Network Role","Network Membership"] if c in rr.columns]
        st.dataframe(rr.sort_values("Decision Priority",ascending=False)[cols],use_container_width=True,hide_index=True)
        st.subheader("Risk × network criticality")
        fig=px.scatter(rr,x="Network Criticality",y="Supplier Risk",size="Decision Priority",color="Evidence/Data Confidence",hover_name="Legal Name",hover_data=["Tier","Network Role"] if "Network Role" in rr.columns else None)
        fig.update_layout(height=560)
        st.plotly_chart(fig,use_container_width=True)

        selected=st.selectbox("Inspect node",rr["Legal Name"].tolist() if not rr.empty else r["Legal Name"].tolist())
        sr=r[r["Legal Name"]==selected]
        if not sr.empty:
            st.subheader(selected)
            st.dataframe(sr.T.rename(columns={sr.index[0]:"Value"}),use_container_width=True)

# -----------------------------
# Page: Events
# -----------------------------
elif page == "Event Radar":
    st.subheader("Event Radar")
    st.caption("Event controls include temporal validation, entity/facility matching, duplicate suppression and network traversal.")
    if events.empty:
        st.info("No event intelligence available.")
    else:
        statuses=sorted(events["Management Status"].dropna().astype(str).unique())
        selected_status=st.multiselect("Status",statuses,default=statuses)
        ev=events[events["Management Status"].astype(str).isin(selected_status)].copy()
        st.dataframe(ev,use_container_width=True,hide_index=True)
        for _,row in ev.iterrows():
            status=str(row.get("Management Status",""))
            with st.expander(f"{row.get('Event ID','')} · {status} · {row.get('Event','')}"):
                a,b=st.columns(2)
                with a:
                    st.write("**Matched entity / facility:**",row.get("Matched Entity/Facility","—"))
                    st.write("**Affected component / product:**",row.get("Affected Component/Product","—"))
                    st.write("**Network path:**",row.get("Network Path","—"))
                with b:
                    st.write("**Why it matters:**",row.get("Why It Matters","—"))
                    st.write("**Next action:**",row.get("Next Action","—"))

# -----------------------------
# Page: Alternates
# -----------------------------
elif page == "Alternate Sourcing":
    st.subheader("Alternate Sourcing")
    st.caption("Initial public-evidence screening only. Fitment and supplier risk are separate; engineering qualification is mandatory before treating a candidate as a replacement.")
    if alts.empty:
        st.info("No alternate supplier data available.")
    else:
        comps=sorted(alts["Component"].dropna().astype(str).unique())
        comp=st.selectbox("Component / need",comps)
        aa=alts[alts["Component"].astype(str)==comp]
        st.dataframe(aa,use_container_width=True,hide_index=True)
        for _,row in aa.iterrows():
            with st.expander(f"{row.get('Candidate','Candidate')} · {row.get('Initial Fitment View','')}"):
                st.write("**Public capability evidence**",row.get("Public Capability Evidence","—"))
                st.write("**Web evidence reference**",row.get("Web Evidence Ref","—"))
                st.write("**Qualification / next step**",row.get("Qualification / Next Step","—"))
        st.warning("The workbook stores web-evidence references, not a live browsing connector. Re-check current public sources before making a sourcing decision.")

# -----------------------------
# Page: Evidence
# -----------------------------
elif page == "Evidence & Methodology":
    st.subheader("Evidence, Assumptions & Controls")
    tabs=st.tabs(["Methodology","Unresolved","Ownership","Exclusions","QA"])
    with tabs[0]:
        st.dataframe(methodology,use_container_width=True,hide_index=True)
    with tabs[1]:
        st.dataframe(unresolved,use_container_width=True,hide_index=True)
    with tabs[2]:
        st.dataframe(ownership,use_container_width=True,hide_index=True)
        st.caption("Ownership is shown separately from material flow and must not be interpreted as a supply relationship.")
    with tabs[3]:
        st.dataframe(excluded,use_container_width=True,hide_index=True)
    with tabs[4]:
        st.dataframe(qa,use_container_width=True,hide_index=True)

st.divider()
st.caption("Project Lighthouse · NovaDrive case environment · Decision-support prototype. Case data is fictional; public-source alternate screening should be re-verified before live use.")
