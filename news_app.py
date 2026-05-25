import streamlit as st
import requests
from datetime import datetime
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

st.set_page_config(
    page_title="AI News Analyst",
    page_icon="📰",
    layout="wide"
)

st.title("📰 AI News Analyst")
st.write(f"Live news updated as of {datetime.now().strftime('%d %B %Y, %I:%M %p')}")

NEWS_API_KEY  = st.secrets["NEWS_API_KEY"]
RAPIDAPI_KEY  = st.secrets["RAPIDAPI_KEY"]

# ── API functions ─────────────────────────────────────────────
@st.cache_data(ttl=1800)
def fetch_news(category, country='in'):
    keywords = {
        'technology':    'technology OR AI OR software OR gadgets',
        'business':      'business OR economy OR market OR finance OR startup',
        'sports':        'sports OR cricket OR football OR IPL OR Olympics',
        'health':        'health OR medical OR medicine OR fitness',
        'science':       'science OR space OR NASA OR research OR discovery',
        'entertainment': 'entertainment OR movies OR bollywood OR netflix OR music'
    }
    query = keywords.get(category, category)
    if country == 'in':
        query += ' OR India'
    elif country == 'us':
        query += ' OR USA OR America'
    elif country == 'gb':
        query += ' OR UK OR Britain'
    url = (
        f"https://newsapi.org/v2/everything?"
        f"q={query}&language=en&sortBy=publishedAt"
        f"&pageSize=10&apiKey={NEWS_API_KEY}"
    )
    response = requests.get(url)
    data = response.json()
    return data.get('articles', [])

@st.cache_data(ttl=1800)
def fetch_search(query):
    url = (
        f"https://newsapi.org/v2/everything?"
        f"q={query}&language=en&sortBy=publishedAt"
        f"&pageSize=10&apiKey={NEWS_API_KEY}"
    )
    response = requests.get(url)
    data = response.json()
    return data.get('articles', [])

@st.cache_data(ttl=60)
def fetch_cricket():
    url = "https://cricbuzz-cricket.p.rapidapi.com/matches/v1/live"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "cricbuzz-cricket.p.rapidapi.com"
    }
    try:
        response = requests.get(url, headers=headers)
        return response.json()
    except:
        return {}

def show_articles(articles, max_count=6):
    valid = [a for a in articles
             if a['title'] and a['title'] != '[Removed]']
    if not valid:
        return []
    cols = st.columns(2)
    for i, article in enumerate(valid[:max_count]):
        with cols[i % 2]:
            with st.container(border=True):
                st.markdown(f"**{article['title']}**")
                if article.get('description'):
                    st.write(article['description'][:150] + "...")
                col1, col2 = st.columns(2)
                with col1:
                    if article.get('source', {}).get('name'):
                        st.caption(f"📰 {article['source']['name']}")
                with col2:
                    if article.get('url'):
                        st.markdown(f"[Read more →]({article['url']})")
    return valid

# ── Session state ─────────────────────────────────────────────
if 'news_messages' not in st.session_state:
    st.session_state.news_messages = []
if 'active_search' not in st.session_state:
    st.session_state.active_search = ""

# ── Sidebar ───────────────────────────────────────────────────
st.sidebar.header("Settings")
country = st.sidebar.selectbox(
    "Country",
    [('India', 'in'), ('USA', 'us'), ('UK', 'gb')],
    format_func=lambda x: x[0]
)
selected_country = country[1]

categories = ['technology', 'business', 'sports',
              'entertainment', 'health', 'science']
selected_categories = st.sidebar.multiselect(
    "Categories", categories,
    default=['technology', 'business', 'sports']
)

st.sidebar.divider()
st.sidebar.subheader("🔍 Search any topic")
search_input = st.sidebar.text_input(
    "Type any topic",
    placeholder="e.g. IPL 2026, Sensex, Modi..."
)
if st.sidebar.button("Search"):
    st.session_state.active_search = search_input
    st.session_state.news_messages = []

st.sidebar.divider()
if st.sidebar.button("🔄 Refresh everything"):
    st.cache_data.clear()
    st.session_state.active_search = ""
    st.session_state.news_messages = []
    st.rerun()

