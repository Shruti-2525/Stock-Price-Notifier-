import streamlit as st
import requests
from bs4 import BeautifulSoup
import yfinance as yf
import plotly.graph_objs as go
import os
import time
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv('data.env')

# Function to send email notifications using SendGrid
def send_email_notification(to_email, stock_name, current_price):
    sender_email = os.getenv('SENDER_EMAIL')  # Securely load sender email
    sendgrid_api_key = os.getenv('SENDGRID_API_KEY')  # Securely load SendGrid API key

    if not sendgrid_api_key or not sender_email:
        st.error("SendGrid API key or sender email not set. Please set them as environment variables.")
        return

    subject = f'Stock Price Alert for {stock_name}'
    body = f'The stock price of {stock_name} has reached ₹{current_price}'

    message = Mail(
        from_email=sender_email,
        to_emails=to_email,
        subject=subject,
        plain_text_content=body)

    try:
        sg = SendGridAPIClient(sendgrid_api_key)
        response = sg.send(message)
        if response.status_code == 202:
            st.success("Email sent successfully!")
        else:
            st.error(f"Error sending email: {response.body}")
    except Exception as e:
        st.error(f"Error sending email: {e}")

# Add CSS for custom styling
st.markdown(
    """
    <style>
    .main {
        background-color: #d95c18;
        font-family: 'Arial', sans-serif;
    }

    .title {
        color: #f6ff00;
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        padding: 10px 0;
    }

    .box {
        background-color: white;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
    }

    .button {
        background-color: #4CAF50;
        color: white;
        font-size: 1.2rem;
        border-radius: 10px;
        width: 100%;
        padding: 10px;
        border: none;
    }

    .stButton button:hover {
        background-color: #45a049;
    }

    .stTextInput, .stNumberInput {
        border-radius: 5px;
    }
    </style>
    """, unsafe_allow_html=True
)

# Stock ticker options
stock_tickers = ['', 'TATASTEEL', 'RELIANCE', 'INFY', 'HDFCBANK', 'BAJFINANCE', 'TCS', 'ITC', 'HINDUNILVR']

# Streamlit User Inputs
st.markdown("<h1 class='title'>📈 Stock Price Notifier</h1>", unsafe_allow_html=True)

# Create a box for input fields
st.markdown("<div class='box'>", unsafe_allow_html=True)

# Select exchange (NSE/BSE)
exchange = 'NSE'

# Stock ticker input with a placeholder at the top
ticker = st.selectbox('Enter stock ticker or type:', stock_tickers, index=0)

# Show a warning if no stock ticker is selected
if ticker == '':
    st.warning('Please select a valid stock ticker.')

# Close the box for inputs
st.markdown("</div>", unsafe_allow_html=True)

# Initialize session state variables if not already set
if 'target_price' not in st.session_state:
    st.session_state.target_price = 0.0

if 'email' not in st.session_state:
    st.session_state.email = ''

# Define time periods for the dynamic graph
time_ranges = {
    "1 Day": "1d",
    "5 Days": "5d",
    "1 Month": "1mo",
    "6 Months": "6mo",
    "1 Year": "1y",
    "5 Years": "5y"
}

# Select time range
time_period = st.selectbox("Select Time Period", list(time_ranges.keys()))

# Function to scrape live stock price from Google Finance
def fetch_google_finance_price(ticker, exchange):
    try:
        url = f'https://www.google.com/finance/quote/{ticker}:{exchange}'
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        price_class = "YMlKec fxKbKc"
        price = soup.find(class_=price_class).text.strip()[1:].replace(",", "")
        return float(price)
    except Exception as e:
        st.error(f"Error fetching stock price from Google Finance: {e}")
        return None

# Function to fetch historical stock data from Yahoo Finance
def fetch_historical_data(ticker, period):
    stock_data = yf.Ticker(f"{ticker}.NS")  # `.NS` is for NSE; use `.BO` for BSE
    return stock_data.history(period=period)  # Fetch the data for the selected period

# Button to fetch current stock price and display stock price graph
if st.button('Fetch Current Price and Show Graph') and ticker != '':
    st.markdown(f"<h2>📊 Stock Price Chart ({time_period})</h2>", unsafe_allow_html=True)
    
    # Fetch live price from Google Finance
    live_price = fetch_google_finance_price(ticker, exchange)
    
    # Display live stock price
    if live_price is not None:
        st.write(f"**Current price of {ticker}: ₹{live_price}**")
    else:
        st.error(f"Error fetching current stock price for {ticker}.")

    # Fetch historical data using Yahoo Finance
    stock_df = fetch_historical_data(ticker, time_ranges[time_period])
    
    # Create a Plotly graph
    fig = go.Figure()

    # Add trace for closing prices
    fig.add_trace(go.Scatter(x=stock_df.index, y=stock_df['Close'], mode='lines', name='Close Price'))

    # Set the layout
    fig.update_layout(
        title=f'Stock Price of {ticker} for {time_period}',
        xaxis_title='Date',
        yaxis_title='Price (₹)',
        template='plotly_white'
    )

    # Display the graph in Streamlit
    st.plotly_chart(fig)

# Option to monitor if price is higher or lower
monitor_type = st.radio("Monitor if price is:", ['Higher', 'Lower'])

# User inputs for target price and email
st.session_state.target_price = st.number_input('Set target price', min_value=0.0, value=st.session_state.target_price)
st.session_state.email = st.text_input('Enter your email for notifications', value=st.session_state.email)

# Button to start monitoring
if st.button('Start Monitoring') and ticker != '':
    if st.session_state.email:  # Check if email is provided
        placeholder = st.empty()  # Placeholder for dynamic updating

        while True:
            # Fetch live stock price from Google Finance
            live_price = fetch_google_finance_price(ticker, exchange)

            if live_price is not None:
                # Dynamically update the placeholder with the current price
                placeholder.write(f"Current price of {ticker}: ₹{live_price}")

                # Check if stock price has reached the target price based on user input (higher or lower)
                if monitor_type == 'Higher' and live_price >= st.session_state.target_price:
                    placeholder.write(f"Alert! {ticker} has exceeded ₹{st.session_state.target_price}")
                    send_email_notification(st.session_state.email, ticker, live_price)
                    break  # Stop monitoring after sending email
                elif monitor_type == 'Lower' and live_price <= st.session_state.target_price:
                    placeholder.write(f"Alert! {ticker} has dropped below ₹{st.session_state.target_price}")
                    send_email_notification(st.session_state.email, ticker, live_price)
                    break  # Stop monitoring after sending email
            else:
                placeholder.write("Error fetching stock price.")

            # Wait 5 seconds before checking again
            time.sleep(5)
    else:
        st.warning("Please enter a valid email address.")
else:
    if ticker == '':
        st.warning('Please select a valid stock ticker to start monitoring.')
    