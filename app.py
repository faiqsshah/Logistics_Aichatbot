import os
import time
import logging
from datetime import datetime
import streamlit as st
import requests
from dotenv import load_dotenv
from typing import List, Dict, Optional

# Set up logging
logging.basicConfig(level=logging.INFO)

# Constants for API URLs
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
SHIPPO_API_URL = "https://api.goshippo.com/shipments/"
SHIPPO_TRACK_URL = "https://api.goshippo.com/tracks/{carrier}/{tracking_number}/"

# Set page config at the very beginning
st.set_page_config(page_title="Logistics AI Assistant", page_icon="🚚", layout="wide")

# Load environment variables
load_dotenv()
SHIPPO_API_KEY = os.getenv("SHIPPO_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Initialize chat history in session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

def format_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_greeting() -> str:
    current_hour = datetime.now().hour
    if current_hour < 12:
        return "Good morning! How can I assist you with your logistics needs today?"
    elif current_hour < 18:
        return "Good afternoon! What logistics questions can I help you with?"
    else:
        return "Good evening! How may I assist you with your shipping and logistics inquiries?"

def get_enhanced_chatbot_response(user_input: str, chat_history: List[Dict[str, str]]) -> Optional[str]:
    if not GROQ_API_KEY:
        return get_fallback_response(user_input)

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    messages = [
        {
            "role": "system",
            "content": "You are an expert AI assistant specializing in logistics, shipping, trucking, and freight forwarding. Provide accurate, helpful, and concise information to user queries. Always maintain a friendly and professional tone."
        },
    ] + [{"role": chat["role"], "content": chat["content"]} for chat in chat_history[-5:]] + [{"role": "user", "content": user_input}]
    
    payload = {
        "model": "mixtral-8x7b-32768",
        "messages": messages,
        "max_tokens": 500,
        "temperature": 0.7
    }
    
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        logging.error(f"API Error: {str(e)}")
        return get_fallback_response(user_input)

def get_fallback_response(user_input: str) -> str:
    logistics_topics = {
        "shipping rates": "Shipping rates vary depending on factors such as package weight, dimensions, destination, and service level. For accurate rates, please use our Shipping Rates Calculator tool in the Tools section.",
        "track shipment": "To track a shipment, you'll need the tracking number and carrier information. Please use our Shipment Tracker tool in the Tools section for real-time tracking updates.",
        "trucking": "Trucking is a crucial part of logistics, involving the transportation of goods by road. It includes various types of services such as full truckload (FTL), less than truckload (LTL), and specialized freight.",
        "freight forwarding": "Freight forwarding involves organizing shipments from the manufacturer or producer to the final point of distribution or consumer.",
        "customs": "Customs procedures are essential for international shipping. They involve declaring goods, paying duties and taxes, and complying with import/export regulations.",
        "packaging": "Proper packaging is crucial for protecting your items during shipping. Use appropriate materials like bubble wrap, packing peanuts, or air pillows.",
        "insurance": "Shipping insurance provides protection against loss, damage, or theft of your packages.",
        "international shipping": "International shipping involves additional considerations such as customs documentation, duties and taxes, restricted items, and longer transit times.",
        "warehousing": "Warehousing is the storage of goods before they are shipped to customers.",
        "last-mile delivery": "Last-mile delivery refers to the final step of the delivery process from a distribution center to the end customer.",
    }

    for topic, response in logistics_topics.items():
        if topic in user_input.lower():
            return response

    return "I'm here to help with all your logistics needs, including shipping, trucking, and freight forwarding. Could you please provide more specific information about what you'd like to know? Feel free to ask about topics such as shipping rates, tracking, customs, packaging, insurance, or any other logistics-related questions."

def get_shipping_rates(origin, destination, weight, length, width, height):

    url = "https://api.goshippo.com/shipments/"
    headers = {"Authorization": f"ShippoToken {SHIPPO_API_KEY}"}

    payload = {
        "address_from": origin,
        "address_to": destination,
        "parcels": [
            {
                "length": str(length),
                "width": str(width),
                "height": str(height),
                "distance_unit": "in",
                "weight": str(weight),
                "mass_unit": "lb"
            }
        ],
        "async": False
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        
        if "rates" in data and data["rates"]:
            rates_info = []
            for rate in data["rates"][:5]:  # Display top 5 rates
                rates_info.append(f"{rate['provider']} - ${rate['amount']} ({rate['duration_terms']})")
            return "Available shipping rates:\n" + "\n".join(rates_info)
        else:
            return "No rates found for the given shipment details. Please check your input and try again."
    except requests.exceptions.RequestException as e:
        print(f"Shippo API Error: {str(e)}")
        return "An error occurred while fetching shipping rates. Please try again later or contact support."

def track_shipment(tracking_number, carrier):
    if not SHIPPO_API_KEY:
        return "Shipment tracking is currently unavailable. Please try again later or contact support."

    url = f"https://api.goshippo.com/tracks/{carrier}/{tracking_number}/"
    headers = {"Authorization": f"ShippoToken {SHIPPO_API_KEY}"}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        tracking_info = response.json()
        
        status = tracking_info['tracking_status']['status']
        location = tracking_info['tracking_status']['location']['city']
        country = tracking_info['tracking_status']['location']['country']
        eta = tracking_info['eta'] if 'eta' in tracking_info else 'Not available'
        
        return f"Tracking Status: {status}\nCurrent Location: {location}, {country}\nEstimated Delivery: {eta}"
    except requests.exceptions.RequestException as e:
        print(f"Shippo API Error: {str(e)}")
        return "An error occurred while tracking the shipment. Please try again later or contact support."

def get_chatbot_response(user_input):
    response_timestamp = format_timestamp()
    response = get_enhanced_chatbot_response(user_input, st.session_state.chat_history)
    
    return f"🤖 {response} (sent at {response_timestamp})"

# Main application
st.title("🚚 Logistics AI Assistant")
st.markdown("<h3>Your Intelligent Shipping and Logistics Partner</h3>", unsafe_allow_html=True)

st.sidebar.header("Navigation")
page = st.sidebar.radio("Go to", ["Home", "Tools", "Contact"])

if page == "Home":
    st.header("Welcome to Your Logistics Command Center")
    st.markdown(f"<h4>{get_greeting()}</h4>", unsafe_allow_html=True)

    st.subheader("Chat with Our AI Logistics Expert")
    
    for chat in st.session_state.chat_history:
        if chat["role"] == "user":
            st.markdown(f'<div style="background-color:#E6F3FF; border-radius:10px; padding:10px; margin:5px;"><strong>You:</strong> {chat["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="background-color:#F0F0F0; border-radius:10px; padding:10px; margin:5px;"><strong>AI:</strong> {chat["content"]}</div>', unsafe_allow_html=True)
    
    user_input = st.text_input("Ask me anything about shipping, logistics, or freight:", key="user_input")

    if st.button("Send", key="send_button"):
        if user_input:
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            bot_response = get_chatbot_response(user_input)
            st.session_state.chat_history.append({"role": "assistant", "content": bot_response})
            st.rerun()

    if st.button("Clear Chat History", key="clear_chat"):
        st.session_state.chat_history = []
        st.rerun()

elif page == "Tools":
    st.header("Logistics Tools")
    
    tool_choice = st.selectbox("Select a tool:", ["Shipping Rates Calculator", "Shipment Tracker", "Trucking Information", "Freight Forwarding Guide"])
    
    if tool_choice == "Shipping Rates Calculator":
        st.subheader("Calculate Shipping Rates")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Origin")
            origin = {
                "name": st.text_input("Sender Name", key="sender_name"),
                "street1": st.text_input("Street Address", key="sender_street"),
                "city": st.text_input("City", key="sender_city"),
                "state": st.text_input("State", key="sender_state"),
                "zip": st.text_input("ZIP Code", key="sender_zip"),
                "country": "US"
            }

        with col2:
            st.markdown("### Destination")
            destination = {
                "name": st.text_input("Recipient Name", key="recipient_name"),
                "street1": st.text_input("Street Address", key="recipient_street"),
                "city": st.text_input("City", key="recipient_city"),
                "state": st.text_input("State", key="recipient_state"),
                "zip": st.text_input("ZIP Code", key="recipient_zip"),
                "country": "US"
            }

        st.markdown("### Package Details")
        col3, col4, col5, col6 = st.columns(4)
        with col3:
            weight = st.number_input("Weight (lbs)", min_value=0.1, value=1.0, step=0.1)
        with col4:
            length = st.number_input("Length (in)", min_value=1.0, value=10.0, step=0.1)
        with col5:
            width = st.number_input("Width (in)", min_value=1.0, value=10.0, step=0.1)
        with col6:
            height = st.number_input("Height (in)", min_value=1.0, value=10.0, step=0.1)

        if st.button("Calculate Shipping Rates"):
            with st.spinner("Calculating rates..."):
                rates = get_shipping_rates(origin, destination, weight, length, width, height)
                st.success(rates)

    elif tool_choice == "Shipment Tracker":
        st.subheader("Track Your Shipment")
        tracking_number = st.text_input("Enter Tracking Number:")
        carrier = st.selectbox("Select Carrier:", ["usps", "fedex", "ups"])

        if st.button("Track Shipment"):
            with st.spinner("Tracking shipment..."):
                tracking_info = track_shipment(tracking_number, carrier)
                st.info(tracking_info)

    elif tool_choice == "Trucking Information":
        st.subheader("Trucking Information")
        trucking_query = st.text_input("What would you like to know about trucking?")
        if st.button("Get Trucking Info"):
            with st.spinner("Fetching information..."):
                info = get_enhanced_chatbot_response(f"Provide information about {trucking_query} in the context of trucking and transportation.", [])
                st.write(info)

    elif tool_choice == "Freight Forwarding Guide":
        st.subheader("Freight Forwarding Guide")
        freight_query = st.text_input("What aspect of freight forwarding would you like to learn about?")
        if st.button("Get Freight Forwarding Info"):
            with st.spinner("Fetching information..."):
                info = get_enhanced_chatbot_response(f"Provide information about {freight_query} in the context of freight forwarding.", [])
                st.write(info)

elif page == "Contact":
    st.header("Contact Us")
    st.markdown("""
    We're here to help with all your logistics needs. Reach out to us through any of the following channels:

    📧 **Email:** [support@logisticsai.com](mailto:support@logisticsai.com)
    
    📞 **Phone:** +1 (800) 123-4567
    
    🌐 **Website:** [www.logisticsai.com](https://www.logisticsai.com)
    
    🏢 **Office Address:**  
    Logistics AI Headquarters  
    123 Shipping Lane  
    Freightville, LG 12345  
    United States

    Our customer support team is available 24/7 to assist you with any questions or concerns.
    """)

    st.markdown("### Send us a message")
    contact_name = st.text_input("Your Name")
    contact_email = st.text_input("Your Email")
    contact_message = st.text_area("Your Message")
    if st.button("Send Message"):
        st.success("Thank you for your message. We'll get back to you shortly!")

if __name__ == "__main__":
    st.sidebar.markdown("---")
    st.sidebar.markdown("© 2023 Logistics AI Assistant")