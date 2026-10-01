"""
app.py
E-Commerce Data Analysis — Desktop Software (Tkinter + SQLite)
Run: python app.py
"""

import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

DB_PATH = "ecommerce.db"

BG = "#f4f6f9"
CARD = "#ffffff"
ACCENT = "#2563eb"
GREEN = "#16a34a"
RED = "#dc2626"
TEXT_MUTED = "#64748b"
TEXT_DARK = "#111827"


# ------------------------------------------------------------------
# DB helper
# ------------------------------------------------------------------
def query(sql, params=()):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return rows


def fmt_money(v):
    return f"₹{v:,.2f}" if v is not None else "₹0.00"


# ------------------------------------------------------------------
# Reusable UI helpers
# ------------------------------------------------------------------
def kpi_card(parent, label, value):
    card = tk.Frame(parent, bg=CARD, highlightbackground="#e5e7eb", highlightthickness=1)
    tk.Label(card, text=label, bg=CARD, fg=TEXT_MUTED, font=("Segoe UI", 9)).pack(
        anchor="w", padx=14, pady=(12, 2)
    )
    tk.Label(card, text=value, bg=CARD, fg=TEXT_DARK, font=("Segoe UI", 16, "bold")).pack(
        anchor="w", padx=14, pady=(0, 12)
    )
    return card


def make_table(parent, columns, rows, widths=None):
    tree = ttk.Treeview(parent, columns=columns, show="headings", height=min(len(rows), 12) or 1)
    for i, col in enumerate(columns):
        tree.heading(col, text=col)
        tree.column(col, width=(widths[i] if widths else 120), anchor="w")
    for r in rows:
        tree.insert("", "end", values=[r[c] for c in columns])
    vsb = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    parent.grid_columnconfigure(0, weight=1)
    parent.grid_rowconfigure(0, weight=1)
    return tree


def section_title(parent, text):
    tk.Label(parent, text=text, bg=BG, fg=TEXT_DARK, font=("Segoe UI", 13, "bold")).pack(
        anchor="w", pady=(16, 6)
    )


# ------------------------------------------------------------------
# Pages
# ------------------------------------------------------------------
class DashboardPage(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG)
        self.build()

    def build(self):
        kpis = query("""
            SELECT COUNT(*) AS total_orders, ROUND(SUM(revenue),2) AS total_revenue,
                   ROUND(SUM(profit),2) AS total_profit, ROUND(AVG(revenue),2) AS aov,
                   COUNT(DISTINCT customer_name) AS total_customers
            FROM sales WHERE order_status = 'delivered'
        """)[0]

        tk.Label(self, text="Executive Overview", bg=BG, fg=TEXT_DARK,
                 font=("Segoe UI", 16, "bold")).pack(anchor="w", pady=(10, 10), padx=10)

        kpi_row = tk.Frame(self, bg=BG)
        kpi_row.pack(fill="x", padx=10)
        cards = [
            ("Total Revenue", fmt_money(kpis["total_revenue"])),
            ("Total Profit", fmt_money(kpis["total_profit"])),
            ("Total Orders", str(kpis["total_orders"])),
            ("Avg Order Value", fmt_money(kpis["aov"])),
            ("Customers", str(kpis["total_customers"])),
        ]
        for label, val in cards:
            c = kpi_card(kpi_row, label, val)
            c.pack(side="left", expand=True, fill="both", padx=6)

        chart_row = tk.Frame(self, bg=BG)
        chart_row.pack(fill="both", expand=True, padx=10, pady=(10, 10))

        # Monthly trend chart
        monthly = query("""
            SELECT strftime('%Y-%m', order_date) AS month,
                   ROUND(SUM(revenue),2) AS revenue, ROUND(SUM(profit),2) AS profit
            FROM sales WHERE order_status='delivered' GROUP BY month ORDER BY month
        """)
        fig1 = Figure(figsize=(5, 3.2), dpi=100)
        ax1 = fig1.add_subplot(111)
        months = [m["month"] for m in monthly]
        ax1.plot(months, [m["revenue"] for m in monthly], marker="o", color=ACCENT, label="Revenue")
        ax1.plot(months, [m["profit"] for m in monthly], marker="o", color=GREEN, label="Profit")
        ax1.set_title("Monthly Revenue & Profit", fontsize=10)
        ax1.tick_params(axis="x", rotation=45, labelsize=7)
        ax1.tick_params(axis="y", labelsize=7)
        ax1.legend(fontsize=7)
        fig1.tight_layout()
        canvas1 = FigureCanvasTkAgg(fig1, master=chart_row)
        canvas1.draw()
        canvas1.get_tk_widget().pack(side="left", fill="both", expand=True, padx=(0, 6))

        # Top categories chart
        cats = query("""
            SELECT category, ROUND(SUM(revenue),2) AS revenue
            FROM sales WHERE order_status='delivered'
            GROUP BY category ORDER BY revenue DESC LIMIT 5
        """)
        fig2 = Figure(figsize=(5, 3.2), dpi=100)
        ax2 = fig2.add_subplot(111)
        ax2.bar([c["category"] for c in cats], [c["revenue"] for c in cats], color="#7c3aed")
        ax2.set_title("Top 5 Categories by Revenue", fontsize=10)
        ax2.tick_params(axis="x", rotation=30, labelsize=7)
        ax2.tick_params(axis="y", labelsize=7)
        fig2.tight_layout()
        canvas2 = FigureCanvasTkAgg(fig2, master=chart_row)
        canvas2.draw()
        canvas2.get_tk_widget().pack(side="left", fill="both", expand=True, padx=(6, 0))


