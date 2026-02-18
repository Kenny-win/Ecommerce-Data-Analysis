import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st
from babel.numbers import format_currency
sns.set(style='dark')

def create_order_delivered_revenue_df(data):
    data["payment_value"] = pd.to_numeric(data["payment_value"], errors="coerce")
    data = data[data["order_status"].eq("delivered")].copy()
    data["month"] = data["order_purchase_timestamp"].dt.to_period("M")

    order_level = (
        data.groupby(["month", "order_id"], as_index=False)
            .agg(order_revenue=("payment_value", "sum"))
    )

    monthly_perf = (
        order_level.groupby("month", as_index=False)
            .agg(
                n_delivered_orders=("order_id", "nunique"),
                revenue=("order_revenue", "sum"),
                aov=("order_revenue", "mean"),
            )
            .sort_values("month")
    )

    last_n = 12
    monthly_last = monthly_perf.tail(last_n).copy()
    monthly_last["month"] = monthly_last["month"].astype(str)
    
    return monthly_last

def create_sum_order_items_df(data):
    data = data[data["order_status"].eq("delivered")].copy()
    data = data.dropna(subset=["product_category_name"])

    units_by_cat = (
    data.drop_duplicates(subset=["order_id", "order_item_id"])
        .groupby("product_category_name")
        .size()
        .rename("units_sold")
        .reset_index()
        .sort_values("units_sold", ascending=False)
    )
    return units_by_cat

def top_rfm_df(data):
    data["payment_value"] = pd.to_numeric(data["payment_value"], errors="coerce")
    data = data[data["order_status"].eq("delivered")].copy()

    order_level = (
        data.groupby(["customer_unique_id", "order_id"], as_index=False)
            .agg(
                order_date=("order_purchase_timestamp", "max"),
                order_value=("payment_value", "sum"),
            )
            .dropna(subset=["customer_unique_id", "order_id", "order_date", "order_value"])
    )

    analysis_date = order_level["order_date"].max().normalize() + pd.Timedelta(days=1)

    recency = (
        order_level.groupby("customer_unique_id", as_index=False)
            .agg(last_purchase=("order_date", "max"))
    )
    recency["recency_days"] = (analysis_date - recency["last_purchase"].dt.normalize()).dt.days

    TOP_N = 15
    top_recency = (
        recency.nsmallest(TOP_N, "recency_days")
            .sort_values("recency_days", ascending=True)
    )

    X_MONTHS = 6
    start_date = analysis_date - pd.DateOffset(months=X_MONTHS)

    last6 = order_level[order_level["order_date"] >= start_date].copy()

    rfm_6m = (
        last6.groupby("customer_unique_id", as_index=False)
            .agg(
                frequency=("order_id", "nunique"),
                monetary=("order_value", "sum"),
            )
    )

    top_frequency = (
        rfm_6m.nlargest(TOP_N, "frequency")
            .sort_values("frequency", ascending=True)
    )

    top_monetary = (
        rfm_6m.nlargest(TOP_N, "monetary")
            .sort_values("monetary", ascending=True)
    )

    return [top_recency, top_frequency, top_monetary]

def all_rfm_df(data):
    data["payment_value"] = pd.to_numeric(data["payment_value"], errors="coerce")
    data = data[data["order_status"].eq("delivered")].copy()

    order_level = (
        data.groupby(["customer_unique_id", "order_id"], as_index=False)
            .agg(
                order_date=("order_purchase_timestamp", "max"),
                order_value=("payment_value", "sum"),
            )
            .dropna(subset=["customer_unique_id", "order_id", "order_date", "order_value"])
    )
    return order_level

def recency(data):
    analysis_date = data["order_date"].max().normalize() + pd.Timedelta(days=1)
    recency_df = (
        data.groupby("customer_unique_id", as_index=False)
            .agg(last_purchase=("order_date", "max"))
    )
    recency_df["recency_days"] = (analysis_date - recency_df["last_purchase"].dt.normalize()).dt.days
    return recency_df

def frequency_monetary(data):
    X_MONTHS = 6
    analysis_date = data["order_date"].max().normalize() + pd.Timedelta(days=1)
    start_date = analysis_date - pd.DateOffset(months=X_MONTHS)

    last6 = data[data["order_date"] >= start_date].copy()

    rfm_6m = (
        last6.groupby("customer_unique_id", as_index=False)
            .agg(
                frequency=("order_id", "nunique"),
                monetary=("order_value", "sum"),
            )
    )

    return rfm_6m

