import os
import requests
from typing import Any, Text, Dict, List, Optional
from datetime import datetime
from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict
from rasa_sdk.events import SlotSet, AllSlotsReset
import re

# Optional: OpenAI for advanced queries
try:
    import openai
    openai.api_key = os.getenv("OPENAI_API_KEY")
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None

# ========================================
# API HELPER FUNCTIONS
# ========================================

def search_health_info(query: str) -> Optional[str]:
    """
    Search health information using multiple reliable sources
    Priority: MedlinePlus (NIH) > Disease Stats > Manual Fallback
    """
    try:
        query = query.strip().lower()
        
        # Clean query
        query = re.sub(r'^(what is|tell me about|tell about|info about|information on|i have|my)\s+', '', query, flags=re.IGNORECASE)
        query = re.sub(r'\s+(info|information|symptoms|symptom)$', '', query, flags=re.IGNORECASE)
        query = ' '.join(query.split()).strip()
        
        if len(query) < 3:
            return None
        
        print(f"[DEBUG] Searching health info for: '{query}'")
        
        # ===============================
        # METHOD 1: MedlinePlus NIH API
        # ===============================
        try:
            # MedlinePlus Health Topics API (Free, Reliable)
            url = "https://connect.medlineplus.gov/service"
            params = {
                'mainSearchCriteria.v.c': query,
                'informationRecipient.languageCode.c': 'en',
                'knowledgeResponseType': 'application/json'
            }
            
            headers = {'User-Agent': 'HealthBot/1.0'}
            response = requests.get(url, params=params, timeout=10, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                feed = data.get('feed', {})
                entries = feed.get('entry', [])
                
                if entries:
                    entry = entries[0]
                    
                    # Extract information
                    title_obj = entry.get('title', {})
                    title = title_obj.get('_value', '') if isinstance(title_obj, dict) else str(title_obj)
                    
                    summary_obj = entry.get('summary', {})
                    summary = summary_obj.get('_value', '') if isinstance(summary_obj, dict) else str(summary_obj)
                    
                    # Get URL
                    link = ''
                    links = entry.get('link', [])
                    if isinstance(links, list):
                        for l in links:
                            if isinstance(l, dict) and l.get('rel') == 'alternate':
                                link = l.get('href', '')
                                break
                    
                    if title and summary and len(summary) > 80:
                        # Limit summary to 500 chars
                        if len(summary) > 500:
                            summary = summary[:500] + "..."
                        
                        return f"""📚 **{title}**

{summary}

⚠️ **Source: MedlinePlus (U.S. National Library of Medicine)**
This is general health information. Not a substitute for professional medical advice.

📞 For diagnosis: Consult doctor or call 1075
🏥 Visit nearest PHC/Government hospital

🔗 Read more: {link if link else 'https://medlineplus.gov'}"""
            
            print(f"[DEBUG] MedlinePlus returned status: {response.status_code}")
        
        except Exception as e:
            print(f"[DEBUG] MedlinePlus API error: {e}")
        
        # ===============================
        # METHOD 2: Disease.sh for COVID
        # ===============================
        if 'covid' in query or 'coronavirus' in query:
            try:
                url = "https://disease.sh/v3/covid-19/countries/india"
                response = requests.get(url, timeout=8)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    return f"""📊 **COVID-19 Statistics - India**

**Current Status:**
• Total Cases: {data.get('cases', 'N/A'):,}
• Active Cases: {data.get('active', 'N/A'):,}
• Recovered: {data.get('recovered', 'N/A'):,}
• Deaths: {data.get('deaths', 'N/A'):,}
• Today's Cases: {data.get('todayCases', 'N/A'):,}

**Resources:**
📱 CoWIN: cowin.gov.in
📞 COVID Helpline: 1800-11-4377
🏥 Free testing at Government hospitals
⚠️ Follow COVID-appropriate behavior"""
            
            except Exception as e:
                print(f"[DEBUG] COVID stats error: {e}")
        
        # ===============================
        # FINAL FALLBACK
        # ===============================
        return None
        
    except Exception as e:
        print(f"[ERROR] Health info search failed: {e}")
        import traceback
        traceback.print_exc()
        return None


# ========================================
# CONFIGURATION
# ========================================
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "YOUR_NEWS_API_KEY_HERE")

# Multilingual support (Hindi, Marathi, English)
LANGUAGES = {
    'en': 'English',
    'hi': 'Hindi',
    'mr': 'Marathi'
}

GREETINGS = {
    'en': "Hello! 🙏 I'm your health awareness assistant. How can I help you today?",
    'hi': "नमस्ते! 🙏 मैं आपका स्वास्थ्य जागरूकता सहायक हूं। आज मैं आपकी कैसे मदद कर सकता हूं?",
    'mr': "नमस्कार! 🙏 मी तुमचा आरोग्य जागरूकता सहाय्यक आहे. आज मी तुम्हाला कशी मदत करू शकतो?"
}

# ========================================
# MULTILINGUAL SUPPORT
# ========================================
class ActionSetLanguage(Action):
    def name(self) -> Text:
        return "action_set_language"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        
        message = tracker.latest_message.get('text', '').lower()
        
        # Detect language
        if any(word in message for word in ['hindi', 'हिंदी', 'हिन्दी']):
            language = 'hi'
        elif any(word in message for word in ['marathi', 'मराठी']):
            language = 'mr'
        else:
            language = 'en'
        
        dispatcher.utter_message(text=GREETINGS[language])
        
        return [SlotSet("language", language)]


# ========================================
# VACCINATION SCHEDULE
# ========================================
class ActionVaccinationSchedule(Action):
    def name(self) -> Text:
        return "action_vaccination_schedule"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        
        message = tracker.latest_message.get('text', '').lower()
        schedule = self._get_vaccination_schedule(message)
        dispatcher.utter_message(text=schedule)
        return []
    
    def _get_vaccination_schedule(self, message):
        """Government of India Vaccination Schedule"""
        
        if any(word in message for word in ['infant', 'baby', 'newborn', 'child']):
            return """💉 **Infant/Child Vaccination Schedule (Government of India):**

**At Birth:**
• BCG (Tuberculosis)
• Hepatitis B (Birth dose)
• OPV 0 (Polio)

**6 Weeks:**
• OPV 1, Pentavalent 1, PCV 1, Rotavirus 1

**10 Weeks:**
• OPV 2, Pentavalent 2, PCV 2, Rotavirus 2

**14 Weeks:**
• OPV 3, Pentavalent 3, PCV 3, Rotavirus 3, IPV 1

**9-12 Months:**
• Measles & Rubella (MR 1), PCV Booster, JE 1

**16-24 Months:**
• MR 2, JE 2, DPT Booster 1, OPV Booster

**5-6 Years:**
• DPT Booster 2

**10 Years:**
• Tetanus & adult Diphtheria (Td)

**16 Years:**
• Td

📍 Visit nearest Government Health Center for FREE vaccination
🏥 Call 1075 (National Immunization Helpline)"""

        elif any(word in message for word in ['adult', 'grown', 'elder', 'senior']):
            return """💉 **Adult Vaccination Schedule:**

**Annually:**
• Flu vaccine (Seasonal Influenza)

**Every 10 Years:**
• Tetanus-Diphtheria (Td) booster

**Age 50+:**
• Pneumococcal vaccine

**Age 60+:**
• Pneumococcal booster
• Zoster vaccine (Shingles)

**For Women:**
• HPV vaccine (up to age 26)
• Td during each pregnancy

**COVID-19:**
• As per government guidelines
• Booster doses as recommended

📍 Available at Government hospitals and Primary Health Centers
💰 Many vaccines available FREE under government schemes"""

        elif 'covid' in message:
            return """💉 **COVID-19 Vaccination:**

**Eligibility:** All adults 18+

**Schedule:**
• Dose 1: First dose
• Dose 2: 12-16 weeks after Dose 1
• Precaution Dose: 9 months after Dose 2

**Vaccines Available:**
• Covaxin
• Covishield
• Corbevax
• Others as approved

📱 Register on: CoWIN Portal or Aarogya Setu App
📍 Visit nearest vaccination center
🆓 FREE for all citizens

⚠️ Get vaccinated to protect yourself and others!"""

        else:
            return """💉 **Vaccination Information:**

Which age group are you asking about?
• Infant/Child vaccination
• Adult vaccination
• COVID-19 vaccination

Reply with the category for detailed schedule.

📞 For queries, call National Immunization Helpline: 1075"""


