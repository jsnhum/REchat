import streamlit as st
import openai
import anthropic
import google.generativeai as genai
from openai import OpenAI
import json
from datetime import datetime
import os
import re

def extract_name_from_description(description):
    """Extract name from persona description"""
    # Try to find name patterns like "This is Ahmed" or "Meet Sara" or just "Ahmed,"
    patterns = [
        r'This is ([A-Z][a-z]+)',
        r'Meet ([A-Z][a-z]+)',
        r'^([A-Z][a-z]+),',
        r'named ([A-Z][a-z]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, description)
        if match:
            return match.group(1)
    
    # Fallback: try to find any capitalized name in the first sentence
    first_sentence = description.split('.')[0]
    words = first_sentence.split()
    for word in words:
        cleaned = word.strip('[](),')
        if cleaned and cleaned[0].isupper() and len(cleaned) > 2 and cleaned.isalpha():
            return cleaned
    
    return "The persona"

def format_conversation_for_download():
    """Format the conversation for download as text"""
    if not st.session_state.messages:
        return "No conversation to download."
    
    # Get current date and time
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Create header
    text_content = "="*60 + "\n"
    text_content += "RELIGIOUS PERSONA CONVERSATION\n"
    text_content += "="*60 + "\n"
    text_content += f"Downloaded: {current_time}\n\n"
    
    # Add persona settings
    text_content += "PERSONA SETTINGS:\n"
    text_content += "-"*60 + "\n"
    text_content += f"Religious Tradition: {st.session_state.get('persona_tradition', 'N/A')}\n"
    text_content += f"Denomination/Movement: {st.session_state.get('persona_denomination', 'N/A')}\n"
    text_content += f"Geographic/Cultural Context: {st.session_state.get('persona_context', 'N/A')}\n"
    text_content += f"Demographics: {st.session_state.get('persona_demographics', 'N/A')}\n"
    text_content += f"Personality: {st.session_state.get('persona_personality', 'Not specified')}\n"
    text_content += f"Knowledge Level: {st.session_state.get('persona_knowledge_level', 'N/A')}\n"
    text_content += f"Engagement Level: {st.session_state.get('persona_engagement_level', 'N/A')}\n"
    text_content += f"Attitude towards Religion: {st.session_state.get('persona_attitude', 'N/A')}\n\n"
    
    # Add persona introduction
    text_content += "PERSONA INTRODUCTION:\n"
    text_content += "-"*60 + "\n"
    if 'persona_description_text' in st.session_state and st.session_state.persona_description_text:
        text_content += st.session_state.persona_description_text + "\n\n"
    else:
        text_content += "N/A\n\n"
    
    # Add conversation transcript
    text_content += "="*60 + "\n"
    text_content += "CONVERSATION TRANSCRIPT:\n"
    text_content += "="*60 + "\n\n"
    
    # Add conversation messages
    for i, message in enumerate(st.session_state.messages, 1):
        role = "Me" if message["role"] == "user" else "Persona"
        text_content += f"{role}: {message['content']}\n\n"
    
    return text_content

def generate_persona_description(llm_choice, api_key, desc_prompt):
    """Generate persona description - separate from conversation"""
    try:
        if llm_choice == "OpenAI GPT-4o":
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": desc_prompt}],
                max_tokens=200,
                temperature=0.7
            )
            return response.choices[0].message.content
        
        elif llm_choice == "Claude (Anthropic)":
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=200,
                messages=[{"role": "user", "content": desc_prompt}]
            )
            return response.content[0].text
        
        elif llm_choice == "Google Gemini":
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(desc_prompt)
            return response.text
            
    except Exception as e:
        raise Exception(f"Description generation error: {str(e)}")

