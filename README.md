

## 🩺 AI-Driven Public Health Chatbot — *HealthBot*


### 👩‍💻 Developed By:

* **Renuka Bagade** 


**Department:** Computer Science and Business Systems
**Institute:** JSPM’s Rajarshi Shahu College of Engineering, Tathawade, Pune
**Academic Year:** 2025–26

---

## 🚀 Project Overview

**HealthBot** is an **AI-powered multilingual public health chatbot** designed to educate rural and semi-urban communities about:

* Preventive healthcare
* Disease symptoms and remedies
* Vaccination schedules
* Common health myths

The chatbot aims to combat misinformation and make verified health information **accessible, accurate, and available anytime** through popular communication platforms like WhatsApp, Telegram, and Web Chat.

---

## 🧠 Features

✅ **Multilingual Chat** — Supports English, Hindi, and Marathi (via `googletrans`)
✅ **Symptom-based Query Handling** — Detects user symptoms and suggests basic remedies
✅ **Myth-Busting Module** — Provides verified information to counter health rumors
✅ **Doctor Guidance & Precautions** — Informs users when to consult a healthcare professional
✅ **Scalable & Modular** — Built with Rasa 3.x for easy integration with APIs and health databases

---

## ⚙️ Tech Stack

| Component          | Technology Used                             |
| ------------------ | ------------------------------------------- |
| Framework          | **Rasa 3.6.2**                              |
| NLP Model          | DIETClassifier (Intent & Entity extraction) |
| Backend Language   | Python 3.10                                 |
| Deployment         | Hugging Face Spaces (Docker)                |
| Data Handling      | Pandas, Numpy                               |
| Translation        | Googletrans, Langdetect                     |
| Communication APIs | Twilio / Telegram (Future Integration)      |

---

## 🧩 Folder Structure

```
📦 HealthBot
├── actions/              # Custom Python actions
├── data/                 # Training data (nlu.yml, stories.yml, rules.yml)
├── models/               # Trained Rasa models (auto-generated)
├── config.yml            # NLP pipeline and policies
├── credentials.yml       # Channel connectors (Telegram, Twilio, etc.)
├── domain.yml            # Intents, entities, slots, responses
├── endpoints.yml         # Action server config
├── requirements.txt      # Dependencies
├── Dockerfile            # Docker build configuration
└── README.md             # Project documentation
```

---

## 🧰 How to Run Locally

If you want to test the bot on your local system:

### 1️⃣ Clone the repository

```bash
git clone https://huggingface.co/spaces/Renuka22Bagade/HealthBot
cd HealthBot
```

### 2️⃣ Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate   # (or venv\Scripts\activate on Windows)
```

### 3️⃣ Install dependencies

```bash
pip install -r requirements.txt
```

### 4️⃣ Train the chatbot

```bash
rasa train
```

### 5️⃣ Run the chatbot and action server

In **two terminals**:

```bash
rasa run actions
rasa shell
```

---

## 🌐 Deployment

This bot is deployed using **Hugging Face Spaces (Docker Runtime)**.
Dockerfile builds the Rasa environment, trains the model, and serves the chatbot API at port **5005**.

Access the live bot here:
👉 **[https://renuka22bagade-healthbot.hf.space](https://renuka22bagade-healthbot.hf.space)**

---

## 📊 Future Enhancements

* Integration with **Government Health APIs**
* **Voice-enabled interface** for accessibility
* **Telegram and WhatsApp** bot rollout
* **Analytics Dashboard** for tracking health query trends
* Integration with **PostgreSQL/Redis** for scalable deployment

---

## 📚 References

* [Rasa Open Source Docs](https://rasa.com/docs/)
* [WHO Health Alert Chatbot](https://www.who.int/news-room/feature-stories/detail/who-health-alert-bringing-covid-19-facts-to-billions-via-whatsapp)
* [Twilio WhatsApp API](https://www.twilio.com/whatsapp)
* [Hugging Face Spaces](https://huggingface.co/spaces)

---

## 💬 Quote

> “Let’s fight misinformation with AI-powered awareness — for healthier, safer communities.” 🌍



