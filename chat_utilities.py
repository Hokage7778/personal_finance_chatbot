# chat_utilities.py

import os
import logging
import requests
from config import API_KEY, MODEL_NAME, MAX_TOKENS, TEMPERATURE, TOP_P

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def sanitize_input(user_input):
    """Sanitize user input to prevent potential security issues."""
    if not user_input:
        return ""

    # Remove any HTML tags
    user_input = user_input.replace("<", "&lt;").replace(">", "&gt;")

    # Remove any script tags
    user_input = user_input.replace("script", "")

    # Limit input length
    max_length = 500
    if len(user_input) > max_length:
        user_input = user_input[:max_length]

    # Remove any system prompt injection attempts
    forbidden_terms = ["<|im_start|>", "<|im_end|>", "system", "assistant"]
    for term in forbidden_terms:
        user_input = user_input.replace(term, "")

    return user_input.strip()

def format_conversation(user_input):
    """Format the conversation for the model."""
    system_prompt = """You are an experienced personal finance advisor with expertise in Indian financial markets,
taxation, and investment products. Your role is to provide clear, practical, and personalized financial advice
tailored to the Indian context. Please follow these guidelines:

1. Only answer questions related to personal finance, investing, and money management in the Indian context
2. If asked about non-financial topics, politely redirect the conversation to financial matters
3. Provide specific, actionable advice while acknowledging that you're not providing official financial recommendations
4. Use clear, simple language to explain complex financial concepts
5. Always encourage responsible financial behavior and long-term planning
6. When discussing investments, focus on Indian investment options such as:
   - Mutual Funds and SIPs
   - Fixed Deposits and Recurring Deposits
   - Public Provident Fund (PPF)
   - National Pension System (NPS)
   - Employee Provident Fund (EPF)
   - Stock market investments through Indian exchanges (NSE/BSE)
   - Government schemes like Sukanya Samriddhi Yojana
   - Tax-saving instruments under Section 80C

7. Include relevant Indian tax considerations:
   - Income Tax slabs and regulations
   - Tax-saving investments under Section 80C
   - Capital Gains Tax implications
   - GST considerations where applicable

8. Consider Indian-specific financial aspects:
   - Rupee-based calculations and examples
   - Indian inflation rates and market conditions
   - RBI policies and banking regulations
   - Local insurance products (Term, Health, Life)
   - Real estate investments in Indian markets

9. Reference relevant Indian financial institutions and regulators:
   - SEBI (Securities and Exchange Board of India)
   - RBI (Reserve Bank of India)
   - IRDAI (Insurance Regulatory and Development Authority of India)
   - PFRDA (Pension Fund Regulatory and Development Authority)

10. Provide guidance on:
    - UPI and digital payment systems in India
    - Indian banking products and services
    - Credit scores (CIBIL) and loan products
    - Emergency fund planning for Indian context
    - Retirement planning considering Indian social security system

Remember: You are not a licensed financial advisor and should encourage users to consult with
qualified professionals registered with SEBI, RBI, or appropriate Indian regulatory bodies for
specific investment or legal advice.

Disclaimer: All advice should be considered within the framework of Indian financial regulations
and tax laws, which may change over time. Users should verify current rules and regulations
with appropriate authorities or consult certified financial advisors in India."""

    return f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{user_input}<|im_end|>\n<|im_start|>assistant"