# ── Live Cricket ──────────────────────────────────────────────
st.subheader("🏏 Live Cricket Scores")

cricket_data = fetch_cricket()
matches      = cricket_data.get('typeMatches', [])
cricket_text = ""

if not matches:
    st.info("No live matches right now.")
else:
    for match_type in matches:
        series_list = match_type.get('seriesMatches', [])
        for series in series_list:
            series_data = series.get('seriesAdWrapper', {})
            if not series_data:
                continue
            series_name  = series_data.get('seriesName', '')
            matches_list = series_data.get('matches', [])
            if not matches_list:
                continue

            st.markdown(f"**{series_name}**")
            cols = st.columns(2)
            for i, match in enumerate(matches_list[:4]):
                match_info = match.get('matchInfo', {})
                team1      = match_info.get('team1', {}).get('teamSName', '')
                team2      = match_info.get('team2', {}).get('teamSName', '')
                status     = match_info.get('status', '')
                match_desc = match_info.get('matchDesc', '')

                cricket_text += f"{series_name}: {team1} vs {team2} — {status}. "

                with cols[i % 2]:
                    with st.container(border=True):
                        st.markdown(f"**{team1} vs {team2}**")
                        st.caption(match_desc)
                        live_keywords = ['live', 'need', 'opt', 'batting', 'bowling']
                        if any(k in status.lower() for k in live_keywords):
                            st.success(f"🔴 LIVE: {status}")
                        elif 'won' in status.lower():
                            st.info(f"✅ {status}")
                        else:
                            st.warning(f"⏳ {status}")

st.divider()

# ── Build all_text ────────────────────────────────────────────
all_text = cricket_text

# ── Search results ────────────────────────────────────────────
if st.session_state.active_search:
    q = st.session_state.active_search
    st.subheader(f"🔍 Search results: '{q}'")
    search_articles = fetch_search(q)
    valid = show_articles(search_articles)
    if not valid:
        st.warning(f"No results found for '{q}'")
    else:
        for a in valid:
            all_text += f"[SEARCH:{q.upper()}] {a['title']}. "
            if a.get('description'):
                all_text += f"{a['description']} "
    st.divider()

# ── Category news ─────────────────────────────────────────────
with st.spinner("Fetching latest news..."):
    for cat in selected_categories:
        articles = fetch_news(cat, selected_country)
        valid    = [a for a in articles
                    if a['title'] and a['title'] != '[Removed]']
        for a in valid:
            all_text += f"[{cat.upper()}] {a['title']}. "
            if a.get('description'):
                all_text += f"{a['description']} "
        if valid:
            st.subheader(f"{cat.capitalize()} news")
            show_articles(articles)
            st.divider()

# ── AI Chat ───────────────────────────────────────────────────
st.subheader("💬 Ask AI about today's news & cricket")

llm = ChatGroq(
    api_key=st.secrets["GROQ_API_KEY"],
    model_name="llama-3.3-70b-versatile"
)

system_prompt = f"""
You are an expert news analyst and cricket commentator.
You have access to live cricket scores and today's news.
Today's date: {datetime.now().strftime('%d %B %Y')}
Country: {country[0]}

Live cricket scores and today's headlines:
{all_text[:5000]}

Answer questions based on this live data.
For cricket questions, give match details from the live scores.
For news questions, use the headlines.
If something is not in the data, say so honestly.
"""

for msg in st.session_state.news_messages:
    with st.chat_message(msg['role']):
        st.write(msg['content'])

question = st.chat_input("Ask about news or cricket scores...")

if question:
    st.session_state.news_messages.append(
        {'role': 'user', 'content': question}
    )
    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):
        with st.spinner("Analysing..."):
            response = llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=question)
            ])
            answer = response.content
            st.write(answer)

    st.session_state.news_messages.append(
        {'role': 'assistant', 'content': answer}
    )

# ── Footer ────────────────────────────────────────────────────
st.divider()
st.caption(
    "🏏 Cricket scores update every 60 seconds · "
    "📰 News updates every 30 minutes · "
    "Powered by Cricbuzz + NewsAPI + Groq LLaMA 3.3"
)