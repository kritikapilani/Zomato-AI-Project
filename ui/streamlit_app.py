import datetime
import logging
import os
import sys
from typing import Any

import httpx
import streamlit as st

# Add workspace root to sys.path so app modules are discoverable
current_dir = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.abspath(os.path.join(current_dir, ".."))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

from app.config import get_settings
from app.models.preferences import BudgetTier, UserPreferences
from app.models.response import Recommendation, RecommendationResponse
from app.services.dataset_loader import get_dataset_loader
from app.services.orchestrator import RecommendationOrchestrator

logger = logging.getLogger(__name__)

# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="Zomato AI Dining Concierge",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Custom Styling (Zomato-inspired Dark / Modern Theme) ---
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

h1, h2, h3, h4, h5, h6 {
    font-family: 'Outfit', sans-serif;
    font-weight: 700;
}

/* App Header & Hero Banner */
.hero-container {
    background: linear-gradient(135deg, #E23744 0%, #B81D2A 100%);
    padding: 2.2rem 2.5rem;
    border-radius: 16px;
    color: white;
    margin-bottom: 2rem;
    box-shadow: 0 12px 30px rgba(226, 55, 68, 0.25);
}

.hero-title {
    font-size: 2.3rem;
    font-weight: 700;
    margin: 0 0 0.4rem 0;
    color: #ffffff;
    display: flex;
    align-items: center;
    gap: 0.6rem;
}

.hero-subtitle {
    font-size: 1.05rem;
    color: rgba(255, 255, 255, 0.9);
    margin: 0;
    max-width: 800px;
    line-height: 1.5;
}

/* Status Pill */
.status-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    background: rgba(0, 0, 0, 0.25);
    padding: 0.35rem 0.85rem;
    border-radius: 20px;
    font-size: 0.82rem;
    margin-top: 1rem;
    color: #ffffff;
}

.status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background-color: #2ED573;
}

/* Restaurant Recommendation Cards */
.restaurant-card {
    background: #181C24;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    padding: 1.5rem;
    margin-bottom: 1.4rem;
    transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}

.restaurant-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.4);
    border-color: rgba(226, 55, 68, 0.4);
}

.card-header-flex {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1rem;
    margin-bottom: 0.8rem;
}

.restaurant-name {
    font-size: 1.4rem;
    font-weight: 700;
    color: #FFFFFF;
    margin: 0;
}

.rank-badge {
    background: #E23744;
    color: white;
    font-size: 0.75rem;
    font-weight: 700;
    padding: 0.25rem 0.65rem;
    border-radius: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.meta-row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 1rem;
}

.rating-badge {
    background: #24963F;
    color: white;
    font-weight: 600;
    font-size: 0.88rem;
    padding: 0.22rem 0.6rem;
    border-radius: 6px;
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
}

.cost-tag {
    color: #A0AEC0;
    font-size: 0.92rem;
    font-weight: 500;
}

.cuisine-pill {
    background: rgba(255, 255, 255, 0.06);
    color: #CBD5E0;
    font-size: 0.8rem;
    padding: 0.2rem 0.6rem;
    border-radius: 12px;
}

.ai-reasoning-box {
    background: rgba(226, 55, 68, 0.08);
    border-left: 3px solid #E23744;
    border-radius: 0 8px 8px 0;
    padding: 0.85rem 1rem;
    margin-top: 0.75rem;
}

.ai-reasoning-title {
    font-size: 0.78rem;
    text-transform: uppercase;
    font-weight: 700;
    color: #E23744;
    letter-spacing: 0.6px;
    margin-bottom: 0.3rem;
    display: flex;
    align-items: center;
    gap: 0.35rem;
}

.ai-reasoning-text {
    font-size: 0.94rem;
    color: #E2E8F0;
    margin: 0;
    line-height: 1.45;
}

.summary-card {
    background: linear-gradient(135deg, rgba(30, 36, 48, 0.9) 0%, rgba(24, 28, 36, 0.9) 100%);
    border: 1px solid rgba(226, 55, 68, 0.25);
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 1.8rem;
}

.summary-title {
    font-size: 0.85rem;
    text-transform: uppercase;
    color: #E23744;
    font-weight: 700;
    letter-spacing: 0.5px;
    margin-bottom: 0.4rem;
}

