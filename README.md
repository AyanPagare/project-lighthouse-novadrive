# Project Lighthouse — NovaDrive Streamlit App

A local Streamlit CRO decision-support prototype built on the NovaDrive case workbook.

## 1. Folder structure

```text
Project_Lighthouse_Streamlit/
├── app.py
├── requirements.txt
├── README.md
└── data/
    └── NovaDrive_CRO_Dashboard_v6.xlsx
```

## 2. Run in VS Code

Open this folder in VS Code, then open the terminal.

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### Command Prompt

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Streamlit will print a local address, normally `http://localhost:8501`.

## 3. What the app contains

- **CRO Command Center** — network KPIs, management-priority nodes and event radar.
- **Supply Network** — confirmed relationship table, interactive network view and node drill-down.
- **Product Exposure** — P1/P2/P3 component and Tier-1 exposure.
- **Risk Intelligence** — supplier risk, network criticality, decision priority and evidence confidence.
- **Event Radar** — event status, matched facility/entity, network path and next action.
- **Alternate Sourcing** — component-specific public-evidence screening and qualification notes.
- **Evidence & Methodology** — methodology, unresolved hypotheses, ownership, exclusions and QA controls.

## 4. Data model rule

The application reads the workbook as the source of truth. Confirmed material relationships come from `Network Master`. Ownership and unresolved hypotheses are kept separate. The application does not treat a candidate supplier from `Supplier Universe` or an alternate-sourcing candidate as an incumbent supplier.

## 5. Replacing the workbook

You can replace:

```text
data/NovaDrive_CRO_Dashboard_v6.xlsx
```

with another workbook that preserves the sheet names and column structure.

You can also upload an `.xlsx` file from the sidebar while the app is running.

## 6. Important case-model limitation

`Product revenue` is business context, not supplier spend. The app therefore displays supplier allocation and network relationships directly rather than claiming that a supplier owns 100% of a product's revenue merely because it touches a component used in that product.

The alternate supplier page uses the evidence already stored in the workbook. It does not pretend that an old search reference is a live verification. Re-check current public sources before using a candidate in a real sourcing decision.