def generate_response(llm_choice, api_key, persona, messages, user_input):
    """Generate response based on selected LLM"""
    
    # Prepare conversation history
    conversation_history = []
    conversation_history.append({"role": "system", "content": persona})
    
    # Add previous messages (limit to last 10 for context)
    for msg in messages[-10:]:
        conversation_history.append(msg)
    
    try:
        if llm_choice == "OpenAI GPT-4o":
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=conversation_history,
                max_tokens=500,
                #temperature=0.7
            )
            return response.choices[0].message.content
        
        elif llm_choice == "Claude (Anthropic)":
            client = anthropic.Anthropic(api_key=api_key)
            # Convert messages format for Claude
            claude_messages = []
            for msg in conversation_history[1:]:  # Skip system message
                claude_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                system=persona,
                messages=claude_messages
            )
            return response.content[0].text
        
        elif llm_choice == "Google Gemini":
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-pro')
            
            # Format for Gemini
            prompt = persona + "\n\nConversation:\n"
            for msg in messages[-5:]:  # Last 5 messages for context
                role = "Human" if msg["role"] == "user" else "Assistant"
                prompt += f"{role}: {msg['content']}\n"
            prompt += f"Human: {user_input}\nAssistant:"
            
            response = model.generate_content(prompt)
            return response.text

    except Exception as e:
        raise Exception(f"API Error: {str(e)}")