# ========================================
# GOVERNMENT HEALTH DATABASE INTEGRATION
# ========================================
class ActionFetchGovernmentData(Action):
    def name(self) -> Text:
        return "action_fetch_government_data"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        
        try:
            message = "🇮🇳 **Government of India Health Data:**\n\n"
            
            # COVID-19 Data for India
            response = requests.get(
                "https://disease.sh/v3/covid-19/countries/india",
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                message += "📊 **COVID-19 Statistics (India):**\n"
                message += f"• Total Cases: {data.get('cases', 'N/A'):,}\n"
                message += f"• Active Cases: {data.get('active', 'N/A'):,}\n"
                message += f"• Recovered: {data.get('recovered', 'N/A'):,}\n"
                message += f"• Deaths: {data.get('deaths', 'N/A'):,}\n"
                message += f"• Today's Cases: {data.get('todayCases', 'N/A'):,}\n\n"
            
            message += """📱 **Government Health Resources:**

**Emergency Numbers:**
• National Health Helpline: 1075
• Ambulance: 102 / 108
• Women Helpline: 1091
• Child Helpline: 1098

**Useful Portals:**
• Ayushman Bharat: pmjay.gov.in
• CoWIN: cowin.gov.in
• Aarogya Setu App
• e-Sanjeevani Telemedicine

**Government Schemes:**
• Ayushman Bharat - PM-JAY
• Pradhan Mantri Surakshit Matritva Abhiyan
• Mission Indradhanush
• National Health Mission

📍 Find nearest Government Hospital/PHC:
Visit: nhp.gov.in"""
            
            dispatcher.utter_message(text=message)
            
        except Exception as e:
            dispatcher.utter_message(
                text="Unable to fetch data. Please try:\n"
                     "📞 National Health Helpline: 1075\n"
                     "🌐 Visit: mohfw.gov.in"
            )
            print(f"Error: {e}")
        
        return []


# ========================================
# ENHANCED SYMPTOM CHECKER
# ========================================
class ActionSymptomChecker(Action):
    def name(self) -> Text:
        return "action_symptom_checker"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        
        message = tracker.latest_message.get('text', '').lower()
        
        # If user is just asking about a disease (not reporting symptoms), redirect
        if any(phrase in message for phrase in ['what is', 'tell me about', 'info about', 'information on']):
        # Call disease info action instead
           action = ActionAnswerHealthQuestion()
        return action.run(dispatcher, tracker, domain)
        # Extract multiple symptoms
        symptoms = self._extract_multiple_symptoms(message)
        
     
        
        # Analyze symptoms
        analysis = self._analyze_symptoms(symptoms)
        
        message_text = f"🩺 **Symptom Analysis:**\n\n"
        message_text += f"Symptoms detected: {', '.join(symptoms)}\n\n"
        message_text += f"**Possible Conditions:**\n{analysis}\n\n"
        message_text += "⚠️ **Disclaimer:** This is NOT a diagnosis. Consult a doctor.\n"
        message_text += "📞 Helpline: 1075 | Emergency: 102/108"
        
        dispatcher.utter_message(text=message_text)
        
        return []
    
    def _extract_multiple_symptoms(self, message):
        """Extract all symptoms from message"""
        symptom_keywords = {
            'fever': ['fever', 'temperature', 'feverish'],
            'cough': ['cough', 'coughing'],
            'headache': ['headache', 'head pain', 'migraine'],
            'body ache': ['body ache', 'body pain', 'muscle pain'],
            'fatigue': ['tired', 'fatigue', 'weakness', 'weak'],
            'sore throat': ['sore throat', 'throat pain'],
            'nausea': ['nausea', 'vomiting'],
            'breathlessness': ['breathless', 'breathing problem', 'shortness of breath'],
            'chest pain': ['chest pain'],
            'stomach pain': ['stomach pain', 'stomach ache', 'abdominal pain'],
            'diarrhea': ['diarrhea', 'loose motion'],
            'rash': ['rash', 'skin rash'],
            'leg pain': ['leg pain', 'leg hurt'],
            'joint pain': ['joint pain', 'knee pain'],
        }
        
        found_symptoms = []
        for symptom, keywords in symptom_keywords.items():
            if any(kw in message for kw in keywords):
                found_symptoms.append(symptom)
        
        return found_symptoms
    
    def _analyze_symptoms(self, symptoms):
        """Analyze combination of symptoms"""
        conditions = []
        
        flu_symptoms = {'fever', 'cough', 'body ache', 'fatigue'}
        if len(set(symptoms) & flu_symptoms) >= 2:
            conditions.append("🟡 **Flu/Influenza** - Rest, hydrate, monitor temperature")
        
        covid_symptoms = {'fever', 'cough', 'breathlessness', 'fatigue'}
        if len(set(symptoms) & covid_symptoms) >= 2:
            conditions.append("🟠 **Possible COVID-19** - Get tested immediately! Isolate yourself.")
        
        cold_symptoms = {'sore throat', 'cough', 'headache'}
        if len(set(symptoms) & cold_symptoms) >= 2:
            conditions.append("🟢 **Common Cold** - Rest, warm fluids, steam inhalation")
        
        dengue_symptoms = {'fever', 'headache', 'body ache', 'rash'}
        if len(set(symptoms) & dengue_symptoms) >= 3:
            conditions.append("🔴 **Possible Dengue** - See doctor immediately! Get tested.")
        
        gastro_symptoms = {'stomach pain', 'nausea', 'diarrhea'}
        if len(set(symptoms) & gastro_symptoms) >= 2:
            conditions.append("🟡 **Gastroenteritis** - Stay hydrated (ORS), avoid solid food temporarily")
        
        # Emergency symptoms
        emergency_symptoms = {'breathlessness', 'chest pain'}
        if any(s in emergency_symptoms for s in symptoms):
            conditions.insert(0, "🔴 **EMERGENCY** - Seek immediate medical attention! Call 108")
        
        if not conditions:
            conditions.append("🟢 **General illness** - Monitor symptoms and consult doctor if worsens")
        
        return "\n\n".join(conditions)


# ========================================
# MEDICATION INFO
# ========================================
class ActionMedicationInfo(Action):
    def name(self) -> Text:
        return "action_medication_info"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        
        message = tracker.latest_message.get('text', '').lower()
        
        medications = {
            'paracetamol': """💊 **Paracetamol:**
• Use: Pain relief, fever reduction
• Dosage: 500-1000mg every 4-6 hours
• Warning: Don't exceed 4000mg/day
• Take with food if stomach upset""",

            'ibuprofen': """💊 **Ibuprofen:**
• Use: Pain, fever, inflammation
• Dosage: 200-400mg every 4-6 hours
• Warning: Take with food, avoid if ulcers""",
        }
        
        found = False
        for med_name, info in medications.items():
            if med_name in message:
                dispatcher.utter_message(text=info + "\n\n⚠️ Always consult doctor before taking any medication!")
                found = True
                break
        
        if not found:
            dispatcher.utter_message(
                text="💊 **Medication Information:**\n\n"
                     "For prescription medications, please consult:\n"
                     "• Your doctor\n"
                     "• Nearest PHC\n"
                     "• Call 1075\n\n"
                     "⚠️ Never self-medicate!"
            )
        
        return []


# ========================================
# ⭐ SINGLE UNIFIED HEALTH QUESTION HANDLER ⭐
# THIS IS THE ONLY ActionAnswerHealthQuestion CLASS
# ========================================
# ========================================
# ⭐ SINGLE UNIFIED HEALTH QUESTION HANDLER ⭐
# THIS IS THE ONLY ActionAnswerHealthQuestion CLASS
# ========================================
class ActionAnswerHealthQuestion(Action):
    def name(self) -> Text:
        return "action_answer_health_question"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        
        question = tracker.latest_message.get('text', '').lower()
        
        # Clean the query
        question = re.sub(r'^(i have|what is|tell me about|tell about|info about|information on|about|info on)\s+', '', question, flags=re.IGNORECASE)
        question = re.sub(r'\s+(info|information|symptoms|symptom|disease)$', '', question, flags=re.IGNORECASE)
        question = question.strip()
        
        print(f"[DEBUG] Cleaned question: '{question}'")
        
        # Quick response topics
        quick_topics = {
            'water': "💧 **Water Intake:** Adults should drink 8-10 glasses (2-3 liters) daily. More if exercising or hot weather. 📞 1075",
            'sleep': "😴 **Sleep:** Adults need 7-9 hours. Tips: fixed schedule, dark room, no screens before bed. 📞 1075",
            'exercise': "🏃 **Exercise:** 30 minutes moderate activity daily, 5 days/week. Walking, jogging, yoga, cycling. 📞 1075",
            'diet': "🥗 **Healthy Diet:** Eat variety: fruits, vegetables, whole grains, lean proteins. Limit sugar, salt, processed foods. 📞 1075",
        }
        
        # Check quick topics first
        for topic, answer in quick_topics.items():
            if topic in question:
                dispatcher.utter_message(text=answer)
                return []
        
        # Try external API
        print(f"[DEBUG] Trying API search for: {question}")
        result = search_health_info(question)
        
        if result:
            dispatcher.utter_message(text=result)
            return []
        
        # Comprehensive local knowledge base
        health_topics = {
            'fever': """🌡️ **Fever Management:**

**What is Fever?**
Body temperature above 100.4°F (38°C). It's a symptom, not a disease.

**Common Causes:**
- Infections (flu, cold, COVID)
- Heat exhaustion
- Inflammation

**Home Care:**
- Rest
- Drink plenty of fluids
- Take paracetamol (650mg every 6 hours)
- Lukewarm sponge bath
- Wear light clothing

**When to See Doctor:**
- Fever > 103°F
- Lasts more than 3 days
- Severe headache, stiff neck
- Difficulty breathing
- Rash
- Persistent vomiting

🏥 Free consultation at PHC
📞 Helpline: 1075
🚨 Emergency: 102/108""",

            'typhoid': """🦠 **Typhoid Fever:**

**What is it?**
Bacterial infection from contaminated food/water.

**Symptoms:**
- Prolonged high fever (103-104°F)
- Weakness, stomach pain
- Headache, loss of appetite
- Constipation or diarrhea

**Treatment:**
- Antibiotics (complete full course!)
- Rest and hydration
- Free at Government hospitals

**Prevention:**
- Drink boiled water
- Wash hands before eating
- Typhoid vaccine available (free)

🏥 Free treatment at PHCs
📞 Helpline: 1075""",

            'cholera': """💧 **Cholera - EMERGENCY:**

**Symptoms:**
- Severe watery diarrhea ("rice water")
- Rapid dehydration
- Vomiting
- Can be fatal within hours!

**URGENT Treatment:**
- ORS (Oral Rehydration Solution)
- IV fluids
- Antibiotics

**Prevention:**
- Boiled/treated water only
- Proper sanitation

🚨 Medical Emergency! Call 108
🏥 Free treatment at all hospitals
📞 Helpline: 1075""",

            'malaria': """🦟 **Malaria:**

**Symptoms:**
- High fever (comes in cycles)
- Chills and sweating
- Headache, body pain
- Nausea

**Diagnosis:**
- Blood test (free at PHCs)

**Treatment:**
- Anti-malarial drugs (FREE!)
- Complete full course

**Prevention:**
- Mosquito nets
- Remove stagnant water
- Repellents

🏥 Free diagnosis & treatment
📞 Helpline: 1075""",

            'dengue': """🦟 **Dengue:**

**Symptoms:**
- High fever
- Severe headache
- Pain behind eyes
- Joint/muscle pain
- Rash

**Treatment:**
- Rest, hydration
- Paracetamol only (NO aspirin!)
- Monitor platelet count

**Warning Signs:**
- Severe abdominal pain
- Persistent vomiting
- Bleeding

🚨 See doctor immediately!
🏥 Free treatment at Government hospitals
📞 Helpline: 1075""",

            'jaundice': """🟡 **Jaundice:**

**Symptoms:**
- Yellow skin and eyes
- Dark urine
- Pale stools
- Fatigue

**Causes:**
- Hepatitis (A, B, C, E)
- Liver disease
- Gallstones

**Treatment:**
- Depends on cause
- Rest, fluids
- Hepatitis vaccines available (free)

🏥 Free screening at PHCs
💉 Free hepatitis vaccines
📞 Helpline: 1075""",

            'tuberculosis': """🫁 **Tuberculosis (TB):**

**Symptoms:**
- Cough >2 weeks
- Coughing blood
- Fever, night sweats
- Weight loss

**Treatment:**
🎉 100% FREE under DOTS!
- 6-9 months medication
- Must complete full course
- 100% CURABLE!

**Prevention:**
- BCG vaccine (at birth)
- Good ventilation

🏥 Free diagnosis & treatment
💊 Free medicines at all PHCs
📞 TB Helpline: 1800-11-6666""",

            'diabetes': """🩸 **Diabetes:**

**Symptoms:**
- Excessive thirst
- Frequent urination
- Hunger, fatigue
- Blurred vision

**Prevention:**
- Healthy diet
- Regular exercise
- Maintain healthy weight

**Management:**
- Blood sugar monitoring
- Medications
- Lifestyle changes

🏥 Free screening at PHCs
📞 Helpline: 1075""",

            'hypertension': """🩺 **High Blood Pressure:**

**Normal:** <120/80 mmHg
**High:** >140/90 mmHg

**Prevention:**
- Reduce salt
- Exercise daily
- Manage stress
- Healthy weight

**Often NO symptoms - "Silent Killer"**

🏥 Free screening at all PHCs
📞 Helpline: 1075""",

            'asthma': """🫁 **Asthma:**

**Symptoms:**
- Wheezing
- Shortness of breath
- Chest tightness
- Cough

**Triggers:**
- Allergens, exercise, cold air

**Management:**
- Use inhaler as prescribed
- Avoid triggers

🏥 Free inhalers at Government hospitals
🚨 Emergency: 102/108""",

            'pcod': """🩺 **PCOD/PCOS:**

**Symptoms:**
- Irregular periods
- Weight gain
- Excess hair growth
- Acne
- Difficulty conceiving

**Management:**
- Weight loss (5-10% helps!)
- Exercise 30-60 min/day
- Balanced diet
- Medications

**It's manageable - you can lead normal life and have children!**

🏥 Free gynecology at Government hospitals
💊 Free medications
📞 Women's Helpline: 1091""",
  'hepatitis a': """🟡 **Hepatitis A:**

**What is it?**
Viral liver infection. Spreads through contaminated food/water.

**Symptoms:**
- Fatigue
- Nausea, vomiting
- Abdominal pain (right upper side)
- Dark urine
- Clay-colored stools
- Jaundice (yellow skin/eyes)

**Transmission:**
- Contaminated food/water
- Poor hygiene
- Raw shellfish from polluted water

**Treatment:**
- No specific antiviral
- Rest, avoid alcohol
- Stay hydrated
- Usually resolves in 1-2 months

**Prevention:**
- Hepatitis A vaccine (available)
- Wash hands thoroughly
- Drink boiled/purified water
- Eat hot, freshly cooked food

🏥 Free diagnosis at Government hospitals
💉 Hepatitis A vaccine available
📞 Helpline: 1075
⚠️ Unlike Hep B/C, Hep A does NOT become chronic!""",

            'hepatitis b': """🟡 **Hepatitis B:**

**What is it?**
Viral liver infection. Can be acute or chronic (long-term).

**Symptoms:**
- Fatigue
- Nausea, vomiting
- Abdominal pain
- Dark urine
- Jaundice
- Joint pain

**Transmission:**
- Blood contact
- Mother to baby (during birth)
- Unprotected sex
- Sharing needles
- NOT through casual contact, food, water

**Treatment:**
- Acute: Supportive care
- Chronic: Antiviral medications, regular monitoring

**Prevention:**
- Hepatitis B vaccine (MOST IMPORTANT!) - FREE
- FREE at all Government hospitals
- Birth dose + 3 doses in infancy
- Safe sex practices
- Don't share needles, razors

🏥 Free screening at Government hospitals
💉 FREE Hepatitis B vaccine (birth dose)
💊 Free treatment for chronic Hep B
📞 Helpline: 1075
⚠️ Pregnant women MUST get tested!
⚠️ Baby needs vaccine within 24 hours of birth!""",

            'hepatitis': """🟡 **Hepatitis:** Liver inflammation. Types: A, B, C, E. Prevention: vaccination (A, B - FREE), clean food/water. 📞 1075""",

            'chickenpox': """🔴 **Chickenpox (Varicella):**

**What is it?**
Highly contagious viral infection. Common in children.

**Symptoms:**
- Red, itchy rash (blisters)
- Fever
- Headache
- Tiredness
- Rash appears in waves (face → chest → all over)

**Contagious Period:**
- 1-2 days before rash appears
- Until all blisters have scabbed over (7-10 days)

**Treatment:**
- Rest and isolation
- Calamine lotion (for itching)
- Paracetamol for fever (NOT aspirin!)
- Lukewarm baths
- Cut nails short (prevent scratching)

**Do NOT:**
- Scratch blisters (causes scarring, infection)
- Give aspirin
- Send to school/work during infection

**Prevention:**
- Chickenpox vaccine (available)
- Isolate infected person
- Good hand hygiene

**When to See Doctor:**
- High fever >102°F
- Difficulty breathing
- Severe headache
- Blisters near eyes
- Infected blisters

🏥 Free treatment at Government hospitals
💉 Free chickenpox vaccine at some centers
📞 Helpline: 1075
⚠️ Adults: More severe - see doctor!""",

            'measles': """🔴 **Measles:**

**What is it?**
Highly contagious viral disease. Preventable by vaccination.

**Symptoms:**
- High fever (104°F+)
- Cough, runny nose, red eyes
- Tiny white spots in mouth
- Red rash (starts on face, spreads down)

**Contagious:**
- 4 days before rash to 4 days after
- 90% of unvaccinated contacts will get infected

**Complications:**
- Ear infections
- Pneumonia
- Diarrhea
- Brain inflammation (encephalitis)
- Death (1-2 per 1000 cases)

**Treatment:**
- No specific antiviral
- Supportive care
- Vitamin A supplements (reduces severity)
- Hospitalization if severe

**Prevention:**
- MMR/MR vaccine (MOST IMPORTANT!) - FREE
- Two doses: 9 months and 16-24 months
- Isolation of infected persons

🏥 Free treatment at Government hospitals
💉 FREE MR vaccine for all children
📞 Helpline: 1075
⚠️ Measles is SERIOUS - can cause death!
⚠️ Get vaccinated - vaccine is safe and effective!""",

            'mumps': """😷 **Mumps:**

**What is it?**
Viral infection affecting salivary glands. Causes swelling of cheeks/jaw.

**Symptoms:**
- Swollen, painful salivary glands (puffy cheeks)
- Fever
- Headache
- Muscle aches
- Pain while chewing/swallowing

**Contagious:**
- 2 days before swelling to 5 days after
- Sharing utensils, drinks

**Treatment:**
- No specific antiviral
- Rest
- Soft foods
- Warm/cold compress
- Paracetamol for pain/fever

**Complications (More in adults):**
- Orchitis (testicular inflammation in males)
- Oophoritis (ovarian inflammation in females)
- Meningitis
- Deafness (rare)

**Prevention:**
- MMR vaccine (FREE)
- Isolation during infection

🏥 Free treatment at Government hospitals
💉 FREE MMR vaccine
📞 Helpline: 1075
⚠️ Can cause infertility in males (rare)!""",

            'migraine': """🤕 **Migraine Headache:**

**What is it?**
Intense, throbbing headache, usually on one side.

**Symptoms:**
- Severe throbbing/pulsing pain
- Nausea and vomiting
- Sensitivity to light, sound
- Visual disturbances (aura): flashing lights
- Numbness or tingling

**Triggers:**
- Stress
- Hormonal changes (menstruation)
- Certain foods (cheese, chocolate, MSG)
- Bright lights, loud sounds
- Sleep changes
- Skipping meals

**Treatment:**

During Attack:
- Rest in dark, quiet room
- Cold compress on forehead
- Pain relievers (paracetamol, ibuprofen)
- Anti-migraine medications (triptans - by prescription)

Prevention:
- Identify and avoid triggers
- Regular sleep schedule
- Regular meals
- Stress management
- Stay hydrated

**When to See Doctor:**
- First-time severe headache
- Sudden, worst headache ever
- Headache with fever, stiff neck, confusion
- Frequent migraines (need preventive medication)

🏥 Free consultation at Government hospitals
💊 Neurologist at district hospitals
📞 Helpline: 1075
⚠️ Migraines are manageable with proper treatment!""",

            'headache': """🤕 **Headache:**

**Types:**
- Tension Headache (most common): dull, aching pain
- Migraine: throbbing, one side, severe
- Cluster Headache: severe pain around one eye

**Common Causes:**
- Stress, tension
- Lack of sleep
- Dehydration
- Hunger
- Eye strain
- Caffeine withdrawal

**Treatment:**

Immediate Relief:
- Rest in quiet, dark room
- Cold or warm compress
- Hydrate well
- Pain relievers (paracetamol, ibuprofen)
- Massage temples, neck

Prevention:
- Regular sleep schedule
- Stay hydrated
- Regular meals
- Manage stress
- Good posture

**RED FLAGS - See Doctor IMMEDIATELY:**
- Sudden, severe "thunderclap" headache
- Headache after head injury
- Fever, stiff neck, confusion
- Vision changes
- Worst headache of your life

🏥 Free consultation at PHCs
📞 Helpline: 1075
🚨 Severe sudden headache? Call 108!""",

            'back pain': """🔙 **Back Pain:**

**Symptoms:**
- Dull, aching pain
- Sharp, stabbing pain
- Pain radiating to legs
- Limited flexibility
- Muscle spasms

**Common Causes:**
- Muscle strain
- Poor posture
- Lifting heavy objects
- Prolonged sitting
- Weak core muscles
- Obesity

**Treatment:**

Immediate Care (First 48 hours):
- Ice pack (15-20 min, 3-4 times/day)
- Rest (but not too much!)
- Pain relievers

After 48 hours:
- Heat therapy
- Gentle stretching
- Gradual return to activity

Prevention:
- Good posture
- Regular exercise
- Core strengthening
- Proper lifting technique
- Maintain healthy weight

**RED FLAGS - See Doctor IMMEDIATELY:**
- Loss of bladder/bowel control
- Numbness in groin area
- Weakness in legs
- Fever with back pain
- After serious fall/injury
- Pain worsens at night

🏥 Free consultation at PHCs
💊 Physiotherapy at district hospitals
📞 Helpline: 1075""",

            'knee pain': """🦵 **Knee Pain:**

**Causes:**
- Injury (ligament, cartilage)
- Arthritis
- Overuse

**Immediate Care:**
- R.I.C.E: Rest, Ice, Compression, Elevation
- Avoid weight-bearing
- Apply ice pack
- Elevate leg

**URGENT - See Doctor If:**
- Can't bear weight on knee
- Severe swelling or deformed
- Knee gives way or locks
- Popping sound with severe pain
- Fever with knee pain

🏥 Free orthopedic at Government hospitals
📞 Helpline: 1075
🚨 Emergency: 102/108""",

            'leg pain': """🦵 **Leg Pain:**

**Immediate Relief:**
- Rest and elevate legs
- Apply ice or heat
- Gentle massage
- Stay hydrated

**URGENT - See Doctor IMMEDIATELY If:**
- Sudden severe pain with swelling, warmth, redness
- After long flight or bed rest (possible DVT blood clot!)
- Leg feels numb or cold
- Can't put weight on leg

🚨 DVT (Deep Vein Thrombosis) is SERIOUS - Call 108!

🏥 Free consultation at PHC
📞 Helpline: 1075""",

            'joint pain': """🦴 **Joint Pain:** Common causes: arthritis, injury, overuse. Management: R.I.C.E (Rest, Ice, Compression, Elevation), pain relievers. See doctor if persistent. 📞 1075""",

            'diabetes': """🩸 **Diabetes:**

**What is it?**
High blood sugar. Body can't produce/use insulin properly.

**Symptoms:**
- Excessive thirst
- Frequent urination
- Increased hunger
- Fatigue
- Blurred vision
- Slow-healing wounds

**Types:**
- Type 1: Body doesn't produce insulin
- Type 2: Body doesn't use insulin well (most common)

**Prevention:**
- Healthy diet
- Regular exercise (30 min/day)
- Maintain healthy weight
- Don't smoke

**Management:**
- Blood sugar monitoring
- Medications/insulin
- Lifestyle changes
- Regular check-ups

🏥 Free screening at PHCs
💊 Free medications available
📞 Helpline: 1075""",

            'hypertension': """🩺 **High Blood Pressure (Hypertension):**

**Normal:** <120/80 mmHg
**High:** >140/90 mmHg

**Often NO symptoms - "Silent Killer"**

**Prevention:**
- Reduce salt intake (<5g/day)
- Exercise daily
- Manage stress
- Maintain healthy weight
- Don't smoke
- Limited alcohol

**Monitoring:**
- Check BP regularly
- Free screening at Government hospitals

🏥 Free screening at all PHCs
💊 Free medications available
📞 Helpline: 1075""",

            'blood pressure': """🩺 **Blood Pressure:** Normal: <120/80 mmHg. High BP (hypertension): >140/90. Often no symptoms. Prevention: low salt, exercise, healthy weight. Free check at PHC. 📞 1075""",

            'thyroid': """🦋 **Thyroid:**

**Problems:**
- Hypothyroid (slow metabolism)
- Hyperthyroid (fast metabolism)

**Symptoms:**
- Weight changes
- Fatigue
- Mood swings

**Diagnosis:**
- TSH blood test (free at PHC)

🏥 Free treatment available
📞 Helpline: 1075""",

            'cancer': """🎗️ **Cancer:**

**Warning Signs:**
- Unexplained lumps
- Persistent pain
- Unusual bleeding
- Weight loss

**Early detection saves lives!**

🏥 Free screening at Government hospitals
📞 Cancer Helpline: 1800-11-2000""",

            'heart': """❤️ **Heart Disease:**

**Warning Signs:**
- Chest pain
- Shortness of breath
- Arm/jaw pain

**Prevention:**
- No smoking
- Exercise
- Healthy diet
- Control BP/diabetes

🏥 Free cardiac care under Ayushman Bharat
🚨 Chest pain? Call 108!""",

            'stroke': """🧠 **Stroke - EMERGENCY:**

**F.A.S.T:**
- Face drooping
- Arm weakness
- Speech difficulty
- Time to call 108!

Every minute counts!
🚨 Call 108 immediately!""",

            'covid': """😷 **COVID-19:**

**Symptoms:**
- Fever, cough
- Breathlessness
- Loss of taste/smell

**Action:**
- Isolate
- Get tested (free)
- Consult doctor

**Vaccination: FREE at all centers**

📞 COVID Helpline: 1800-11-4377""",

            'mental health': """🧠 **Mental Health:**

As important as physical health!

**Help Available:**
- Counseling
- Therapy
- Medications

**Seeking help is strength!**

📞 Mental Health Helpline: 1800-599-0019""",
  'pregnancy': """🤰 **Pregnancy Care:**

**Important:**
- Register at nearest PHC for FREE check-ups
- Eat nutritious food
- Take iron/folic acid tablets (free)
- Regular check-ups
- Avoid alcohol, smoking
- Adequate rest

**Free Services:**
- Antenatal check-ups
- Delivery (under JSY scheme)
- Postnatal care
- Immunizations

**Warning Signs - See Doctor:**
- Severe abdominal pain
- Heavy bleeding
- Severe headache
- Vision problems
- Reduced baby movement

🏥 Free delivery at Government hospitals
📞 Helpline: 1075
📱 Download: PMSMA App""",

            'pneumonia': """🫁 **Pneumonia:**

**What is it?**
Lung infection. Can be serious!

**Symptoms:**
- Cough (with phlegm)
- Fever, chills
- Chest pain (breathing/coughing)
- Difficulty breathing
- Fatigue

**Treatment:**
- Antibiotics
- Rest
- Hydration
- Oxygen (if needed)
- Hospitalization if severe

**Prevention:**
- Pneumococcal vaccine
- Flu vaccine
- Hand hygiene
- No smoking

🏥 Free treatment at Government hospitals
🚨 Breathing difficulty? Call 108!
📞 Helpline: 1075""",

  'cancer': """🎗️ **Cancer:**

**What is it?**
Abnormal cell growth.

**Warning Signs:**
- Unexplained lumps
- Persistent pain
- Unusual bleeding
- Unexplained weight loss
- Change in bowel/bladder habits
- Persistent cough
- Difficulty swallowing

**Prevention:**
- Don't smoke
- Healthy diet
- Regular exercise
- Limit alcohol
- Sun protection
- Regular screening

**Early detection saves lives!**

🏥 Free screening at Government hospitals
💊 Free treatment under various schemes
📞 National Cancer Helpline: 1800-11-2000""",

            'heart': """❤️ **Heart Disease:**

**Warning Signs:**
- Chest pain/discomfort
- Shortness of breath
- Pain in arm, jaw, neck
- Nausea, lightheadedness
- Cold sweat

**Prevention:**
- No smoking
- Exercise regularly
- Healthy diet (low salt, low fat)
- Control BP/diabetes
- Manage stress
- Maintain healthy weight

🏥 Free cardiac care under Ayushman Bharat
📞 Helpline: 1075
🚨 Chest pain? Call 108 immediately!""",

            'stroke': """🧠 **Stroke - MEDICAL EMERGENCY:**

**F.A.S.T Recognition:**
- **F**ace drooping (one side)
- **A**rm weakness (can't raise both)
- **S**peech difficulty (slurred)
- **T**ime to call 108!

**Other Signs:**
- Sudden severe headache
- Vision problems
- Dizziness, loss of balance
- Confusion

**Every minute counts! Brain cells die!**

🚨 Call 108 IMMEDIATELY!
Don't drive yourself - wait for ambulance!

Prevention:
- Control BP/diabetes
- No smoking
- Exercise
- Healthy diet""",

            'arthritis': """🦴 **Arthritis:**

**What is it?**
Joint inflammation. Pain and stiffness.

**Types:**
- Osteoarthritis (wear and tear)
- Rheumatoid arthritis (autoimmune)

**Symptoms:**
- Joint pain
- Stiffness (especially morning)
- Swelling
- Reduced range of motion

**Management:**
- Exercise (gentle, regular)
- Weight control
- Pain relievers
- Hot/cold therapy
- Physical therapy

🏥 Free treatment at PHC
💊 Rheumatologist at district hospitals
📞 Helpline: 1075""",

            'alzheimer': """🧠 **Alzheimer's Disease:**

**What is it?**
Progressive brain disorder affecting memory.

**Symptoms:**
- Memory loss affecting daily life
- Confusion about time/place
- Difficulty with tasks
- Misplacing things
- Personality changes
- Withdrawal from activities

**When to See Doctor:**
- Concerns about memory
- Changes in thinking
- Behavior changes

**Early diagnosis important!**

🏥 Free consultation at Government hospitals
📞 Helpline: 1075

⚠️ Not all memory loss is Alzheimer's!""",

            'depression': """😔 **Depression:**

**Symptoms:**
- Persistent sadness
- Loss of interest in activities
- Fatigue
- Sleep problems
- Changes in appetite
- Difficulty concentrating
- Feelings of worthlessness
- Thoughts of self-harm

**It's treatable!**

**Help Available:**
- Counseling
- Therapy (CBT)
- Medications
- Support groups

**Seeking help is strength, not weakness!**

🏥 Free mental health services
📞 National Mental Health Helpline: 1800-599-0019
📞 General Helpline: 1075

🚨 Thoughts of self-harm? Call immediately!""",

            'anxiety': """😰 **Anxiety:**

**Symptoms:**
- Excessive worry
- Restlessness
- Rapid heartbeat
- Difficulty concentrating
- Sleep problems
- Muscle tension
- Panic attacks

**Management:**
- Therapy (CBT)
- Relaxation techniques
- Breathing exercises
- Medications (if needed)
- Regular exercise
- Adequate sleep

🏥 Free mental health services
📞 Mental Health Helpline: 1800-599-0019
📞 General Helpline: 1075""",

        }
        
        # Check local knowledge base with partial matching
        for topic, answer in health_topics.items():
            if topic in question or question in topic:
                print(f"[DEBUG] Matched topic: {topic}")
                dispatcher.utter_message(text=answer)
                return []
        
        # Ultimate fallback
        dispatcher.utter_message(
            text="I don't have specific information about that condition.\n\n"
                 "**I can help with:**\n"
                 "• Common conditions (typhoid, cholera, malaria, dengue, jaundice)\n"
                 "• Chronic diseases (diabetes, hypertension, asthma, PCOD)\n"
                 "• Symptoms (fever, cough, pain)\n"
                 "• Preventive care\n\n"
                 "**For specific medical advice:**\n"
                 "📞 National Health Helpline: 1075\n"
                 "🏥 Visit nearest PHC/Government hospital"
        )
        
        return []

# ========================================
# REMEDY SUGGESTION
# ========================================
class ActionSuggestRemedyFinal(Action):
    def name(self) -> Text:
        return "action_suggest_remedy_final"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        
        symptom = tracker.get_slot("symptom_name")
        
        if not symptom:
            message = tracker.latest_message.get('text', '').lower()
            if 'fever' in message:
                symptom = 'fever'
            elif 'cough' in message:
                symptom = 'cough'
            elif 'headache' in message:
                symptom = 'headache'
        
        if symptom:
            remedies = {
                'fever': "Rest, drink fluids, take paracetamol. See doctor if > 102°F or lasts > 3 days.",
                'cough': "Warm water with honey, steam inhalation, stay hydrated. See doctor if lasts > 2 weeks.",
                'headache': "Rest in dark room, drink water, cold compress. Persistent headaches need doctor visit.",
            }
            
            remedy = remedies.get(symptom, "Rest, stay hydrated, consult doctor if symptoms worsen.")
            
            dispatcher.utter_message(
                text=f"💊 **Remedy for {symptom}:**\n\n{remedy}\n\n"
                     "⚠️ Consult doctor for persistent symptoms\n"
                     "📞 Helpline: 1075"
            )
        else:
            dispatcher.utter_message(text="Please tell me your symptom first.")
        
        return []


# ========================================
# DISEASE OUTBREAK ALERTS
# ========================================
class ActionOutbreakAlerts(Action):
    def name(self) -> Text:
        return "action_outbreak_alerts"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        
        location = tracker.get_slot("location") or "India"
        
        try:
            alerts = self._get_outbreak_alerts(location)
            
            message = f"🚨 **Health Alerts for {location}:**\n\n"
            message += alerts
            message += "\n\n📞 Report outbreaks: 104 (State Health Helpline)"
            
            dispatcher.utter_message(text=message)
            
        except Exception as e:
            dispatcher.utter_message(
                text="For latest health alerts:\n"
                     "📱 Download Aarogya Setu App\n"
                     "🌐 Visit: mohfw.gov.in\n"
                     "📞 Call: 1075"
            )
            print(f"Alert error: {e}")
        
        return []
    
    def _get_outbreak_alerts(self, location):
        """Get disease outbreak alerts"""
        
        common_alerts = {
            'Maharashtra': [
                "🦟 Dengue: High alert during monsoon. Use mosquito nets.",
                "🦟 Malaria: Risk in rural areas. Take prophylaxis.",
                "🌊 Waterborne diseases: Ensure clean drinking water.",
                "🌡️ Heat stroke: Risk during summer. Stay hydrated."
            ],
            'Odisha': [
                "🦟 Dengue: High alert during monsoon. Use mosquito nets.",
                "🦟 Malaria: Endemic in tribal areas. Take prophylaxis.",
                "🌊 Diarrheal diseases: Ensure clean drinking water.",
                "🌡️ Heat stroke: Risk during summer. Stay hydrated."
            ],
            'India': [
                "😷 COVID-19: Follow COVID-appropriate behavior",
                "🦟 Dengue & Chikungunya: Monsoon season alert",
                "🤒 Seasonal Flu: Get vaccinated annually",
                "🌊 Waterborne diseases: Boil water before drinking"
            ]
        }
        
        alerts = common_alerts.get(location, common_alerts['India'])
        
        message = ""
        for i, alert in enumerate(alerts, 1):
            message += f"{i}. {alert}\n"
        
        message += "\n**Prevention Tips:**\n"
        message += "• Maintain hygiene\n"
        message += "• Use mosquito repellent\n"
        message += "• Drink clean water\n"
        message += "• Get timely vaccinations\n"
        message += "• Visit doctor if symptoms appear"
        
        return message


# ========================================
# BMI CALCULATOR
# ========================================
class ValidateBMIForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_bmi_form"

    def validate_weight(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate weight input"""
        try:
            if isinstance(slot_value, str):
                slot_value = slot_value.lower().replace('kg', '').replace('kgs', '').replace('kilos', '').strip()
            
            weight = float(slot_value)
            
            if 20 <= weight <= 300:
                return {"weight": weight}
            else:
                dispatcher.utter_message(text="⚠ Please enter a valid weight between 20-300 kg.")
                return {"weight": None}
                
        except (ValueError, TypeError):
            dispatcher.utter_message(text="⚠ Please enter weight as a number (e.g., 70 or 70.5)")
            return {"weight": None}

    def validate_height(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate height input"""
        try:
            if isinstance(slot_value, str):
                slot_value = slot_value.lower().replace('cm', '').replace('centimeters', '').replace('centimeter', '').strip()
                
                if 'feet' in slot_value or 'foot' in slot_value or 'ft' in slot_value:
                    dispatcher.utter_message(text="Please enter height in centimeters (cm).\nExample: 170 cm")
                    return {"height": None}
            
            height = float(slot_value)
            
            if 1.0 <= height <= 2.5:
                height = height * 100
                dispatcher.utter_message(text=f"✓ Converted to {height} cm")
            
            if 50 <= height <= 250:
                return {"height": height}
            else:
                dispatcher.utter_message(text="⚠ Please enter a valid height between 50-250 cm.")
                return {"height": None}
                
        except (ValueError, TypeError):
            dispatcher.utter_message(text="⚠ Please enter height as a number in centimeters (e.g., 170)")
            return {"height": None}

    def validate_age(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate age input"""
        try:
            if isinstance(slot_value, str):
                slot_value = slot_value.lower().replace('years', '').replace('year', '').replace('yrs', '').replace('yr', '').strip()
            
            age = float(slot_value)
            
            if 2 <= age <= 120:
                return {"age": age}
            else:
                dispatcher.utter_message(text="⚠ Please enter a valid age between 2-120 years.")
                return {"age": None}
                
        except (ValueError, TypeError):
            dispatcher.utter_message(text="⚠ Please enter age as a number (e.g., 25)")
            return {"age": None}

    def validate_gender(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate gender input"""
        if isinstance(slot_value, str):
            gender = slot_value.lower().strip()
            
            if any(g in gender for g in ['male', 'man', 'boy', 'm']):
                return {"gender": "male"}
            elif any(g in gender for g in ['female', 'woman', 'girl', 'f']):
                return {"gender": "female"}
            elif any(g in gender for g in ['other', 'transgender', 'trans']):
                return {"gender": "other"}
        
        dispatcher.utter_message(text="⚠ Please specify: Male, Female, or Other")
        return {"gender": None}


class ActionCalculateBMI(Action):
    def name(self) -> Text:
        return "action_calculate_bmi"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        
        try:
            weight = tracker.get_slot("weight")
            height = tracker.get_slot("height")
            age = tracker.get_slot("age")
            gender = tracker.get_slot("gender")
            
            if not all([weight, height, age, gender]):
                dispatcher.utter_message(text="⚠ Missing information. Please try again.")
                return [
                    SlotSet("weight", None),
                    SlotSet("height", None),
                    SlotSet("age", None),
                    SlotSet("gender", None)
                ]
            
            height_m = height / 100
            bmi = weight / (height_m ** 2)
            bmi_rounded = round(bmi, 1)
            
            category, emoji, risk = self._get_bmi_category(bmi, age)
            recommendations = self._get_recommendations(bmi, age, gender, weight, height_m)
            ideal_min, ideal_max = self._calculate_ideal_weight(height_m)
            
            message = f"""📊 BMI Calculation Results

👤 Your Details:
- Gender: {gender.title()}
- Age: {int(age)} years
- Weight: {weight} kg
- Height: {height} cm ({height_m:.2f} m)

📈 Your BMI: {bmi_rounded}

{emoji} Category: {category}
⚠ Health Risk: {risk}

💪 Ideal Weight Range:
{ideal_min} - {ideal_max} kg
(For your height)

{recommendations}

📞 Free Healthcare:
🏥 Free BMI screening at all PHCs
💊 Free diet counseling at wellness centers
📱 Download India Nutrition App
📞 National Health Helpline: 1075

⚠ Note: BMI is a screening tool. Consult doctor for complete health assessment."""

            dispatcher.utter_message(text=message)
            
            return [
                SlotSet("weight", None),
                SlotSet("height", None),
                SlotSet("age", None),
                SlotSet("gender", None)
            ]
            
        except Exception as e:
            print(f"[ERROR] BMI calculation failed: {e}")
            dispatcher.utter_message(text="⚠ Unable to calculate BMI. Please try again.\n📞 Helpline: 1075")
            
            return [
                SlotSet("weight", None),
                SlotSet("height", None),
                SlotSet("age", None),
                SlotSet("gender", None)
            ]

    def _get_bmi_category(self, bmi: float, age: float) -> tuple:
        if age < 18:
            if bmi < 16:
                return "Severely Underweight", "🔴", "High - Malnutrition Risk"
            elif bmi < 18.5:
                return "Underweight", "🟡", "Moderate - Nutritional Deficiency"
            elif bmi < 25:
                return "Normal (Healthy)", "🟢", "Low - Good Health"
            elif bmi < 30:
                return "Overweight", "🟡", "Moderate - Health Issues Possible"
            else:
                return "Obese", "🔴", "High - Serious Health Risks"
        
        if bmi < 16:
            return "Severely Underweight", "🔴", "High - Severe Malnutrition"
        elif bmi < 18.5:
            return "Underweight", "🟡", "Moderate - Nutritional Deficiency"
        elif bmi < 25:
            return "Normal (Healthy Weight)", "🟢", "Low - Optimal Health"
        elif bmi < 30:
            return "Overweight (Pre-Obese)", "🟡", "Moderate - Increased Risk"
        elif bmi < 35:
            return "Obese Class I", "🟠", "High - Significant Risk"
        elif bmi < 40:
            return "Obese Class II", "🔴", "Very High - Severe Risk"
        else:
            return "Obese Class III (Morbidly Obese)", "🔴", "Extremely High - Critical"

    def _calculate_ideal_weight(self, height_m: float) -> tuple:
        min_weight = 18.5 * (height_m ** 2)
        max_weight = 24.9 * (height_m ** 2)
        return round(min_weight, 1), round(max_weight, 1)

    def _get_recommendations(self, bmi: float, age: float, gender: str, weight: float, height_m: float) -> str:
        recommendations = "\n🎯 Personalized Recommendations:\n\n"
        
        if bmi < 18.5:
            ideal_min, _ = self._calculate_ideal_weight(height_m)
            weight_to_gain = round(ideal_min - weight, 1)
            recommendations += f"""Goal: Gain ~{weight_to_gain} kg

Diet: Increase calories, eat nutritious foods
Exercise: Strength training
📞 Free nutrition counseling at PHC"""
        
        elif bmi < 25:
            recommendations += """✅ Your weight is HEALTHY!

Maintain by:
- Balanced diet
- Regular exercise (30 min/day)
- Stay hydrated
- Adequate sleep

Keep up the good work! 💪"""
        
        else:
            ideal_min, ideal_max = self._calculate_ideal_weight(height_m)
            weight_to_lose = round(weight - ideal_max, 1)
            recommendations += f"""Goal: Lose ~{weight_to_lose} kg

Diet: Reduce 500 calories/day
- Avoid fried, sugary foods
- Increase vegetables, protein

Exercise: 45-60 min daily walk
Weekly Target: Lose 0.5-1 kg

📞 Free weight management at wellness centers"""
        
        return recommendations


# ========================================
# PREVENTIVE HEALTHCARE
# ========================================
class ActionPreventiveHealthcare(Action):
    def name(self) -> Text:
        return "action_preventive_healthcare"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        
        message_text = tracker.latest_message.get('text', '').lower()
        advice = self._get_preventive_advice(message_text)
        dispatcher.utter_message(text=advice)
        return []
    
    def _get_preventive_advice(self, query):
        preventive_measures = {
            'diabetes': """🍎 **Prevent Diabetes:**

**Diet:**
• Reduce sugar and refined carbs
• Eat whole grains, vegetables, fruits
• Control portion sizes

**Lifestyle:**
• Exercise 30 minutes daily
• Maintain healthy weight
• Don't smoke

**Screening:**
• Blood sugar test after age 45
• Free screening at PHCs

📞 Helpline: 1075""",

            'hypertension': """❤️ **Prevent High Blood Pressure:**

**Diet:**
• Reduce salt intake (< 5g/day)
• Eat potassium-rich foods
• DASH diet

**Lifestyle:**
• Regular exercise
• Maintain healthy weight
• Manage stress
• Don't smoke

**Monitoring:**
• Check BP regularly
• Free screening at Government hospitals

📞 Helpline: 1075""",
        }
        
        for disease, advice in preventive_measures.items():
            if disease in query:
                return advice
        
        return """🏥 **General Preventive Healthcare:**

**Healthy Lifestyle:**
• Balanced diet
• Regular exercise (30 min/day)
• Adequate sleep (7-8 hours)
• No smoking/tobacco
• Limited alcohol

**Regular Check-ups:**
• Annual health screening
• Blood pressure monitoring
• Blood sugar testing
• Vaccinations

📞 National Health Helpline: 1075
🌐 Visit: mohfw.gov.in"""


# ========================================
# HEALTH CHECKUP FORM VALIDATION
# ========================================
class ValidateHealthCheckupForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_health_checkup_form"

    def validate_temperature(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        
        if isinstance(slot_value, str):
            slot_value = slot_value.lower()
            
            if slot_value in ["normal", "fine", "ok", "good"]:
                return {"temperature": 98.6}
            
            try:
                temp = float(slot_value)
                if 95.0 <= temp <= 107.0:
                    return {"temperature": temp}
                else:
                    dispatcher.utter_message(text="Temperature should be between 95°F and 107°F.")
                    return {"temperature": None}
            except ValueError:
                dispatcher.utter_message(text="Please provide valid temperature (e.g., 98.6 or 'normal').")
                return {"temperature": None}
        
        return {"temperature": slot_value}

    def validate_mood_level(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        
        valid_moods = ["happy", "neutral", "sad", "anxious", "stressed", "good", "bad", "ok", "fine"]
        
        if isinstance(slot_value, str):
            if any(mood in slot_value.lower() for mood in valid_moods):
                return {"mood_level": slot_value}
        
        dispatcher.utter_message(text="Please describe your mood (happy, sad, anxious, neutral).")
        return {"mood_level": None}

    def validate_pain_score(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        
        if isinstance(slot_value, str):
            slot_value = slot_value.lower()
            
            if slot_value in ["no", "none", "zero", "no pain"]:
                return {"pain_score": "0"}
            
            try:
                score = int(slot_value)
                if 0 <= score <= 10:
                    return {"pain_score": str(score)}
                else:
                    dispatcher.utter_message(text="Pain score should be 0-10.")
                    return {"pain_score": None}
            except ValueError:
                dispatcher.utter_message(text="Please provide number 0-10.")
                return {"pain_score": None}
        
        return {"pain_score": slot_value}

    def validate_symptom_name(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        
        if slot_value and len(slot_value) > 2:
            return {"symptom_name": slot_value}
        
        dispatcher.utter_message(text="Please describe symptoms (headache, fever, cough).")
        return {"symptom_name": None}


# ========================================
# SUBMIT CHECKUP
# ========================================
class ActionSubmitCheckup(Action):
    def name(self) -> Text:
        return "action_submit_checkup"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        
        temperature = tracker.get_slot("temperature")
        mood = tracker.get_slot("mood_level")
        pain = tracker.get_slot("pain_score")
        symptom = tracker.get_slot("symptom_name")

        message = "📊 **Health Check-up Summary:**\n\n"
        message += f"🌡️ Temperature: {temperature}°F\n"
        message += f"😊 Mood: {mood}\n"
        message += f"💢 Pain: {pain}/10\n"
        message += f"🩺 Symptoms: {symptom}\n\n"

        analysis = self._analyze_health(temperature, mood, pain, symptom)
        message += f"**Recommendations:**\n{analysis}\n\n"
        message += "⚠️ For serious concerns, visit nearest PHC or call 104/1075"

        dispatcher.utter_message(text=message)
        
        return [
            SlotSet("temperature", None),
            SlotSet("mood_level", None),
            SlotSet("pain_score", None),
            SlotSet("symptom_name", None)
        ]

    def _analyze_health(self, temp, mood, pain, symptom):
        recs = []
        
        if isinstance(temp, (int, float)):
            if temp > 100.4:
                recs.append("🔥 Fever detected. Rest, hydrate, consult doctor if persists.")
            elif temp >= 103:
                recs.append("🚨 HIGH FEVER! Seek immediate medical attention!")
        
        try:
            pain_val = int(pain) if pain else 0
            if pain_val >= 7:
                recs.append("⚠️ High pain level. Seek medical attention.")
            elif pain_val >= 4:
                recs.append("💊 Moderate pain. Rest and consider pain relief.")
        except:
            pass
        
        if mood and any(m in str(mood).lower() for m in ["sad", "anxious", "stressed"]):
            recs.append("🧠 Mental health matters. Consider relaxation or counseling.")
        
        if not recs:
            recs.append("✅ Health seems stable. Maintain healthy habits!")
        
        return "\n".join(f"• {r}" for r in recs)


# ========================================
# SYMPTOM RESPONSE
# ========================================
class ActionRespondSymptom(Action):
    def name(self) -> Text:
        return "action_respond_symptom"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        
        message = tracker.latest_message.get('text', '').lower()
        symptom_name = self._extract_symptom(message)
        advice = self._get_symptom_advice(symptom_name, message)
        
        dispatcher.utter_message(text=advice)
        return []
    
    def _extract_symptom(self, message):
        """Extract symptom from message"""
        symptoms = [
            ('knee pain', ['knee pain', 'knees hurt', 'knee hurting', 'pain in knee', 'my knee', 'knee ache']),
            ('leg pain', ['leg pain', 'legs hurt', 'leg hurting', 'pain in leg', 'my leg', 'leg ache']),
            ('joint pain', ['joint pain', 'joints hurt', 'joint ache']),
            ('migraine', ['migraine']),
            ('headache', ['headache', 'head pain', 'head ache']),
            ('chest pain', ['chest pain', 'chest ache']),
            ('back pain', ['back pain', 'back ache']),
            ('stomach pain', ['stomach pain', 'stomach ache', 'belly pain']),
            ('body pain', ['body pain', 'body ache', 'muscle pain']),
            ('fever', ['fever', 'temperature', 'feverish']),
            ('cough', ['cough', 'coughing']),
            ('cold', ['cold', 'runny nose', 'sneezing']),
            ('sore throat', ['sore throat', 'throat pain']),
            ('diarrhea', ['diarrhea', 'loose motion']),
            ('vomiting', ['vomit', 'vomiting', 'nausea']),
            ('breathlessness', ['breathless', 'breathing problem']),
        ]
        
        for symptom, keywords in symptoms:
            for keyword in keywords:
                if keyword in message:
                    return symptom
        
        return "general"
    
    def _get_symptom_advice(self, symptom, message=""):
        """Provide advice for symptoms"""
        
        symptom_advice = {
            'knee pain': """🦵 **Knee Pain Relief:**

**Immediate Care:**
• R.I.C.E: Rest, Ice, Compression, Elevation
• Avoid putting weight on knee
• Apply ice pack (15-20 min, 3-4 times/day)
• Elevate leg when sitting/lying

**URGENT - See Doctor If:**
• Can't bear weight on knee
• Severe swelling or knee looks deformed
• Knee gives way or locks
• Popping sound with severe pain
• Fever with knee pain (infection)

🏥 Free orthopedic consultation at Government hospitals
📞 Helpline: 1075
🚨 Emergency: 102/108""",

            'leg pain': """🦵 **Leg Pain Relief:**

**Immediate Relief:**
• Rest and elevate legs above heart level
• Apply ice (first 48 hours) or heat (after 48 hours)
• Gentle massage
• Stay hydrated

**URGENT - See Doctor IMMEDIATELY If:**
• Sudden severe pain with swelling, warmth, redness
• After long flight or bed rest (possible DVT blood clot!)
• Leg feels numb or cold
• Can't put weight on leg

🚨 DVT (Deep Vein Thrombosis) is SERIOUS - Call 108!

🏥 Free consultation at PHC
📞 Helpline: 1075""",

            'fever': """🌡️ **Fever Management:**
Rest, drink fluids, take paracetamol. 
See doctor if > 102°F or lasts > 3 days.
📞 Emergency: 102/108""",

            'headache': """🤕 **Headache Relief:**
Rest in dark room, drink water, cold compress. 
See doctor if severe or persistent.
📞 Helpline: 1075""",

            'cough': """🤧 **Cough Relief:**
Warm water with honey, steam inhalation, stay hydrated.
See doctor if lasts > 2 weeks or blood in sputum.
📞 Helpline: 1075""",

            'stomach pain': """🤢 **Stomach Pain:**
Rest, avoid solid food temporarily, drink clear liquids.
URGENT if: severe pain, vomiting blood, black stools.
📞 Emergency: 102/108""",

            'chest pain': """🚨 **CHEST PAIN - EMERGENCY:**
Could be heart attack!
Call 108 IMMEDIATELY!
Don't drive yourself - wait for ambulance.
🚨 Every second counts!""",

            'breathlessness': """🚨 **BREATHLESSNESS - EMERGENCY:**
Difficulty breathing is serious!
Call 108 IMMEDIATELY!
Sit upright, stay calm.
🚨 Don't delay!""",
        }
        
        if symptom in symptom_advice:
            return symptom_advice[symptom]
        else:
            return f"""🩺 **Health Concern: {symptom.title()}**

**General Advice:**
• Rest and monitor symptoms
• Stay hydrated
• Maintain hygiene

**Free Healthcare:**
• Visit nearest PHC
• Helpline: 1075
• Emergency: 102/108"""


# ========================================
# ADDITIONAL UTILITY ACTIONS
# ========================================
class ActionFetchHealthData(Action):
    def name(self) -> Text:
        return "action_fetch_health_data"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        
        try:
            response = requests.get("https://disease.sh/v3/covid-19/all", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                message = "🌍 **Global COVID-19 Data:**\n\n"
                message += f"• Total Cases: {data.get('cases', 'N/A'):,}\n"
                message += f"• Deaths: {data.get('deaths', 'N/A'):,}\n"
                message += f"• Recovered: {data.get('recovered', 'N/A'):,}\n"
                message += f"• Active: {data.get('active', 'N/A'):,}\n\n"
                message += "📊 Source: Disease.sh (Live Data)"
                
                dispatcher.utter_message(text=message)
            else:
                dispatcher.utter_message(text="Unable to fetch data. Call 1075")
        
        except Exception as e:
            dispatcher.utter_message(text="Error fetching data. Please try: mohfw.gov.in")
            print(f"Error: {e}")
        
        return []


class ActionFetchDiseaseInfo(Action):
    def name(self) -> Text:
        return "action_fetch_disease_info"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        
        message_text = tracker.latest_message.get('text', '').lower()
        
        if 'covid' in message_text or 'coronavirus' in message_text:
            action = ActionFetchHealthData()
            return action.run(dispatcher, tracker, domain)
        else:
            wiki_answer = search_health_info(message_text)
            if wiki_answer:
                dispatcher.utter_message(text=wiki_answer)
            else:
                dispatcher.utter_message(
                    text="For detailed disease information:\n"
                         "🌐 WHO: https://www.who.int\n"
                         "🌐 CDC: https://www.cdc.gov\n"
                         "📞 Helpline: 1075"
                )
        
        return []


class ActionFetchHealthNews(Action):
    def name(self) -> Text:
        return "action_fetch_health_news"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        
        dispatcher.utter_message(
            text="📰 **For Latest Health News:**\n\n"
                 "🌐 Visit: mohfw.gov.in\n"
                 "📱 Download: Aarogya Setu App\n"
                 "📞 Helpline: 1075"
        )
        
        return []


class ActionFetchVaccinationData(Action):
    def name(self) -> Text:
        return "action_fetch_vaccination_data"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        
        try:
            response = requests.get(
                "https://disease.sh/v3/covid-19/vaccine/coverage/countries/india?lastdays=1",
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                
                message = "💉 **COVID-19 Vaccination Data (India):**\n\n"
                
                if data.get('timeline'):
                    latest_date = list(data['timeline'].keys())[0]
                    doses = data['timeline'][latest_date]
                    message += f"• Total Doses: {doses:,}\n"
                    message += f"• Date: {latest_date}\n\n"
                
                message += "📱 Register: CoWIN Portal\n"
                message += "🆓 FREE for all citizens\n"
                message += "📞 Helpline: 1075"
                
                dispatcher.utter_message(text=message)
            else:
                dispatcher.utter_message(text="Visit CoWIN portal for vaccination info")
        
        except Exception as e:
            dispatcher.utter_message(text="For vaccination data, visit: cowin.gov.in")
            print(f"Vaccination error: {e}")
        
        return []