all_df = pd.read_csv("all_data.csv")
print(all_df.info())

datetime_columns = ["order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date", "order_delivered_customer_date", "order_estimated_delivery_date"]
all_df.sort_values(by="order_purchase_timestamp", inplace=True)
all_df.reset_index(inplace=True)
 
for column in datetime_columns:
    all_df[column] = pd.to_datetime(all_df[column])

min_date = all_df["order_purchase_timestamp"].min()
max_date = all_df["order_purchase_timestamp"].max()

with st.sidebar:
    # Menambahkan logo perusahaan
    st.image("https://raw.githubusercontent.com/Kenny-win/Ecommerce-Data-Analysis/main/asset/logo.png")
    
    # Mengambil start_date & end_date dari date_input
    start_date, end_date = st.date_input(
        label='Rentang Waktu',min_value=min_date,
        max_value=max_date,
        value=[min_date, max_date]
    )

main_df = all_df[(all_df["order_purchase_timestamp"] >= str(start_date)) & 
                (all_df["order_purchase_timestamp"] <= str(end_date))]


order_delivered_revenue_df = create_order_delivered_revenue_df(main_df)
sum_order_items_df = create_sum_order_items_df(main_df)
rfm_df = top_rfm_df(main_df)
all_rfm = all_rfm_df(main_df)
recency_df = recency(all_rfm)
frequency_monetary_df = frequency_monetary(all_rfm)



st.header('XYZ E-commerce Company Dashboard :sparkles:')

st.subheader('Performa Penjualan dan Revenue Perusahaan')
 
col1, col2 = st.columns(2)
 
with col1:
    total_orders = order_delivered_revenue_df.n_delivered_orders.sum()
    st.metric("Total orders", value=total_orders)
 
with col2:
    total_revenue = format_currency(order_delivered_revenue_df.revenue.sum(), "USD",locale='en_US') 
    st.metric("Total Revenue", value=total_revenue)

# Tren Penjualan (jumlah delivered orders)
fig1, ax = plt.subplots(figsize=(10, 4))

ax.plot(
    order_delivered_revenue_df["month"],
    order_delivered_revenue_df["n_delivered_orders"],
    marker='o',
    linewidth=2
)

ax.set_title("Tren Penjualan (Jumlah Delivered Orders) - 12 Bulan Terakhir")
ax.set_xlabel("Bulan")
ax.set_ylabel("Jumlah Delivered Orders")

ax.tick_params(axis='y', labelsize=12)
ax.tick_params(axis='x', labelsize=10, rotation=45)

ax.grid(True, alpha=0.3)

plt.tight_layout()
st.pyplot(fig1)


# Tren Revenue (Delivred Orders)
fig2, ax = plt.subplots(figsize=(10, 4))

ax.plot(
    order_delivered_revenue_df["month"],
    order_delivered_revenue_df["revenue"],
    marker='o',
    linewidth=2,
    color="tab:green"
)

ax.set_title("Tren Revenue (Delivered Orders) - 12 Bulan Terakhir")
ax.set_xlabel("Bulan")
ax.set_ylabel("Revenue (Total Payment Value)")

ax.tick_params(axis='y', labelsize=12)
ax.tick_params(axis='x', labelsize=10, rotation=45)
ax.grid(True, alpha=0.3)
plt.tight_layout()
st.pyplot(fig2)


# Tren AOV (Average Order Value)
fig3, ax = plt.subplots(figsize=(10, 4))

ax.plot(
    order_delivered_revenue_df["month"],
    order_delivered_revenue_df["aov"],
    marker='o',
    linewidth=2,
    color="tab:orange"
)

ax.set_title("Tren AOV (Average Order Value) - 12 Bulan Terakhir")
ax.set_xlabel("Bulan")
ax.set_ylabel("AOV")

ax.tick_params(axis='y', labelsize=12)
ax.tick_params(axis='x', labelsize=10, rotation=45)

ax.grid(True, alpha=0.3)

plt.tight_layout()
st.pyplot(fig3)

# Delivered Orders vs Revenue
fig4, ax1 = plt.subplots(figsize=(10,4))

