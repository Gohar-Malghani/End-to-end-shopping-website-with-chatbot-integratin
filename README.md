# 🛍️ E-Commerce Shopping Website with AI Customer Service Chatbot

A full-stack e-commerce shopping website designed to provide customers with a smooth online shopping experience. The project also includes an AI-powered customer service chatbot to help users with shopping-related questions and customer support.

## 🚀 Project Overview

This project combines an online shopping platform with an AI customer service assistant. Customers can explore products, interact with the shopping website, and get assistance from the chatbot for customer service-related queries.

## ✨ Features

### 🛒 E-Commerce Website
- Online shopping interface
- Product browsing and product details
- Shopping cart functionality
- Customer account and authentication system
- Order management and checkout flow
- Responsive user interface

### 🤖 AI Customer Service Chatbot
- Answers customer service-related questions
- Helps with order and delivery inquiries
- Provides guidance about returns and refunds
- Assists with payment-related questions
- Handles customer support queries
- Uses a dedicated customer service prompt to keep responses focused on relevant topics

*Note: Features should be adjusted to match the functionality actually implemented in the project.*

## 🛠️ Tech Stack

- **Backend:** Django
- **Programming Language:** Python
- **AI Framework:** LangChain
- **LLM Runtime:** Ollama
- **Frontend:** HTML, CSS, JavaScript and Bootstrap (if used)
- **Database:** SQLite or the database configured in the project
- **Version Control:** Git and GitHub

## ⚙️ Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
cd YOUR-REPOSITORY
```

Replace the repository URL with your actual GitHub repository URL.

### 2. Create a Virtual Environment

```bash
python -m venv .venv
```

### 3. Activate the Virtual Environment

For Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 4. Install Dependencies

If the project contains a `requirements.txt` file:

```bash
pip install -r requirements.txt
```

### 5. Set Up Ollama

Install Ollama if it is required by the chatbot, then download the model configured in your project.

For example, if your code uses `llama3.2:1b`:

```bash
ollama pull llama3.2:1b
```

Make sure Ollama is running before testing the chatbot.

### 6. Apply Database Migrations

```bash
python manage.py migrate
```

### 7. Run the Development Server

```bash
python manage.py runserver
```

Open the website in your browser:

http://127.0.0.1:8000/

## 📁 Project Structure

```text
YOUR-REPOSITORY/
├── manage.py
├── requirements.txt
├── README.md
├── config/
├── chat/
├── templates/
└── static/
```

*The structure above is an example. Update it according to your actual project folders.*

## 🔒 Security Notes

- Never commit passwords, API keys, or `.env` files.
- Keep virtual environments and unnecessary generated files out of Git.
- Use Django's security features and validate user input.
- Configure production security settings before deployment.

## 🎯 Project Goals

- Build a complete end-to-end online shopping experience.
- Integrate an AI-based customer service assistant.
- Practice Django backend development and AI integration.
- Improve the customer support experience through conversational AI.

## 👨‍💻 Author

**Gohar Malghani**

GitHub: https://github.com/Gohar-Malghani

## 📄 License

Add a suitable open-source license if you intend to distribute this project under one.