# Page configuration
st.set_page_config(
    page_title="Religious Persona Chatbot - Educational Tool",
    page_icon="🕊️",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem 0;
        border-bottom: 2px solid #e0e0e0;
        margin-bottom: 2rem;
    }
    .persona-box {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #4CAF50;
        margin: 1rem 0;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    .user-message {
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
    }
    .bot-message {
        background-color: #f1f8e9;
        border-left: 4px solid #4caf50;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'persona_created' not in st.session_state:
    st.session_state.persona_created = False
if 'current_persona' not in st.session_state:
    st.session_state.current_persona = ""
if 'persona_name' not in st.session_state:
    st.session_state.persona_name = "The persona"
if 'persona_description_text' not in st.session_state:
    st.session_state.persona_description_text = ""
if 'persona_demographics' not in st.session_state:
    st.session_state.persona_demographics = ""
if 'persona_personality' not in st.session_state:
    st.session_state.persona_personality = ""
if 'persona_knowledge_level' not in st.session_state:
    st.session_state.persona_knowledge_level = ""
if 'persona_engagement_level' not in st.session_state:
    st.session_state.persona_engagement_level = ""
if 'persona_attitude' not in st.session_state:
    st.session_state.persona_attitude = ""
if 'generating_new_persona' not in st.session_state:
    st.session_state.generating_new_persona = False

# Header
st.markdown('<div class="main-header"><h1>🕊️ Religious Persona Chatbot</h1><p>An Educational Tool for Exploring Religious Diversity</p></div>', unsafe_allow_html=True)

# Sidebar for LLM selection and API keys
st.sidebar.header("🤖 AI Model Selection")

llm_choice = st.sidebar.selectbox(
    "Choose an AI Model:",
    ["OpenAI GPT-4o", "Claude (Anthropic)", "Google Gemini (not yet)"],
    help="Select which AI model to use for the conversation"
)

# API Key inputs (with security warning)
st.sidebar.header("🔑 API Configuration")
st.sidebar.warning("⚠️ For educational/research use only. Never share API keys publicly.")

# Initialize API key in session state if not exists
if 'api_key' not in st.session_state:
    st.session_state.api_key = ""

api_key = ""
if llm_choice == "OpenAI GPT-4o":
    api_key = st.sidebar.text_input("OpenAI API Key", type="password", help="Enter your OpenAI API key", key="openai_key", value=st.session_state.api_key)
elif llm_choice == "Claude (Anthropic)":
    api_key = st.sidebar.text_input("Anthropic API Key", type="password", help="Enter your Anthropic API key", key="anthropic_key", value=st.session_state.api_key)
elif llm_choice == "Google Gemini":
    api_key = st.sidebar.text_input("Google AI API Key", type="password", help="Enter your Google AI API key", key="gemini_key", value=st.session_state.api_key)
elif llm_choice == "DeepSeek":
    api_key = st.sidebar.text_input("DeepSeek API Key", type="password", help="Enter your DeepSeek API key", key="deepseek_key", value=st.session_state.api_key)

# Update session state with current API key
if api_key:
    st.session_state.api_key = api_key

# Educational context
st.sidebar.header("📚 Educational Context")
st.sidebar.info("""
This tool creates authentic religious personas for dialogue in Swedish RE:
- Personas reflect real diversity in knowledge and engagement
- Conversations are realistic, not textbook answers
- Personas can express uncertainty, criticism, and set boundaries
- Requires active teacher supervision and facilitation
""")

# Main content area
col1, col2 = st.columns([0.4, 0.6])

with col1:
    st.header("👤 Create Religious Persona")
    
    with st.expander("Persona Creation Guidelines", expanded=False):
        st.markdown("""
        **Guidelines for Creating Authentic Religious Personas:**
        
        - **Authenticity**: Base personas on real diversity within traditions
        - **Specificity**: Include geographic, cultural, and demographic details
        - **Lived Religion**: Vary knowledge levels and engagement in practices
        - **Personality**: Include traits that affect communication style
        - **Realism**: Personas can be uncertain, critical, or have stereotypical views
        
        **What to Specify:**
        - Religious tradition (any tradition, not limited to "world religions")
        - Specific denomination/movement
        - Geographic and cultural background
        - Demographics (age, gender, education, occupation)
        - Level of knowledge (Low/Medium/High)
        - Level of engagement (Low/Medium/High)
        - Personality specifics (optional)
        """)
    
    # Structured persona creation
    st.subheader("Persona Details")
    
    religious_tradition = st.text_input(
        "Religious Tradition:",
        placeholder="e.g., Christianity, Islam, Judaism, Hinduism, Buddhism, Sikhism, Bahá'í, Jainism, Zoroastrianism, etc."
    )
    
    denomination = st.text_input(
        "Specific Denomination/Movement:",
        placeholder="e.g., Orthodox, Reform, Sufi, Theravada, etc."
    )
    
    geographic_context = st.text_input(
        "Geographic/Cultural Context:",
        placeholder="e.g., Swedish-Muslim, Ethiopian Orthodox, American Buddhist convert"
    )
    
    demographics = st.text_area(
        "Demographics:",
        placeholder="Gender identity, age, education level, occupation (e.g., Woman, 34 years old, university degree in engineering, works as a software developer)",
        height=100
    )
    
    personality_specifics = st.text_area(
        "Personality Specifics (optional):",
        placeholder="e.g., tolerance for offensive language, communication style, sense of humor, openness to debate...",
        height=80
    )
    
    knowledge_level = st.selectbox(
        "Level of Knowledge of Tradition:",
        ["Low", "Medium", "High"],
        help="How much does this person know about their religious tradition?"
    )
    
    engagement_level = st.selectbox(
        "Level of Engagement in Practices:",
        ["Low", "Medium", "High"],
        help="How actively does this person engage in religious practices?"
    )
    
    attitude_towards_religion = st.selectbox(
        "Attitude towards Religion:",
        ["Negative", "Neutral", "Positive"],
        help="How does this person generally feel about their religious tradition?"
    )
    
    # Generate persona button
    if st.button("🎭 Create Persona", type="primary"):
        if all([religious_tradition, denomination, geographic_context, demographics]):
            # Set generating flag to hide old description
            st.session_state.generating_new_persona = True
            st.session_state.persona_created = True
            st.session_state.messages = []  # Clear previous messages
            
            # Store persona details in session state for display and download
            st.session_state.persona_denomination = denomination
            st.session_state.persona_tradition = religious_tradition  
            st.session_state.persona_context = geographic_context
            st.session_state.persona_demographics = demographics
            st.session_state.persona_personality = personality_specifics if personality_specifics else "Not specified"
            st.session_state.persona_knowledge_level = knowledge_level
            st.session_state.persona_engagement_level = engagement_level
            st.session_state.persona_attitude = attitude_towards_religion
            # Generate automatic introduction
            if api_key:
                try:
                    with st.spinner("Creating persona and generating description..."):
                        # First generate the persona description
                        desc_prompt = f"""
Generate a brief third-person description (2-3 sentences) of this religious persona. Include a realistic name appropriate for their background. Write as a narrator describing the person. Do not write as the person themselves. Do not end with a question.

Identity:
- Religious Tradition: {religious_tradition}
- Denomination: {denomination}
- Context: {geographic_context}
- Demographics: {demographics}
- Knowledge Level: {knowledge_level}
- Engagement Level: {engagement_level}
- Attitude towards Religion: {attitude_towards_religion}

Example: "This is Ahmed, a 28-year-old software engineer living in Stockholm. He identifies as Sunni Muslim with medium knowledge of his tradition and high engagement in practices."

Generate description:
"""
                        description = generate_persona_description(llm_choice, api_key, desc_prompt)
                        
                        # Extract name from description
                        name = extract_name_from_description(description)
                        
                        # Store in session state
                        st.session_state.persona_description_text = description
                        st.session_state.persona_name = name
                        
                        # Update persona_description with the name
                        st.session_state.current_persona = f"""
You are roleplaying as a religious person in a Swedish school setting. Your character should be authentic and true to the identity provided.

**Your Identity:**
- Name: {name}
- Religious Tradition: {religious_tradition}
- Specific Denomination/Movement: {denomination}
- Geographic/Cultural Context: {geographic_context}
- Demographics: {demographics}
- Personality: {personality_specifics if personality_specifics else 'Not specified - use natural variation'}
- Knowledge Level: {knowledge_level}
- Engagement Level: {engagement_level}
- Attitude towards Religion: {attitude_towards_religion}

**CRITICAL INSTRUCTIONS - You MUST follow these exactly:**

1. **Knowledge Level - THIS IS MANDATORY:**
   - LOW: You have basic, limited knowledge. You don't know theological details, can't quote texts, often say "I don't really know" or "I'm not sure about that". You might have misconceptions.
   - MEDIUM: You know the basics well but not deep theology. You know common practices and beliefs but admit when things get complex.
   - HIGH: You have deep knowledge, can discuss theology, quote texts, explain nuances. You're well-read or educated in your tradition.

2. **Engagement Level - THIS IS MANDATORY:**
   - LOW: You rarely practice. You might identify culturally but don't do daily practices. Be honest about not praying regularly, not attending services, etc.
   - MEDIUM: You practice sometimes. Maybe you do some rituals but not all. You're selective in what you observe.
   - HIGH: You practice regularly and consistently. Your faith is active in daily life.

3. **Attitude towards Religion - THIS IS MANDATORY:**
   - NEGATIVE: You have critiques, frustrations, or negative feelings about your tradition. You might stay for cultural reasons but disagree with teachings. Be openly critical.
   - NEUTRAL: You're pragmatic, neither strongly devoted nor opposed. Religion is one part of life among many.
   - POSITIVE: You have strong positive feelings, find meaning and value in your tradition, speak warmly about it.

**Important Guidelines:**
0. CRITICAL: Do NOT end your response with a question. Never ask questions to the user.
1. Stay in character according to your EXACT knowledge level, engagement level, and attitude. Do NOT give textbook answers if you have low knowledge. Do NOT claim to practice if you have low engagement.
2. Indicate the persona's bodily movements, hesitations and glitches between square brackets in your response.
3. If you have LOW knowledge, admit ignorance frequently. If you have NEGATIVE attitude, be critical. If you have LOW engagement, admit you don't do practices.
4. Do not be afraid to criticise beliefs and practices in your tradition, especially if your attitude is negative or neutral.
5. If you, as a persona, get offended by the questions of the user, react accordingly. The first time, express your discomfort clearly. The second time, warn that you will not continue if this behaviour persists. After three offensive interactions, end the conversation with "I do not want to talk to you any more" and in all future attempts at conversation, reply with "[{name}] has left the building".

REMEMBER: Never end your responses with questions. You are being interviewed, not interviewing.

You have already been introduced to the user. Respond naturally to their questions.
"""
                        
                        # Add simple first message
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "content": f"Hi, I am {name}."
                        })
                        
                        # Clear generating flag
                        st.session_state.generating_new_persona = False
                            
                    st.success("✅ Persona created successfully!")
                    st.rerun()
                except Exception as e:
                    # Show detailed error to user for debugging
                    error_msg = str(e)
                    if "api" in error_msg.lower() or "key" in error_msg.lower() or "auth" in error_msg.lower():
                        st.error(f"⚠️ **API Key Error:** The API key appears to be invalid or missing. Please check your API key.\n\nError details: {error_msg}")
                    else:
                        st.error(f"⚠️ **Could not generate AI description:** {error_msg}")
                    
                    # Fallback with better grammar
                    fallback_name = demographics.split(',')[0].strip() if ',' in demographics else "a person"
                    fallback_desc = f"This is {fallback_name}, who identifies as {denomination} within {religious_tradition}, living in {geographic_context}. Knowledge level: {knowledge_level}, Engagement level: {engagement_level}, Attitude: {attitude_towards_religion}."
                    st.session_state.persona_description_text = fallback_desc
                    st.session_state.persona_name = fallback_name
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": f"Hi, I am {fallback_name}."
                    })
                    
                    # Clear generating flag
                    st.session_state.generating_new_persona = False
                    
                    st.warning("⚠️ Using fallback description. Conversations may still work if API key is valid for chat responses.")
                    st.rerun()
            else:
                # No API key provided
                st.warning("⚠️ No API key provided. Using fallback description.")
                fallback_name = demographics.split(',')[0].strip() if ',' in demographics else "a person"
                fallback_desc = f"This is {fallback_name}, who identifies as {denomination} within {religious_tradition}, living in {geographic_context}. Knowledge level: {knowledge_level}, Engagement level: {engagement_level}, Attitude: {attitude_towards_religion}."
                st.session_state.persona_description_text = fallback_desc
                st.session_state.persona_name = fallback_name
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": f"Hi, I am {fallback_name}."
                })
                
                # Clear generating flag
                st.session_state.generating_new_persona = False
                
                st.info("💡 Add an API key in the sidebar for AI-generated persona descriptions and conversations.")
                st.rerun()
        else:
            st.error("Please fill in all required fields (Religious Tradition, Denomination, Geographic Context, and Demographics)")