.summary-body {
    font-size: 1.05rem;
    color: #F7FAFC;
    font-weight: 500;
    line-height: 1.5;
    margin: 0;
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# --- Helper to Fetch Data & Query Recommendations ---
@st.cache_resource
def get_cached_dataset_info() -> dict[str, Any]:
    """Retrieve dataset status from local loader."""
    try:
        loader = get_dataset_loader()
        if not loader.is_loaded:
            loader.load()
        return loader.get_status()
    except Exception as e:
        logger.error("Error checking dataset status: %s", e)
        return {"is_loaded": False, "row_count": 0, "locations_count": 0}


def fetch_recommendations(preferences: UserPreferences) -> RecommendationResponse:
    """
    Fetch recommendations using FastAPI HTTP endpoint if available;
    transparently falls back to in-process RecommendationOrchestrator.
    """
    api_url = "http://127.0.0.1:8000/api/v1/recommendations"
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(api_url, json=preferences.model_dump())
            if resp.status_code == 200:
                data = resp.json()
                return RecommendationResponse(**data)
    except Exception:
        # Fallback to direct in-process orchestrator
        logger.info("FastAPI backend not running at %s. Using in-process orchestrator.", api_url)

    # In-process execution
    settings = get_settings()
    groq_client = None
    if settings.groq_api_key.strip():
        try:
            from app.services.groq_client import GroqLLMClient

            groq_client = GroqLLMClient(settings)
        except Exception:
            groq_client = None

    orchestrator = RecommendationOrchestrator(
        settings=settings,
        groq_client=groq_client,
    )
    return orchestrator.recommend(preferences)


# --- Popular Bangalore Locations & Cuisines ---
POPULAR_LOCATIONS = [
    "Indiranagar",
    "Koramangala",
    "Whitefield",
    "Jayanagar",
    "MG Road",
    "Brigade Road",
    "HSR Layout",
    "BTM",
    "Bellandur",
    "Banashankari",
    "Malleshwaram",
    "Church Street",
    "Residency Road",
    "Electronic City",
    "Frazer Town",
    "Other (Custom Location)",
]

POPULAR_CUISINES = [
    "North Indian",
    "South Indian",
    "Italian",
    "Chinese",
    "Continental",
    "Cafe",
    "Biryani",
    "Burger",
    "Desserts",
    "Fast Food",
    "Street Food",
    "Asian",
    "Pizza",
    "Other (Custom Cuisine)",
]


# --- Main Application Layout ---
def main():
    dataset_info = get_cached_dataset_info()
    row_count = dataset_info.get("row_count", 12519)
    loc_count = dataset_info.get("locations_count", 93)

    settings = get_settings()
    has_groq = bool(settings.groq_api_key.strip())

    # Hero Banner
    st.markdown(
        f"""
        <div class="hero-container">
            <h1 class="hero-title">🍽️ Zomato AI Dining Concierge</h1>
            <p class="hero-subtitle">
                Personalized restaurant discovery powered by structured retrieval and LLM reasoning.
                Get curated dining suggestions with personalized AI explanations.
            </p>
            <div class="status-pill">
                <span class="status-dot"></span>
                <span><strong>{row_count:,}</strong> Bangalore restaurants indexed across <strong>{loc_count}</strong> localities | AI: <strong>{'Groq LLaMA 3.3 Active' if has_groq else 'Intelligent Fallback Engine'}</strong></span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --- Sidebar Controls ---
    with st.sidebar:
        st.header("🎯 Your Dining Preferences")
        st.markdown("Customize your dining criteria below:")

        # 1. Location
        loc_choice = st.selectbox(
            "📍 Location / Locality",
            options=POPULAR_LOCATIONS,
            index=0,
            help="Select a neighborhood in Bangalore or choose Other to enter your own.",
        )
        if loc_choice == "Other (Custom Location)":
            location = st.text_input("Enter Locality / Area", value="Indiranagar").strip()
        else:
            location = loc_choice

        # 2. Cuisine
        cuisine_choice = st.selectbox(
            "🍲 Preferred Cuisine",
            options=POPULAR_CUISINES,
            index=2,  # Italian
            help="Select preferred cuisine or choose Other to specify custom dishes.",
        )
        if cuisine_choice == "Other (Custom Cuisine)":
            cuisine = st.text_input("Enter Cuisine (e.g. Sushi, Mediterranean)", value="Italian").strip()
        else:
            cuisine = cuisine_choice

        # 3. Budget Tier
        budget_options: list[BudgetTier] = ["low", "medium", "high"]
        budget_labels = {
            "low": "Low (≤ ₹500 for two)",
            "medium": "Medium (₹500 - ₹1,500)",
            "high": "High (> ₹1,500 for two)",
        }
        budget = st.radio(
            "💰 Budget Tier",
            options=budget_options,
            format_func=lambda x: budget_labels[x],
            index=1,  # medium
            help="Estimated dining cost for two people.",
        )

        # 4. Minimum Rating
        min_rating = st.slider(
            "⭐ Minimum Rating",
            min_value=0.0,
            max_value=5.0,
            value=3.8,
            step=0.1,
            help="Restaurants below this rating will be excluded (or relaxed if too few matches).",
        )

        # 5. Top K
        top_k = st.slider(
            "🔢 Number of Recommendations",
            min_value=1,
            max_value=10,
            value=5,
            help="How many top restaurant suggestions you want to see.",
        )

        # 6. Additional Free-Text Preferences
        st.markdown("**✨ Special Preferences (Optional)**")
        additional_preferences = st.text_area(
            "Vibe, ambiance, dietary needs, or features:",
            placeholder="e.g. outdoor seating, quick service, romantic date, live music",
            help="Tell the AI any specific vibes or needs to rank your options.",
        ).strip() or None

        submit_btn = st.button("✨ Get Recommendations", type="primary", use_container_width=True)

    # --- Main Screen Content ---
    if submit_btn or "last_response" in st.session_state:
        if submit_btn:
            # Build UserPreferences
            try:
                prefs = UserPreferences(
                    location=location,
                    budget=budget,
                    cuisine=cuisine,
                    min_rating=min_rating,
                    additional_preferences=additional_preferences,
                    top_k=top_k,
                )
            except Exception as e:
                st.error(f"Invalid input: {e}")
                return

            with st.spinner("🔍 Filtering candidates and generating AI recommendations..."):
                response = fetch_recommendations(prefs)
                st.session_state["last_response"] = response
                st.session_state["last_prefs"] = prefs
        else:
            response = st.session_state["last_response"]
            prefs = st.session_state.get("last_prefs")

        # Display Relaxation Warning if occurred
        relaxation = response.metadata.get("relaxation_applied", [])
        if relaxation:
            st.info(
                f"💡 **Search Expanded:** We slightly relaxed criteria ({', '.join(relaxation)}) "
                f"to ensure you get the best available dining options in {prefs.location if prefs else 'the area'}."
            )

        # Executive Summary Card
        if response.summary:
            st.markdown(
                f"""
                <div class="summary-card">
                    <div class="summary-title">🤖 AI Concierge Overview</div>
                    <p class="summary-body">{response.summary}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Empty State
        if not response.recommendations:
            st.warning(
                f"⚠️ No restaurants found matching your exact criteria in **{prefs.location if prefs else 'this area'}**.\n\n"
                "**Tips to find more spots:**\n"
                "- Try popular nearby Bangalore dining hubs like *Indiranagar*, *Koramangala*, or *Whitefield*.\n"
                "- Lower the minimum rating threshold (e.g. to 3.5).\n"
                "- Broaden your cuisine preference (e.g. Continental or Cafe)."
            )
            return

        # Render Recommendation Cards
        st.subheader(f"🏆 Top {len(response.recommendations)} Curated Dining Picks")

        for idx, rec in enumerate(response.recommendations, start=1):
            rating_display = f"★ {rec.rating:.1f}" if rec.rating > 0 else "NEW"
            cost_display = f"₹{rec.estimated_cost:,} for two" if rec.estimated_cost > 0 else "Cost not listed"

            # Split cuisine into tag pills
            cuisine_tags = [c.strip() for c in rec.cuisine.split(",") if c.strip()]
            cuisine_pills_html = "".join([f'<span class="cuisine-pill">{c}</span>' for c in cuisine_tags[:4]])

            st.markdown(
                f"""
                <div class="restaurant-card">
                    <div class="card-header-flex">
                        <div>
                            <h3 class="restaurant-name">{rec.name}</h3>
                        </div>
                        <span class="rank-badge">#{idx} Pick</span>
                    </div>
                    <div class="meta-row">
                        <span class="rating-badge">{rating_display}</span>
                        <span class="cost-tag">💵 {cost_display}</span>
                        {cuisine_pills_html}
                    </div>
                    <div class="ai-reasoning-box">
                        <div class="ai-reasoning-title">✨ Why You'll Love It</div>
                        <p class="ai-reasoning-text">{rec.explanation}</p>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Telemetry Drawer
        with st.expander("📊 Technical Execution Details & Telemetry", expanded=False):
            meta = response.metadata
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Latency", f"{meta.get('latency_ms', 0)} ms")
            with col2:
                st.metric("Candidates Considered", meta.get("candidates_considered", 0))
            with col3:
                st.metric("Total Matches", meta.get("total_matching", 0))
            with col4:
                st.metric("Engine", meta.get("source", "N/A").upper())

            st.json(meta)

    else:
        # Initial Landing State
        st.info("👈 Use the controls on the left to set your dining preferences and click **'Get Recommendations'** to begin!")

        st.markdown("### 🌟 Popular Dining Hubs in Bangalore")
        colA, colB, colC = st.columns(3)
        with colA:
            st.markdown("#### 🍸 Indiranagar & MG Road\nTrendy cafes, craft microbreweries, rooftop bars, and fine dining.")
        with colB:
            st.markdown("#### 🍔 Koramangala & HSR\nYouthful dining scenes, artisan burger joints, vibrant desserts, and street food.")
        with colC:
            st.markdown("#### 🍲 Whitefield & Bellandur\nGlobal cuisines, family-friendly casual diners, and luxury hotel buffets.")


if __name__ == "__main__":
    main()