def clean_response(response):
    """Clean and format the model's response."""
    try:
        # Remove any system or user prompts
        response = response.replace("<|im_start|>", "").replace("<|im_end|>", "")
        response = response.replace("system", "").replace("user", "").replace("assistant", "")

        # Handle bold text (remove asterisks)
        response = response.replace("**", "")

        # Convert numbered lists and bullet points to proper formatting
        lines = response.split('\n')
        formatted_lines = []

        for line in lines:
            line = line.strip()
            # Skip empty lines
            if not line:
                continue

            # Handle numbered items (e.g., "1.", "2.", etc.)
            if any(line.startswith(f"{i}.") for i in range(1, 10)):
                formatted_lines.append(f"\n{line}")
            # Handle bullet points
            elif line.startswith('-'):
                formatted_lines.append(f"• {line[1:].strip()}")
            # Handle section headers (typically followed by colon)
            elif ':' in line and len(line) < 50:
                # Remove any remaining asterisks
                clean_line = line.replace('*', '')
                formatted_lines.append(f"\n💡 {clean_line}\n")
            else:
                # Remove any remaining asterisks
                clean_line = line.replace('*', '')
                formatted_lines.append(clean_line)

        # Join lines and clean up extra whitespace
        response = '\n'.join(formatted_lines)

        # Format specific keywords with emojis
        keywords = {
            'Current Income': '💰 Current Income',
            'Expenses': '💳 Expenses',
            'Savings': '🏦 Savings',
            'Investments': '📈 Investments',
            'Debts': '📊 Debts',
            'Financial Goals': '🎯 Financial Goals',
            'Risk Tolerance': '⚖️ Risk Tolerance',
            'Time Horizon': '⏳ Time Horizon',
            'Monthly Income': '💵 Monthly Income',
            'Budget': '📒 Budget',
            'Mutual Funds': '📊 Mutual Funds',
            'SIP': '📈 SIP',
            'PPF': '🏦 PPF',
            'NPS': '🔒 NPS',
            'EPF': '💼 EPF',
            'Tax Saving': '💸 Tax Saving',
            'Insurance': '🛡️ Insurance',
            'UPI': '📱 UPI',
            'Credit Score': '📊 Credit Score',
            'Real Estate': '🏠 Real Estate'
        }

        for key, value in keywords.items():
            response = response.replace(key, value)

        # Add proper spacing and formatting
        response = response.replace(':.', ':')  # Remove unnecessary periods after colons
        response = response.replace('?:', '?')  # Clean up question marks followed by colons

        # Ensure proper spacing after punctuation
        response = response.replace('.', '. ')
        response = response.replace('  ', ' ')

        # Add line breaks after questions
        response = response.replace('? ', '?\n')

        # Clean up any multiple line breaks
        while '\n\n\n' in response:
            response = response.replace('\n\n\n', '\n\n')

        # Add disclaimer if not present
        disclaimer = "\n\n⚠️ Disclaimer: This is AI-generated advice. Please consult with qualified financial advisors registered with SEBI/RBI for professional guidance."
        if "disclaimer" not in response.lower():
            response += disclaimer

        # Ensure the response starts with a capital letter
        if response and len(response) > 0:
            response = response[0].upper() + response[1:]

        return response.strip()

    except Exception as e:
        logger.error(f"Error in clean_response: {str(e)}")
        return response.strip()  # Return original response if formatting fails

def generate_chat_response(user_input):
    """Generate response using Hugging Face API."""
    API_URL = f"https://api-inference.huggingface.co/models/{MODEL_NAME}"
    headers = {"Authorization": f"Bearer {API_KEY}"}

    try:
        # Sanitize the input first
        sanitized_input = sanitize_input(user_input)
        formatted_input = format_conversation(sanitized_input)

        payload = {
            "inputs": formatted_input,
            "parameters": {
                "max_new_tokens": MAX_TOKENS,
                "temperature": TEMPERATURE,
                "top_p": TOP_P,
                "return_full_text": False,
                "do_sample": True,
                "num_return_sequences": 1,
                "stop": ["<|im_end|>"]
            }
        }

        logger.info(f"Sending request to Hugging Face API: {API_URL}")
        response = requests.post(API_URL, headers=headers, json=payload)

        response.raise_for_status()
        response_data = response.json()

        if isinstance(response_data, list) and len(response_data) > 0:
            generated_text = response_data[0].get('generated_text', '')
            formatted_response = clean_response(generated_text)
            return formatted_response
        else:
            logger.error(f"Unexpected response format: {response_data}")
            return "I apologize, but I encountered an error processing your request."

    except requests.exceptions.RequestException as e:
        logger.error(f"API request error: {str(e)}")
        return f"I apologize, but I'm having trouble connecting to the server. Please try again later."
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return "I apologize, but something went wrong. Please try again."
