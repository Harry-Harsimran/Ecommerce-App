# E-Commerce Data Analysis — Desktop Software

A standalone desktop application (Tkinter + SQLite + matplotlib) — no browser,
no server.  Same 200-row sample dataset, now with a **liquid-glass UI**:
frosted translucent panels, specular rims, a glowing gradient backdrop,
glass filter chips, a custom glass table and transparent charts.

`app_classic.py` is the previous flat UI, kept for reference.

## Setup

```bash
pip install -r requirements.txt
python generate_data.py   
python app.py               
```


## Tabs

| Tab              | What it shows                                                   |
|-------------------|------------------------------------------------------------------|
| Dashboard         | KPI cards, monthly revenue/profit chart, top-5-category chart    |
| Sales             | Filterable order table (click glass chips for status/category)   |
| Customers         | Top 15 by lifetime value, repeat-rate KPIs, revenue-by-state chart|
| Products          | Category margin table, top/bottom 5 products, revenue-vs-profit chart |
| Revenue & Profit  | Monthly revenue/profit/margin chart, payment-type breakdown table|

## Structure

```
ecommerce_desktop_app/
├── app.py              (liquid-glass UI)
├── app_classic.py      (previous UI)
├── generate_data.py    
├── requirements.txt
├── ecommerce.db          
└── README.md
```