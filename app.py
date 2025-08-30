import pandas as pd
import pandas_datareader.data as web
import datetime
import streamlit as st
import plotly.graph_objects as go

# --- Streamlit App Configuration ---
st.set_page_config(
    page_title="U.S. Treasury Yield Curve Analyzer",
    layout="wide", # Use a wide layout for better chart visibility
    initial_sidebar_state="expanded"
)

# --- 1. Data Fetching and Caching ---
# Define FRED series IDs for various Treasury maturities
FRED_SERIES_IDS = {
    '1 Mo': 'DGS1MO', '3 Mo': 'DGS3MO', '6 Mo': 'DGS6MO', '1 Yr': 'DGS1',
    '2 Yr': 'DGS2', '3 Yr': 'DGS3', '5 Yr': 'DGS5', '7 Yr': 'DGS7',
    '10 Yr': 'DGS10', '20 Yr': 'DGS20', '30 Yr': 'DGS30',
}

# Map maturities to numerical values for plotting
MATURITY_MAP = {
    '1 Mo': 1/12, '3 Mo': 3/12, '6 Mo': 6/12, '1 Yr': 1, '2 Yr': 2, '3 Yr': 3,
    '5 Yr': 5, '7 Yr': 7, '10 Yr': 10, '20 Yr': 20, '30 Yr': 30,
}

# Streamlit's caching decorator for data loading
@st.cache_data
def get_yield_data(start_date, end_date):
    """Fetches yield data from FRED for the specified date range."""
    try:
        # Removed max_tries as it's not supported by older pandas_datareader versions
        data = web.DataReader(list(FRED_SERIES_IDS.values()), 'fred', start_date, end_date)
        data.columns = [key for key in FRED_SERIES_IDS.keys()] # Rename columns to friendly names
        return data
    except Exception as e:
        st.error(f"Error fetching data from FRED: {e}") # Use st.error for Streamlit display
        return pd.DataFrame() # Return empty DataFrame on error

# Pre-fetch a reasonable range of data to improve initial load time
today = datetime.date.today()
end_fetch_date = today - datetime.timedelta(days=1) # Get data up to yesterday
start_fetch_date = end_fetch_date - datetime.timedelta(days=365 * 5) # Last 5 years

all_yield_data = get_yield_data(start_fetch_date, end_fetch_date)

if all_yield_data.empty:
    st.error("Failed to load initial yield data. The app might not function correctly.")
    min_date = datetime.date(2000, 1, 1)
    max_date = today
else:
    min_date = all_yield_data.index.min().date()
    max_date = all_yield_data.index.max().date()


## Streamlit App Layout

# Streamlit apps are built by calling Streamlit commands in a Python script. The layout is determined by the order of these calls.

### Sidebar

st.sidebar.title('U.S. Treasury Yield Curve Analyzer')
st.sidebar.markdown("### Select Date")

# Date picker for selecting the yield curve date
selected_date = st.sidebar.date_input(
    label='Select Date',
    value=max_date, # Default to the most recent available date
    min_value=min_date,
    max_value=max_date,
    help="Choose a date to view the U.S. Treasury yield curve."
)

st.sidebar.markdown("""
    ---
    This application fetches U.S. Treasury yield data from the Federal Reserve Economic Data (FRED)
    and displays the yield curve for a selected date.

    **Maturities available:** 1-Month, 3-Month, 6-Month, 1-Year, 2-Year, 3-Year, 5-Year, 7-Year, 10-Year, 20-Year, 30-Year.

    Data provided by FRED.
""")

### Main Content
# Placeholder for status messages (will be updated dynamically)
status_text_placeholder = st.empty()
status_text_placeholder.markdown("Select a date to view the yield curve.")

# --- Plotting Logic (integrated directly into the app flow) ---
if all_yield_data.empty:
    status_text_placeholder.error("Error: Yield data could not be retrieved from FRED. Please check your internet connection or try again later.")
    st.plotly_chart(go.Figure().add_annotation(text="No data available", xref="paper", yref="paper", showarrow=False))
else:
    # Ensure selected_date is a datetime.date object
    if isinstance(selected_date, datetime.datetime):
        selected_date = selected_date.date()

    # Find the closest available date in the data
    available_dates = all_yield_data.index.date
    actual_date = None

    if selected_date not in available_dates:
        valid_dates = available_dates[available_dates <= selected_date]
        if not valid_dates.size:
            status_text_placeholder.warning(f"No data available on or before {selected_date.strftime('%Y-%m-%d')}. Please select an earlier date.")
            st.plotly_chart(go.Figure().add_annotation(text="No data available for this date range", xref="paper", yref="paper", showarrow=False))
        else:
            actual_date = max(valid_dates)
            status_text_placeholder.info(f"Showing yield curve for **{actual_date.strftime('%Y-%m-%d')}** (closest available date to {selected_date.strftime('%Y-%m-%d')}).")
    else:
        actual_date = selected_date
        status_text_placeholder.empty() # Clear initial message
        status_text_placeholder.success(f"Showing yield curve for **{actual_date.strftime('%Y-%m-%d')}**.")

    if actual_date: # Only proceed if a valid date was found
        daily_data = all_yield_data.loc[str(actual_date)]

        if isinstance(daily_data, pd.DataFrame):
            daily_data = daily_data.iloc[-1]

        plot_data = pd.DataFrame({
            'Maturity (Years)': [MATURITY_MAP[m] for m in daily_data.index],
            'Yield (%)': daily_data.values
        }).dropna()

        if plot_data.empty:
            status_text_placeholder.warning(f"No complete yield curve data available for {actual_date.strftime('%Y-%m-%d')}.")
            st.plotly_chart(go.Figure().add_annotation(text="No complete data for this date", xref="paper", yref="paper", showarrow=False))
        else:
            # --- Create Plotly Figure ---
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=plot_data['Maturity (Years)'],
                y=plot_data['Yield (%)'],
                mode='lines+markers',
                name='Yield Curve',
                line=dict(color='blue', width=3),
                marker=dict(size=8, color='blue', symbol='circle')
            ))

            fig.update_layout(
                title={
                    'text': f'U.S. Treasury Yield Curve: {actual_date.strftime("%Y-%m-%d")}',
                    'x': 0.5, 'xanchor': 'center'
                },
                xaxis_title='Maturity (Years)', yaxis_title='Yield (%)',
                hovermode='x unified', margin=dict(l=40, r=40, t=80, b=40),
                autosize=True,
                yaxis=dict(range=[plot_data['Yield (%)'].min() * 0.9, plot_data['Yield (%)'].max() * 1.1])
            )

            # Display the Plotly figure in Streamlit
            st.plotly_chart(fig, use_container_width=True) # use_container_width makes it responsive