class SalesPage(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG)
        self.category_var = tk.StringVar(value="All")
        self.status_var = tk.StringVar(value="All")
        self.build()

    def build(self):
        tk.Label(self, text="Sales", bg=BG, fg=TEXT_DARK, font=("Segoe UI", 16, "bold")).pack(
            anchor="w", padx=10, pady=(10, 6)
        )

        filter_row = tk.Frame(self, bg=BG)
        filter_row.pack(fill="x", padx=10)

        categories = ["All"] + [r["category"] for r in query("SELECT DISTINCT category FROM sales ORDER BY category")]
        statuses = ["All"] + [r["order_status"] for r in query("SELECT DISTINCT order_status FROM sales ORDER BY order_status")]

        tk.Label(filter_row, text="Category:", bg=BG).pack(side="left", padx=(0, 4))
        ttk.Combobox(filter_row, textvariable=self.category_var, values=categories, width=16, state="readonly").pack(side="left", padx=(0, 12))
        tk.Label(filter_row, text="Status:", bg=BG).pack(side="left", padx=(0, 4))
        ttk.Combobox(filter_row, textvariable=self.status_var, values=statuses, width=14, state="readonly").pack(side="left", padx=(0, 12))
        tk.Button(filter_row, text="Apply Filter", command=self.refresh, bg=ACCENT, fg="white", relief="flat", padx=10).pack(side="left")

        self.table_frame = tk.Frame(self, bg=BG)
        self.table_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.refresh()

    def refresh(self):
        for w in self.table_frame.winfo_children():
            w.destroy()

        sql = "SELECT order_id, order_date, customer_name, customer_city, product_name, category, quantity, revenue, profit, payment_type, order_status FROM sales WHERE 1=1"
        params = []
        if self.category_var.get() != "All":
            sql += " AND category = ?"
            params.append(self.category_var.get())
        if self.status_var.get() != "All":
            sql += " AND order_status = ?"
            params.append(self.status_var.get())
        sql += " ORDER BY order_date DESC"
        rows = query(sql, params)

        cols = ["order_id", "order_date", "customer_name", "customer_city", "product_name",
                "category", "quantity", "revenue", "profit", "payment_type", "order_status"]
        widths = [60, 130, 130, 100, 130, 110, 50, 80, 80, 100, 90]
        make_table(self.table_frame, cols, rows, widths)


