import requests
import gradio as gr

API_URL = "http://localhost:5005/webhooks/rest/webhook"

def chat_with_bot(message, sender="Renuka"):
    if not message:
        return "Please type a message."
    payload = {"sender": sender, "message": message}
    response = requests.post(API_URL, json=payload)
    if response.status_code == 200:
        data = response.json()
        if data:
            return " ".join([m.get("text", "") for m in data])
        else:
            return "🤖 (No reply)"
    else:
        return f"Error: {response.status_code}"

with gr.Blocks(title="AI Health Chatbot") as demo:
    gr.Markdown("## 🩺 AI Health Chatbot\nTalk to your assistant about health and wellness tips.")
    chatbox = gr.ChatInterface(fn=chat_with_bot, title="AI Health Chatbot")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7860, debug=False)