ax1.plot(order_delivered_revenue_df["month"], order_delivered_revenue_df["n_delivered_orders"], marker="o", color="tab:blue")
ax1.set_xlabel("Bulan")
ax1.set_ylabel("Delivered Orders", color="tab:blue")
ax1.tick_params(axis="y", labelcolor="tab:blue")
ax1.grid(True, alpha=0.3)

ax2 = ax1.twinx()
ax2.plot(order_delivered_revenue_df["month"], order_delivered_revenue_df["revenue"], marker="o", color="tab:green")
ax2.set_ylabel("Revenue", color="tab:green")
ax2.tick_params(axis="y", labelcolor="tab:green")

plt.title("Performa Bulanan: Delivered Orders vs Revenue (12 Bulan Terakhir)")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
st.pyplot(fig4)


st.subheader('Produk Terbaik dan Terburuk')

# Top 10 Kategori Produk Paling Banyak Terjual
fig5, ax = plt.subplots(figsize=(10, 5))
top10_most_sold = sum_order_items_df.head(10)
bottom10_least_sold = sum_order_items_df.tail(10)

ax.barh(
    top10_most_sold["product_category_name"][::-1],
    top10_most_sold["units_sold"][::-1]
)

ax.set_title("Top 10 Kategori Produk Paling Banyak Terjual (Delivered)")
ax.set_xlabel("Jumlah Unit Terjual")
ax.set_ylabel("Kategori Produk")

ax.tick_params(axis='x', labelsize=12)
ax.tick_params(axis='y', labelsize=10)

ax.grid(axis='x', alpha=0.3)

plt.tight_layout()
st.pyplot(fig5)

# Bottom 10 Kategori Produk Paling Sedikit Terjual
fig6, ax = plt.subplots(figsize=(10, 5))

ax.barh(
    bottom10_least_sold["product_category_name"][::-1],
    bottom10_least_sold["units_sold"][::-1],
    color="tab:red"
)

ax.set_title("Bottom 10 Kategori Produk Paling Sedikit Terjual (Delivered)")
ax.set_xlabel("Jumlah Unit Terjual")
ax.set_ylabel("Kategori Produk")

ax.tick_params(axis='x', labelsize=12)
ax.tick_params(axis='y', labelsize=10)

ax.grid(axis='x', alpha=0.3)

plt.tight_layout()
st.pyplot(fig6)

# RFM Visualization
st.subheader('Pelanggan Terbaik Berdasarkan Analisis RFM')

col1, col2, col3 = st.columns(3)
 
with col1:
    avg_recency = round(recency_df.recency_days.mean(), 1)
    st.metric("Average Recency (days)", value=avg_recency)
 
with col2:
    avg_frequency = round(frequency_monetary_df.frequency.mean(), 2)
    st.metric("Average Frequency", value=avg_frequency)
 
with col3:
    avg_frequency = format_currency(frequency_monetary_df.monetary.mean(), "USD",locale='en_US') 
    st.metric("Average Monetary", value=avg_frequency)


fig7, axes = plt.subplots(1, 3, figsize=(18, 5))
top_recency = rfm_df[0]
top_frequency = rfm_df[1]
top_monetary = rfm_df[2]
TOP_N = 15
X_MONTHS = 6

# Recency
axes[0].barh(top_recency["customer_unique_id"], top_recency["recency_days"], color="tab:blue")
axes[0].set_title(f"Top {TOP_N} Paling Baru Transaksi (Recency)")
axes[0].set_xlabel("Recency (hari sejak transaksi terakhir)")
axes[0].set_ylabel("customer_unique_id")
axes[0].invert_yaxis()

# Frequency
axes[1].barh(top_frequency["customer_unique_id"], top_frequency["frequency"], color="tab:green")
axes[1].set_title(f"Top {TOP_N} Paling Sering Beli (Frequency) - {X_MONTHS} Bulan")
axes[1].set_xlabel("Jumlah order (6 bulan terakhir)")
axes[1].set_ylabel("customer_unique_id")

# Monetary
axes[2].barh(top_monetary["customer_unique_id"], top_monetary["monetary"], color="tab:orange")
axes[2].set_title(f"Top {TOP_N} Pengeluaran Terbesar (Monetary) - {X_MONTHS} Bulan")
axes[2].set_xlabel("Total pengeluaran (payment_value) 6 bulan terakhir")
axes[2].set_ylabel("customer_unique_id")

plt.tight_layout()
st.pyplot(fig7)