class CustomersPage(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG)
        self.build()

    def build(self):
        tk.Label(self, text="Customers", bg=BG, fg=TEXT_DARK, font=("Segoe UI", 16, "bold")).pack(
            anchor="w", padx=10, pady=(10, 6)
        )

        repeat = query("""
            WITH oc AS (
                SELECT customer_name, COUNT(*) AS orders FROM sales
                WHERE order_status='delivered' GROUP BY customer_name
            )
            SELECT SUM(CASE WHEN orders>1 THEN 1 ELSE 0 END) AS repeat_customers,
                   COUNT(*) AS total_customers,
                   ROUND(100.0*SUM(CASE WHEN orders>1 THEN 1 ELSE 0 END)/COUNT(*),2) AS repeat_rate_pct
            FROM oc
        """)[0]

        kpi_row = tk.Frame(self, bg=BG)
        kpi_row.pack(fill="x", padx=10)
        for label, val in [
            ("Total Customers", str(repeat["total_customers"])),
            ("Repeat Customers", str(repeat["repeat_customers"])),
            ("Repeat Rate", f"{repeat['repeat_rate_pct']}%"),
        ]:
            kpi_card(kpi_row, label, val).pack(side="left", expand=True, fill="both", padx=6)

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=10, pady=10)

        left = tk.Frame(body, bg=BG)
        left.pack(side="left", fill="both", expand=True, padx=(0, 6))
        section_title(left, "Top 15 Customers by Lifetime Value")
        table_holder = tk.Frame(left, bg=BG)
        table_holder.pack(fill="both", expand=True)
        top_customers = query("""
            SELECT customer_name, customer_city, customer_state, COUNT(*) AS num_orders,
                   ROUND(SUM(revenue),2) AS lifetime_value
            FROM sales WHERE order_status='delivered'
            GROUP BY customer_name, customer_city, customer_state
            ORDER BY lifetime_value DESC LIMIT 15
        """)
        make_table(table_holder, ["customer_name", "customer_city", "customer_state", "num_orders", "lifetime_value"],
                   top_customers, [140, 100, 60, 70, 100])

        right = tk.Frame(body, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=(6, 0))
        section_title(right, "Revenue by State")
        states = query("""
            SELECT customer_state, ROUND(SUM(revenue),2) AS revenue
            FROM sales WHERE order_status='delivered'
            GROUP BY customer_state ORDER BY revenue DESC
        """)
        fig = Figure(figsize=(4.5, 4), dpi=100)
        ax = fig.add_subplot(111)
        ax.barh([s["customer_state"] for s in states][::-1], [s["revenue"] for s in states][::-1], color="#0891b2")
        ax.set_title("Revenue by State", fontsize=10)
        ax.tick_params(labelsize=7)
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=right)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)


class ProductsPage(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG)
        self.build()

    def build(self):
        tk.Label(self, text="Products", bg=BG, fg=TEXT_DARK, font=("Segoe UI", 16, "bold")).pack(
            anchor="w", padx=10, pady=(10, 6)
        )

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        left = tk.Frame(body, bg=BG)
        left.pack(side="left", fill="both", expand=True, padx=(0, 6))
        section_title(left, "Category Performance")
        cat_holder = tk.Frame(left, bg=BG)
        cat_holder.pack(fill="both", expand=True)
        category_perf = query("""
            SELECT category, ROUND(SUM(revenue),2) AS revenue, ROUND(SUM(profit),2) AS profit,
                   ROUND(100.0*SUM(profit)/NULLIF(SUM(revenue),0),2) AS margin_pct
            FROM sales WHERE order_status='delivered' GROUP BY category ORDER BY revenue DESC
        """)
        make_table(cat_holder, ["category", "revenue", "profit", "margin_pct"], category_perf, [130, 90, 90, 80])

        section_title(left, "Top / Bottom 5 Products by Revenue")
        tb_holder = tk.Frame(left, bg=BG)
        tb_holder.pack(fill="both", expand=True)
        top_p = query("""SELECT product_name, category, ROUND(SUM(revenue),2) AS revenue
                          FROM sales WHERE order_status='delivered'
                          GROUP BY product_name, category ORDER BY revenue DESC LIMIT 5""")
        bottom_p = query("""SELECT product_name, category, ROUND(SUM(revenue),2) AS revenue
                             FROM sales WHERE order_status='delivered'
                             GROUP BY product_name, category ORDER BY revenue ASC LIMIT 5""")
        make_table(tb_holder, ["product_name", "category", "revenue"], top_p + bottom_p, [140, 110, 90])

        right = tk.Frame(body, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=(6, 0))
        section_title(right, "Revenue vs Profit by Category")
        fig = Figure(figsize=(4.8, 4.5), dpi=100)
        ax = fig.add_subplot(111)
        cats = [c["category"] for c in category_perf]
        x = range(len(cats))
        w = 0.35
        ax.bar([i - w/2 for i in x], [c["revenue"] for c in category_perf], width=w, label="Revenue", color=ACCENT)
        ax.bar([i + w/2 for i in x], [c["profit"] for c in category_perf], width=w, label="Profit", color=GREEN)
        ax.set_xticks(list(x))
        ax.set_xticklabels(cats, rotation=30, fontsize=7, ha="right")
        ax.tick_params(axis="y", labelsize=7)
        ax.legend(fontsize=8)
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=right)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)


