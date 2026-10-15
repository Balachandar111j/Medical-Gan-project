<<<<<<< HEAD
# Medical-Gan-project
Synthetic Data Generation for Imbalanced Medical Datasets Using GANs. It uses CTGAN to generate synthetic malignant tumor records for the Breast Cancer Wisconsin dataset (212 malignant vs 357 benign), compares Baseline, SMOTE and CTGAN with leakage-safe evaluation, and reports results honestly.
=======
# Retail Sales and Customer Purchasing Analysis Using Exploratory Data Analysis and Data Visualization

Undergraduate mini project (Artificial Intelligence and Data Science) analysing the Sample Superstore retail dataset with Python.

## What the project does
- Cleans and validates 9,994 retail transactions (2014–2017) and documents every cleaning decision.
- Covers all five syllabus units: EDA, Matplotlib visualisation, univariate, bivariate and multivariate analysis.
- Produces 31 charts, 31 summary tables and a results table answering 10 business questions.
- Includes a **live interactive dashboard** (Streamlit) with filters, a discount what-if simulator and EDA explorer.

## Folder structure
```
Retail_Sales_Analysis/
├── app/
│   ├── streamlit_app.py          # interactive dashboard
│   ├── data_utils.py             # loading + cleaning (same rules as the notebook)
│   └── requirements.txt          # app-only libraries (used by Streamlit Cloud)
├── .streamlit/config.toml        # dashboard theme
├── data/
│   ├── original_dataset.csv      # raw file, never modified
│   └── cleaned_dataset.csv       # output of notebook Section 20
├── notebooks/
│   └── retail_sales_analysis.ipynb
├── outputs/
│   ├── charts/                   # 31 PNG charts
│   ├── summary_tables/           # 31 CSV tables (incl. cleaning_log.csv)
│   └── app_screenshots/          # dashboard screenshots for the report
├── report/                       # mini_project_report.docx / .pdf (Phase 9)
├── presentation/                 # mini_project_presentation.pptx (Phase 10)
├── README.md
└── requirements.txt
```

## Run the dashboard (macOS / Windows / Linux)
1. Unzip the project and open Terminal in the `Retail_Sales_Analysis` folder.
2. Create a virtual environment and install the libraries:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Start the app:
   ```bash
   streamlit run app/streamlit_app.py
   ```
4. Your browser opens at `http://localhost:8501`. Press `Ctrl + C` in Terminal to stop it.

### Dashboard features
- **Sidebar filters:** date range, region, segment, category, sub-category, discount range — every chart updates.
- **Overview:** KPI tiles, monthly sales trend with 3-month average, monthly profit, auto-generated insights.
- **Products:** category sales vs profit, sub-category profit, top sellers and biggest loss-makers.
- **Regions & Segments:** region × category heatmap, US state profit map, weakest states, segment comparison.
- **Discounts & What-if:** margin by discount band, discount vs profit scatter, and a slider that simulates capping discounts.
- **EDA (Units 3–5):** pick a variable → statistics, IQR outliers, histogram, box plot; Pearson/Spearman heatmap.
- **Data:** cleaning summary, filtered table, CSV download, and upload of your own Superstore-style file.

### Put it online (free) for the review
1. Push this folder to a GitHub repository.
2. Go to share.streamlit.io → *Create app* → choose the repository.
3. Main file path: `app/streamlit_app.py` → *Deploy*. You get a public link to open on any device.

## Run the notebook
**Google Colab**
1. Upload `notebooks/retail_sales_analysis.ipynb` to Colab.
2. *Runtime → Run all*.
3. Choose the dataset file when Section 5 shows the upload button.
4. Section 20 downloads a ZIP of the whole project folder.

**VS Code / Jupyter**
1. `pip install -r requirements.txt`
2. Keep the dataset at `data/original_dataset.csv`.
3. Open the notebook and *Run All*.

## Dataset
- Sample Superstore (Kaggle: `vivek468/superstore-dataset-final`), fictional US retailer.
- 9,994 rows × 21 columns; totals: sales $2,297,200.86, profit $286,397.02.
- Data-quality issues found and handled: mixed date formats (`4/15/2017` and `11-08-2016`), one inconsistent Category label, trailing spaces in 16 product names, one near-duplicate pair.

## Key findings
- Technology leads sales ($836K) and profit ($145K); Furniture earns only a 2.5% margin.
- Every transaction with a discount above 40% lost money; discounts above 20% lost $135K combined.
- Tables (−$17.7K), Bookcases and Supplies are loss-making sub-categories; 301 products lose money.
- Central region has the lowest margin (7.9%); West has the highest (14.9%).
- Sales peak in September and November–December.

## Notes
- The state map downloads its US outline from the internet (Plotly CDN); without internet it stays blank, but the "10 states with the lowest profit" chart below it still works.
- The discount what-if assumes customers keep buying the same quantity, so it is an upper estimate, not a forecast.

## Tools
Python, Pandas, NumPy, Matplotlib, Seaborn, SciPy (p-values), Scikit-learn (optional PCA), Streamlit and Plotly (dashboard).
>>>>>>> 946b788 (Initial commit)