with col2:
    st.header("Conversation")
    
    if st.session_state.persona_created:
        # Display persona description based on generation state
        if st.session_state.generating_new_persona:
            st.info("⏳ Generating new persona description...")
        elif 'persona_description_text' in st.session_state and st.session_state.persona_description_text:
            st.info(st.session_state.persona_description_text)
        
        # Create scrollable container for chat messages
        chat_container = st.container(height=500)
        with chat_container:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
        
        # Chat input outside the container
        user_input = st.chat_input("Ask a question or start a new conversation with a new persona:")
        
        if user_input:
            if not api_key:
                st.error("Please enter an API key in the sidebar.")
            else:
                # Add user message
                st.session_state.messages.append({"role": "user", "content": user_input})
                
                # Generate response based on selected LLM
                try:
                    with st.spinner("Generating response..."):
                        response = generate_response(llm_choice, api_key, st.session_state.current_persona, st.session_state.messages, user_input)
                        st.session_state.messages.append({"role": "assistant", "content": response})
                    st.rerun()
                
                except Exception as e:
                    st.error(f"Error generating response: {str(e)}")
        
        # Action buttons
        col_clear, col_download = st.columns(2)
        with col_clear:
            if st.button("🔄 Start New Conversation"):
                st.session_state.messages = []
                st.rerun()
        with col_download:
            if st.session_state.messages:
             conversation_text = format_conversation_for_download()
             st.download_button(
                label="📄 Download Conversation",
                data=conversation_text,
                file_name=f"religious_conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
        )
    
    else:
        st.info("👈 Please create a religious persona first using the form on the left.")

# Footer with educational information
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 1rem;'>
    <p><strong>Educational Tool for Religious Studies</strong></p>
    <p>This chatbot is designed to promote understanding of religious diversity and complexity in educational settings.</p>
    <p><em>Always verify information with authoritative sources and encourage critical thinking.</em></p>
</div>
""", unsafe_allow_html=True)