class RevenuePage(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG)
        self.build()

    def build(self):
        totals = query("""
            SELECT ROUND(SUM(revenue),2) AS total_revenue, ROUND(SUM(profit),2) AS total_profit,
                   ROUND(100.0*SUM(profit)/NULLIF(SUM(revenue),0),2) AS margin_pct
            FROM sales WHERE order_status='delivered'
        """)[0]

        tk.Label(self, text="Revenue & Profit", bg=BG, fg=TEXT_DARK, font=("Segoe UI", 16, "bold")).pack(
            anchor="w", padx=10, pady=(10, 6)
        )

        kpi_row = tk.Frame(self, bg=BG)
        kpi_row.pack(fill="x", padx=10)
        for label, val in [
            ("Total Revenue", fmt_money(totals["total_revenue"])),
            ("Total Profit", fmt_money(totals["total_profit"])),
            ("Overall Margin", f"{totals['margin_pct']}%"),
        ]:
            kpi_card(kpi_row, label, val).pack(side="left", expand=True, fill="both", padx=6)

        monthly = query("""
            SELECT strftime('%Y-%m', order_date) AS month, ROUND(SUM(revenue),2) AS revenue,
                   ROUND(SUM(profit),2) AS profit,
                   ROUND(100.0*SUM(profit)/NULLIF(SUM(revenue),0),2) AS margin_pct
            FROM sales WHERE order_status='delivered' GROUP BY month ORDER BY month
        """)

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=10, pady=10)

        chart_frame = tk.Frame(body, bg=BG)
        chart_frame.pack(fill="both", expand=True)
        fig = Figure(figsize=(9, 3.2), dpi=100)
        ax = fig.add_subplot(111)
        ax2 = ax.twinx()
        months = [m["month"] for m in monthly]
        ax.plot(months, [m["revenue"] for m in monthly], marker="o", color=ACCENT, label="Revenue")
        ax.plot(months, [m["profit"] for m in monthly], marker="o", color=GREEN, label="Profit")
        ax2.plot(months, [m["margin_pct"] for m in monthly], marker="s", color=RED, linestyle="--", label="Margin %")
        ax.set_title("Monthly Revenue, Profit & Margin", fontsize=10)
        ax.tick_params(axis="x", rotation=45, labelsize=7)
        ax.tick_params(axis="y", labelsize=7)
        ax2.tick_params(axis="y", labelsize=7)
        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, fontsize=7, loc="upper left")
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

        section_title(body, "Revenue by Payment Type")
        pay_holder = tk.Frame(body, bg=BG)
        pay_holder.pack(fill="both", expand=True)
        payment = query("""
            SELECT payment_type, COUNT(*) AS orders, ROUND(SUM(revenue),2) AS revenue
            FROM sales WHERE order_status='delivered'
            GROUP BY payment_type ORDER BY revenue DESC
        """)
        make_table(pay_holder, ["payment_type", "orders", "revenue"], payment, [140, 80, 100])


# ------------------------------------------------------------------
# Main window
# ------------------------------------------------------------------
class ECommerceApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("E-Commerce Data Analysis — Desktop")
        self.geometry("1150x720")
        self.configure(bg=BG)
        self.minsize(950, 600)

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Treeview", rowheight=24, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))
        style.configure("TNotebook.Tab", padding=(16, 8), font=("Segoe UI", 10))

        try:
            query("SELECT 1 FROM sales LIMIT 1")
        except sqlite3.OperationalError:
            messagebox.showerror(
                "Database not found",
                "ecommerce.db has no 'sales' table.\nRun generate_data.py first.",
            )
            self.destroy()
            return

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        notebook.add(DashboardPage(notebook), text="  Dashboard  ")
        notebook.add(SalesPage(notebook), text="  Sales  ")
        notebook.add(CustomersPage(notebook), text="  Customers  ")
        notebook.add(ProductsPage(notebook), text="  Products  ")
        notebook.add(RevenuePage(notebook), text="  Revenue & Profit  ")


if __name__ == "__main__":
    app = ECommerceApp()
    app.mainloop()
