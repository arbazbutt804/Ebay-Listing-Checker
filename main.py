import streamlit as st
import pandas as pd
from datetime import datetime, timedelta


def read_csv_filtered(file, expected_columns, dtype=None, delimiter=',', skiprows=None):
    try:
        df = pd.read_csv(file, dtype=dtype, delimiter=delimiter, encoding='utf-8', skiprows=skiprows)
        missing_columns = [col for col in expected_columns if col not in df.columns]
        if missing_columns:
            st.error(f"Missing expected columns: {', '.join(missing_columns)}")
            return None
        return df
    except Exception as e:
        st.error(f"Error reading the CSV file: {e}")
        return None


def format_item_number(item_number):
    return '{:.0f}'.format(float(item_number)) if item_number else ''


def process_ebay_data(listing_file, order_file):
    expected_order_columns = ['Item number', 'Sale date']
    order_data = read_csv_filtered(order_file, expected_order_columns, dtype={'Item number': str}, skiprows=1)

    if order_data is None:
        return None, None

    order_data['Item number'] = order_data['Item number'].apply(format_item_number)
    order_data['Sale date'] = pd.to_datetime(order_data['Sale date'], errors='coerce')
    order_data = order_data.dropna(subset=['Sale date'])

    expected_listing_columns = ['Item number', 'Start date', 'Available quantity']
    listing_data = read_csv_filtered(listing_file, expected_listing_columns, dtype={'Item number': str})

    if listing_data is None:
        return None, None

    listing_data['Item number'] = listing_data['Item number'].apply(format_item_number)
    listing_data['Start date'] = pd.to_datetime(listing_data['Start date'], errors='coerce')

    sixty_days_ago = datetime.now() - timedelta(days=60)
    recent_sales = order_data[order_data['Sale date'] > sixty_days_ago]
    sold_items = set(recent_sales['Item number'])
    sold_df = pd.DataFrame(list(sold_items), columns=['Sold Item Numbers'])

    unsold_items = []
    for index, row in listing_data.iterrows():
        item_number = row['Item number']
        available_quantity = row['Available quantity']
        start_date = row['Start date']
        if (item_number not in sold_items) and (available_quantity > 0) and (start_date < sixty_days_ago):
            unsold_items.append(item_number)

    unsold_df = pd.DataFrame(unsold_items, columns=['Unsold Item Numbers'])

    return sold_df, unsold_df


def get_download_link(df, filename):
    csv = df.to_csv(index=False)
    return st.download_button(label=f"{filename}", data=csv, file_name=filename, mime='text/csv', use_container_width=True)


# Streamlit UI
st.set_page_config(page_title="eBay Sales Analyzer", layout="centered")
st.title("📊 eBay Unsold Items Analyzer")
st.write("Upload your eBay Listing and Order CSV files to analyze which items haven't been sold in the last 60 days.")

listing_file = st.file_uploader("Upload eBay Listing Data CSV", type=['csv'])
order_file = st.file_uploader("Upload eBay Order Details CSV", type=['csv'])

if 'sold_df' not in st.session_state:
    st.session_state.sold_df = None
if 'unsold_df' not in st.session_state:
    st.session_state.unsold_df = None

if listing_file and order_file:
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🔍 Process Data", use_container_width=True):
            with st.spinner("Processing..."):
                sold_df, unsold_df = process_ebay_data(listing_file, order_file)
                if sold_df is not None and unsold_df is not None:
                    st.session_state.sold_df = sold_df
                    st.session_state.unsold_df = unsold_df

if st.session_state.sold_df is not None and st.session_state.unsold_df is not None:
    col1, col2 = st.columns(2)
    with col1:
        get_download_link(st.session_state.sold_df, "sold_items.csv")
    with col2:
        get_download_link(st.session_state.unsold_df, "unsold_items.csv")
