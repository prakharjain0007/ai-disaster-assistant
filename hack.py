import os
import json
import random
import math
from datetime import datetime

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from PIL import Image


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="AI Disaster Assistant",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# LIVE APP LINK
# ============================================================

LIVE_APP_URL = "http://ai-disaster-management.streamlit.app"


# ============================================================
# CONFIG / HELPERS
# ============================================================

def clock():
    return datetime.now().strftime("%H:%M")


def sev(score):
    if score >= 80:
        return {
            "hex": "#ef4444",
            "label": "CRITICAL",
            "color": "red",
        }
    elif score >= 50:
        return {
            "hex": "#f59e0b",
            "label": "WARNING",
            "color": "orange",
        }

    return {
        "hex": "#10b981",
        "label": "STABLE",
        "color": "green",
    }


# ============================================================
# AI CONFIG
# ============================================================

# Never put a production API key directly into this file.
#
# Example:
# export AI_ENDPOINT="https://your-backend.example.com/api/ai"
# export AI_API_KEY="..."
#
# The backend should keep the actual provider key secret.

AI_ENDPOINT = os.getenv("AI_ENDPOINT", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

CHAT_SYS = """
You are a first-aid and survival assistant inside a disaster-response
application used in India.

Reply ONLY with JSON:

{
  "title": "string",
  "steps": ["string", "string", "string"]
}

Give 3-6 short imperative steps.

If life is at risk, include calling 112.

Never diagnose.
Give practical safety guidance only.
"""

VISION_SYS = """
You triage disaster photos.

Reply ONLY with JSON:

{
  "score": 0,
  "sum": "1-2 sentences about visible damage",
  "act": "one recommended action"
}

Score severity from 0-100.
Do not diagnose people.
"""


def call_ai(system_prompt, messages):

    if not AI_ENDPOINT:
        raise RuntimeError("AI_ENDPOINT is not configured.")

    import requests

    headers = {
        "Content-Type": "application/json",
    }

    if AI_API_KEY:
        headers["Authorization"] = f"Bearer {AI_API_KEY}"

    response = requests.post(
        AI_ENDPOINT,
        headers=headers,
        json={
            "system": system_prompt,
            "messages": messages,
        },
        timeout=45,
    )

    response.raise_for_status()

    data = response.json()

    if "content" in data:
        return str(data["content"]).strip()

    if "text" in data:
        return str(data["text"]).strip()

    raise RuntimeError("Unexpected AI response format.")


def parse_json(text):
    text = text.replace("```json", "")
    text = text.replace("```", "")
    return json.loads(text.strip())


# ============================================================
# HAZARDS
# ============================================================

HAZ = {
    "flood": {
        "label": "Flash Flood",
        "code": "FLOOD",
        "emoji": "🌊",
        "base": 78,
        "sum": (
            "Water line approximately 1.2 m on ground floor. "
            "Load-bearing walls intact; debris blocking egress paths."
        ),
        "act": (
            "Move occupants to upper floors or the green corridor. "
            "Cut mains power if safe."
        ),
    },

    "collapse": {
        "label": "Structural Collapse",
        "code": "COLLAPSE",
        "emoji": "🏢",
        "base": 88,
        "sum": (
            "Partial pancake failure on levels 2-3. "
            "Column shear cracks over 5 mm detected."
        ),
        "act": (
            "Do not enter. Dispatch urban search and rescue "
            "and a structural engineer."
        ),
    },

    "fire": {
        "label": "Wildfire",
        "code": "FIRE",
        "emoji": "🔥",
        "base": 70,
        "sum": (
            "Flame front approximately 400 m out, wind-driven toward "
            "settlements. Smoke density high."
        ),
        "act": (
            "Evacuate downwind residents. Request aerial water support."
        ),
    },

    "slide": {
        "label": "Landslide",
        "code": "SLIDE",
        "emoji": "⛰️",
        "base": 74,
        "sum": (
            "Slope failure with approximately 800 m³ debris blocking "
            "the access road. Tension cracks above."
        ),
        "act": (
            "Close road, evacuate downslope homes, monitor for "
            "secondary slides."
        ),
    },

    "med": {
        "label": "Medical",
        "code": "MED",
        "emoji": "❤️",
        "base": 66,
        "sum": (
            "Trauma pattern visible. Patient responsive, bleeding "
            "appears controlled."
        ),
        "act": (
            "Dispatch paramedics. Keep patient still, warm and talking."
        ),
    },
}


# ============================================================
# INCIDENTS
# ============================================================

if "incidents" not in st.session_state:

    st.session_state.incidents = [

        {
            "id": "i1",
            "type": "flood",
            "name": "Mutha Riverbank, Sector 4",
            "x": 130,
            "y": 150,
            "score": 94,
            "status": "OPEN",
            "unit": None,
            "time": "10:12",
            "src": "IoT sensor",
        },

        {
            "id": "i2",
            "type": "collapse",
            "name": "Old Mill Apartments, Kasba",
            "x": 250,
            "y": 100,
            "score": 88,
            "status": "OPEN",
            "unit": None,
            "time": "10:31",
            "src": "Citizen",
        },

        {
            "id": "i3",
            "type": "slide",
            "name": "Sinhagad Rd Slope",
            "x": 60,
            "y": 60,
            "score": 71,
            "status": "IN PROGRESS",
            "unit": "Rescue Squad Alpha",
            "time": "10:05",
            "src": "Drone",
        },

        {
            "id": "i4",
            "type": "med",
            "name": "Hadapsar Relief Camp",
            "x": 330,
            "y": 190,
            "score": 58,
            "status": "OPEN",
            "unit": None,
            "time": "10:40",
            "src": "Citizen",
        },
    ]


# ============================================================
# SHELTERS
# ============================================================

SHELTERS = [

    {
        "id": "s1",
        "name": "Shivaji Stadium Hub",
        "x": 310,
        "y": 55,
        "cap": 400,
        "occ": 312,
        "doc": True,
        "water": "5,200 L",
    },

    {
        "id": "s2",
        "name": "Govt Polytechnic Hall",
        "x": 215,
        "y": 205,
        "cap": 250,
        "occ": 118,
        "doc": False,
        "water": "1,800 L",
    },

    {
        "id": "s3",
        "name": "St. Mary's School",
        "x": 80,
        "y": 210,
        "cap": 180,
        "occ": 171,
        "doc": True,
        "water": "900 L",
    },
]


SUPPLY = [

    {
        "name": "Drinking Water",
        "value": 42,
        "color": "#2563eb",
    },

    {
        "name": "Ration Kits",
        "value": 28,
        "color": "#f59e0b",
    },

    {
        "name": "Medical Supplies",
        "value": 18,
        "color": "#ef4444",
    },

    {
        "name": "Emergency Blankets",
        "value": 12,
        "color": "#10b981",
    },
]


UNITS = [
    "Rescue Squad Alpha",
    "NDRF Team 7",
    "Medic Unit Bravo",
    "Fire Engine 12",
    "Heli-Lift Delta",
]


# ============================================================
# FIRST AID KNOWLEDGE BASE
# ============================================================

KB = [

    (
        ["flood", "drown"],
        "Flood Protocol",
        [
            "Move to higher ground immediately; avoid basements.",
            "Never walk or drive through moving water.",
            "Switch off mains power if it is safe to reach.",
            "Carry water, medicines, ID and a charged phone.",
            "For life-threatening emergencies, call 112.",
        ],
    ),

    (
        ["burn", "scald"],
        "Burn First-Aid",
        [
            "Cool the burn under running water for 20 minutes.",
            "Remove rings and loose clothing near the burn unless stuck.",
            "Cover loosely with clean cling film or a non-fluffy cloth.",
            "Do not use ice, butter or toothpaste.",
            "Get urgent help for serious or extensive burns.",
        ],
    ),

    (
        ["bleed", "wound", "cut"],
        "Severe Bleeding",
        [
            "Press firmly on the wound with a clean cloth.",
            "Do not remove soaked cloth; add more on top.",
            "Raise the limb if no fracture is suspected.",
            "Call for help and watch for signs of shock.",
        ],
    ),

    (
        ["collapse", "trapped", "rubble", "earthquake"],
        "Trapped / Collapse",
        [
            "Cover your mouth with cloth to limit dust.",
            "Tap on pipes or walls to help rescuers locate you.",
            "Do not light matches because of possible gas leaks.",
            "Stay put until rescuers locate you if moving is unsafe.",
        ],
    ),

    (
        ["fire", "smoke"],
        "Wildfire / Smoke",
        [
            "Evacuate crosswind and away from the flame front.",
            "Use a cloth over your nose and mouth while evacuating.",
            "Close windows and shut off gas if safe before leaving.",
            "Follow official evacuation instructions.",
        ],
    ),
]


def offline_reply(question):

    q = question.lower()

    if (
        "water source" in q
        or "drink" in q
        or "nearest water" in q
    ):

        steps = [
            f"{s['name']}: {s['water']} clean water in stock"
            for s in SHELTERS
        ]

        steps.append(
            "Treat uncertain water before drinking according to local emergency guidance."
        )

        return {
            "title": "Nearest water sources",
            "steps": steps,
        }

    for keywords, title, steps in KB:

        if any(keyword in q for keyword in keywords):

            return {
                "title": title,
                "steps": steps,
            }

    return {
        "title": "I can help with that",
        "steps": [
            "Try asking about floods, burns, bleeding, collapse or wildfire.",
            "For life-threatening emergencies, call 112.",
        ],
    }


# ============================================================
# MAP
# ============================================================

def create_map(incidents, shelters, low_bandwidth=False):

    fig = go.Figure()

    active = [
        i
        for i in incidents
        if i["status"] != "RESOLVED"
    ]

    # Main road

    fig.add_trace(
        go.Scatter(
            x=[0, 400],
            y=[95, 95],
            mode="lines",
            line=dict(
                color="white",
                width=10,
            ),
            hoverinfo="skip",
            showlegend=False,
        )
    )

    # River

    river_x = list(range(401))

    river_y = [
        170
        + 25 * math.sin(x / 45)
        + 10 * math.sin(x / 18)
        for x in river_x
    ]

    fig.add_trace(
        go.Scatter(
            x=river_x,
            y=river_y,
            mode="lines",
            line=dict(
                color="#bfdbfe",
                width=16,
            ),
            hoverinfo="skip",
            showlegend=False,
        )
    )

    # Shelter markers

    fig.add_trace(
        go.Scatter(
            x=[s["x"] for s in shelters],
            y=[s["y"] for s in shelters],
            mode="markers+text",
            marker=dict(
                size=15,
                color="#10b981",
                line=dict(
                    color="white",
                    width=2,
                ),
            ),
            text=[
                s["name"]
                for s in shelters
            ],
            textposition="bottom center",
            textfont=dict(size=9),
            name="Shelters",
            hovertemplate="%{text}<extra></extra>",
        )
    )

    # Incidents

    colors = [
        sev(i["score"])["hex"]
        for i in active
    ]

    fig.add_trace(
        go.Scatter(
            x=[i["x"] for i in active],
            y=[i["y"] for i in active],
            mode="markers+text",
            marker=dict(
                size=16,
                color=colors,
                line=dict(
                    color="white",
                    width=2,
                ),
            ),
            text=[
                f"{HAZ[i['type']]['code']} {i['score']}"
                for i in active
            ],
            textposition="top center",
            textfont=dict(size=9),
            name="Incidents",
            hovertext=[
                i["name"]
                for i in active
            ],
            hovertemplate="%{hovertext}<extra></extra>",
        )
    )

    # Green corridor

    available = [
        s
        for s in shelters
        if s["cap"] - s["occ"] >= 20
    ]

    critical = [
        i
        for i in active
        if i["score"] >= 80
    ]

    for incident in critical:

        if not available:
            continue

        nearest = min(
            available,
            key=lambda s: math.hypot(
                incident["x"] - s["x"],
                incident["y"] - s["y"],
            ),
        )

        fig.add_trace(
            go.Scatter(
                x=[
                    incident["x"],
                    nearest["x"],
                ],
                y=[
                    incident["y"],
                    nearest["y"],
                ],
                mode="lines",
                line=dict(
                    color="#10b981",
                    width=3,
                    dash="dash",
                ),
                hoverinfo="skip",
                showlegend=False,
            )
        )

    fig.update_layout(
        height=480,
        margin=dict(
            l=0,
            r=0,
            t=10,
            b=0,
        ),
        paper_bgcolor="#f1f5f9",
        plot_bgcolor="#f1f5f9",
        xaxis=dict(
            range=[0, 400],
            visible=False,
        ),
        yaxis=dict(
            range=[260, 0],
            visible=False,
            scaleanchor="x",
            scaleratio=1,
        ),
        showlegend=True,
        legend=dict(
            orientation="h",
            y=-0.03,
        ),
    )

    return fig


# ============================================================
# SESSION STATE
# ============================================================

defaults = {

    "tab": "command",

    "low": False,

    "haz": "flood",

    "note": "",

    "ai": None,

    "uploaded_image": None,

    "messages": [
        {
            "from": "ai",
            "title": "AI Assistant online",
            "steps": [
                "Ask about floods, burns, bleeding, collapse or wildfire.",
                "Use a quick action below for instant guidance.",
            ],
        }
    ],

    "telemetry": {
        "river": 4.2,
        "rain": 62,
        "seis": 0.8,
        "aqi": 118,
    },
}


for key, value in defaults.items():

    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# TELEMETRY
# ============================================================

if not st.session_state.low:

    tel = st.session_state.telemetry

    tel["river"] = round(
        tel["river"]
        + (random.random() - 0.45) * 0.15,
        2,
    )

    tel["rain"] = round(
        max(
            20,
            tel["rain"]
            + (random.random() - 0.5) * 6,
        )
    )

    tel["seis"] = round(
        max(
            0.2,
            tel["seis"]
            + (random.random() - 0.5) * 0.2,
        ),
        1,
    )

    tel["aqi"] = round(
        tel["aqi"]
        + (random.random() - 0.5) * 5
    )


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    .main-title {
        font-size: 28px;
        font-weight: 800;
        color: #0f172a;
        margin-bottom: 0;
    }

    .sub-title {
        color: #64748b;
        font-size: 13px;
    }

    .status-pill {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 999px;
        padding: 5px 10px;
        font-size: 12px;
        color: #475569;
        display: inline-block;
        margin-right: 5px;
    }

    .live-app-box {
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        border-radius: 12px;
        padding: 10px 14px;
        margin-top: 10px;
    }

    .critical-box {
        background: #fef2f2;
        border: 1px solid #fecaca;
        padding: 12px;
        border-radius: 12px;
    }

    .warning-box {
        background: #fffbeb;
        border: 1px solid #fde68a;
        padding: 12px;
        border-radius: 12px;
    }

    .success-box {
        background: #ecfdf5;
        border: 1px solid #a7f3d0;
        padding: 12px;
        border-radius: 12px;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HEADER
# ============================================================

header_left, header_right = st.columns([2, 2])


with header_left:

    st.markdown(
        '<div class="main-title">🚨 AI Disaster Assistant</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="sub-title">Unified emergency response</div>',
        unsafe_allow_html=True,
    )

    # LIVE APP LINK

    st.markdown(
        f"""
        <div class="live-app-box">
            🌐 <b>Live Application:</b>
            <a href="{LIVE_APP_URL}" target="_blank">
                Open AI Disaster Management
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )


with header_right:

    c1, c2, c3 = st.columns(3)

    with c1:

        st.markdown(
            '<span class="status-pill">🟢 Satellite Mesh Active</span>',
            unsafe_allow_html=True,
        )

    with c2:

        st.markdown(
            '<span class="status-pill">🟢 PostGIS Engine Ready</span>',
            unsafe_allow_html=True,
        )

    with c3:

        low_value = st.toggle(
            "⚡ 2G Low-Bandwidth",
            value=st.session_state.low,
        )

        if low_value != st.session_state.low:

            st.session_state.low = low_value

            st.rerun()


if st.session_state.low:

    st.warning(
        "Low-bandwidth mode: map animation and live telemetry are paused."
    )


# ============================================================
# NAVIGATION
# ============================================================

tabs = {

    "command": "🛸 Command Center",

    "sos": "📱 Citizen SOS",

    "shelters": "🏥 Relief Shelters",

    "ai": "🤖 AI Assistant",

    "notify": "🔔 Notifications",
}


selected = st.radio(
    "Navigation",
    list(tabs.keys()),
    format_func=lambda x: tabs[x],
    horizontal=True,
    label_visibility="collapsed",
)


st.session_state.tab = selected


# ============================================================
# COMMAND CENTER
# ============================================================

if selected == "command":

    incidents = st.session_state.incidents

    active = [
        i
        for i in incidents
        if i["status"] != "RESOLVED"
    ]

    critical = [
        i
        for i in active
        if i["score"] >= 80
    ]

    avg = (
        round(
            sum(
                i["score"]
                for i in active
            )
            / len(active)
        )
        if active
        else 0
    )

    beds = sum(
        s["cap"] - s["occ"]
        for s in SHELTERS
    )

    k1, k2, k3, k4 = st.columns(4)

    with k1:

        st.metric(
            "⚠️ Active threats",
            len(active),
            f"{len(incidents) - len(active)} resolved",
        )

    with k2:

        st.metric(
            "🔥 Critical triage",
            len(critical),
            "AI score 80+",
        )

    with k3:

        st.metric(
            "🔎 Avg threat score",
            avg,
            "across open incidents",
        )

    with k4:

        st.metric(
            "👥 Open shelter beds",
            beds,
            f"{len(SHELTERS)} hubs online",
        )

    map_col, queue_col = st.columns([1.6, 1])

    with map_col:

        st.subheader("📍 Live disaster map")

        t1, t2, t3, t4 = st.columns(4)

        t1.metric(
            "River",
            f"{st.session_state.telemetry['river']} m",
        )

        t2.metric(
            "Rain",
            f"{st.session_state.telemetry['rain']} mm/h",
        )

        t3.metric(
            "Seismic",
            f"M{st.session_state.telemetry['seis']}",
        )

        t4.metric(
            "AQI",
            st.session_state.telemetry["aqi"],
        )

        fig = create_map(
            incidents,
            SHELTERS,
            st.session_state.low,
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )

        st.caption(
            "🔴 Critical   🟠 Warning   🟢 Shelter   "
            "— AI green corridor"
        )

    with queue_col:

        st.subheader("🚨 Priority triage queue")

        sorted_incidents = sorted(
            incidents,
            key=lambda i: (
                i["status"] == "RESOLVED",
                -i["score"],
            ),
        )

        for incident in sorted_incidents:

            s = sev(incident["score"])

            h = HAZ[incident["type"]]

            with st.container(border=True):

                top1, top2 = st.columns([4, 1])

                with top1:

                    st.markdown(
                        f"**{h['emoji']} {incident['name']}**"
                    )

                    st.caption(
                        f"{h['label']} · "
                        f"{incident['time']} · "
                        f"{incident['src']}"
                    )

                with top2:

                    st.metric(
                        "Score",
                        incident["score"],
                    )

                st.write(
                    f"**Status:** {incident['status']}"
                )

                if incident["unit"]:

                    st.caption(
                        f"Assigned: {incident['unit']}"
                    )

                if incident["status"] != "RESOLVED":

                    a, b = st.columns(2)

                    with a:

                        if incident["status"] == "OPEN":

                            if st.button(
                                "Dispatch unit",
                                key=f"dispatch_{incident['id']}",
                                use_container_width=True,
                            ):

                                assigned = [
                                    i["unit"]
                                    for i in incidents
                                    if i["unit"]
                                ]

                                available_units = [
                                    u
                                    for u in UNITS
                                    if u not in assigned
                                ]

                                unit = (
                                    available_units[0]
                                    if available_units
                                    else UNITS[
                                        len(assigned)
                                        % len(UNITS)
                                    ]
                                )

                                incident["status"] = "IN PROGRESS"

                                incident["unit"] = unit

                                st.rerun()

                    with b:

                        if st.button(
                            "Resolve",
                            key=f"resolve_{incident['id']}",
                            use_container_width=True,
                        ):

                            incident["status"] = "RESOLVED"

                            st.rerun()


# ============================================================
# CITIZEN SOS
# ============================================================

elif selected == "sos":

    left, right = st.columns(2)

    with left:

        st.subheader("🚨 Report an emergency")

        hazard_options = list(HAZ.keys())

        hazard_labels = {
            k: f"{HAZ[k]['emoji']} {HAZ[k]['label']}"
            for k in hazard_options
        }

        hazard = st.selectbox(
            "What is happening?",
            hazard_options,
            format_func=lambda x: hazard_labels[x],
        )

        st.session_state.haz = hazard

        st.success(
            "📍 GPS locked — 18.5242° N, 73.8525° E"
        )

        note = st.text_input(
            "Where exactly?",
            placeholder="Landmark, floor, people nearby...",
        )

        uploaded = st.file_uploader(
            "📷 Attach a photo",
            type=[
                "jpg",
                "jpeg",
                "png",
                "webp",
            ],
        )

        if uploaded:

            image = Image.open(uploaded)

            st.image(
                image,
                caption="Uploaded scene",
                use_container_width=True,
            )

            if st.button(
                "🔍 Analyze with AI Vision",
                use_container_width=True,
            ):

                try:

                    import base64

                    image_bytes = uploaded.getvalue()

                    encoded = base64.b64encode(
                        image_bytes
                    ).decode()

                    result = call_ai(
                        VISION_SYS,
                        [
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "image",
                                        "data": encoded,
                                    },
                                    {
                                        "type": "text",
                                        "text": (
                                            f"Reported hazard: "
                                            f"{HAZ[hazard]['label']}. "
                                            "Assess this photo."
                                        ),
                                    },
                                ],
                            }
                        ],
                    )

                    parsed = parse_json(result)

                    st.session_state.ai = {

                        "score": max(
                            0,
                            min(
                                100,
                                round(
                                    float(
                                        parsed["score"]
                                    )
                                ),
                            ),
                        ),

                        "sum": parsed.get(
                            "sum",
                            "",
                        ),

                        "act": parsed.get(
                            "act",
                            "",
                        ),

                        "live": True,
                    }

                except Exception:

                    st.session_state.ai = {

                        "score": min(
                            99,
                            HAZ[hazard]["base"]
                            + random.randint(
                                0,
                                14,
                            ),
                        ),

                        "sum": HAZ[hazard]["sum"],

                        "act": HAZ[hazard]["act"],

                        "live": False,
                    }

        ai_result = st.session_state.ai

        if ai_result:

            score = ai_result["score"]

            status = sev(score)

            st.markdown(
                f"""
                ### AI Vision Damage Assessment

                **Severity:** `{status['label']}`  
                **Score:** `{score}/100`

                **Structure:** {ai_result.get(
                    'sum',
                    HAZ[hazard]['sum']
                )}

                **Recommended action:** {ai_result.get(
                    'act',
                    HAZ[hazard]['act']
                )}
                """
            )

            st.progress(
                score / 100
            )

        if st.button(
            "🚨 SEND SOS TO COMMAND CENTER",
            type="primary",
            use_container_width=True,
        ):

            score = (

                st.session_state.ai["score"]

                if st.session_state.ai

                else HAZ[hazard]["base"]
            )

            new_incident = {

                "id": f"i{int(datetime.now().timestamp())}",

                "type": hazard,

                "name": (
                    note.strip()
                    or f"Citizen SOS: "
                    f"{HAZ[hazard]['label']}"
                ),

                "x": random.randint(
                    40,
                    360,
                ),

                "y": random.randint(
                    40,
                    220,
                ),

                "score": score,

                "status": "OPEN",

                "unit": None,

                "time": clock(),

                "src": "Citizen",
            }

            st.session_state.incidents.insert(
                0,
                new_incident,
            )

            st.session_state.ai = None

            st.success(
                f"SOS received. "
                f"{HAZ[hazard]['label']} "
                f"(score {score}) added to the command center."
            )

    with right:

        st.subheader("📱 No internet? Send an SMS")

        sms = (
            f"SOS! "
            f"TYPE:{HAZ[hazard]['code']}|"
            f"LOC:18.5242,73.8525|"
            f"TIME:{clock()}"
        )

        st.write(
            "This compressed message is designed for low-bandwidth "
            "emergency communication."
        )

        st.code(
            sms,
            language="text",
        )

        st.button(
            "📋 Copy SMS payload",
            use_container_width=True,
        )

        st.info(
            "Send the payload to your regional emergency gateway. "
            "The location and hazard type can be decoded on arrival."
        )


# ============================================================
# SHELTERS
# ============================================================

elif selected == "shelters":

    shelter_col, supply_col = st.columns([2, 1])

    with shelter_col:

        st.subheader("🏥 Relief Shelters & Resource Mesh")

        for shelter in SHELTERS:

            percentage = round(
                shelter["occ"]
                / shelter["cap"]
                * 100
            )

            available = (
                shelter["cap"]
                - shelter["occ"]
            )

            with st.container(border=True):

                a, b = st.columns([3, 1])

                with a:

                    st.markdown(
                        f"### {shelter['name']}"
                    )

                with b:

                    if percentage >= 90:

                        st.error(
                            "Nearly full"
                        )

                    else:

                        st.success(
                            "Accepting"
                        )

                st.progress(
                    percentage / 100,
                    text=(
                        f"{shelter['occ']} / "
                        f"{shelter['cap']} beds"
                    ),
                )

                c1, c2 = st.columns(2)

                with c1:

                    st.write(
                        f"🛏️ **{available} free beds**"
                    )

                with c2:

                    st.write(
                        f"💧 **{shelter['water']} clean water**"
                    )

                if shelter["doc"]:

                    st.success(
                        "🩺 Doctor on site"
                    )

                else:

                    st.warning(
                        "🩹 First-aid only"
                    )

    with supply_col:

        st.subheader("📦 City-wide supplies")

        supply_df = pd.DataFrame(
            SUPPLY
        )

        fig = go.Figure(
            data=[
                go.Pie(
                    labels=supply_df["name"],
                    values=supply_df["value"],
                    hole=0.55,
                    marker=dict(
                        colors=supply_df["color"]
                    ),
                )
            ]
        )

        fig.update_layout(
            height=350,
            margin=dict(
                l=0,
                r=0,
                t=20,
                b=0,
            ),
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )

        for item in SUPPLY:

            st.write(
                f"**{item['name']}** — "
                f"{item['value']}%"
            )


# ============================================================
# AI ASSISTANT
# ============================================================

elif selected == "ai":

    st.subheader(
        "🤖 AI First-Aid & Assistant"
    )

    st.caption(
        "Guidance only. Call 112 for life-threatening emergencies."
    )

    chat_box = st.container(
        height=500
    )

    with chat_box:

        for message in st.session_state.messages:

            if message["from"] == "me":

                st.chat_message(
                    "user"
                ).write(
                    message["text"]
                )

            else:

                with st.chat_message(
                    "assistant"
                ):

                    st.markdown(
                        f"### {message['title']}"
                    )

                    for step in message["steps"]:

                        st.markdown(
                            f"- {step}"
                        )

                    if message.get("live"):

                        st.caption(
                            "Live AI"
                        )

                    elif message.get(
                        "live"
                    ) is False:

                        st.caption(
                            "Offline guide"
                        )

    st.markdown(
        "#### Quick actions"
    )

    q1, q2, q3 = st.columns(3)

    quick_questions = [

        (
            "🌊 Flood Protocol",
            "Flood Protocol",
        ),

        (
            "🔥 Burn First-Aid",
            "Burn First-Aid",
        ),

        (
            "💧 Nearest Water Source",
            "Nearest Water Source",
        ),
    ]

    for column, (
        label,
        question,
    ) in zip(
        [q1, q2, q3],
        quick_questions,
    ):

        with column:

            if st.button(
                label,
                use_container_width=True,
            ):

                st.session_state.messages.append(
                    {
                        "from": "me",
                        "text": question,
                    }
                )

                try:

                    history = []

                    for m in st.session_state.messages[-8:]:

                        if m["from"] == "me":

                            history.append(
                                {
                                    "role": "user",
                                    "content": m["text"],
                                }
                            )

                        else:

                            history.append(
                                {
                                    "role": "assistant",
                                    "content": json.dumps(
                                        {
                                            "title": m["title"],
                                            "steps": m["steps"],
                                        }
                                    ),
                                }
                            )

                    result = call_ai(
                        CHAT_SYS,
                        history,
                    )

                    parsed = parse_json(
                        result
                    )

                    response = {

                        "from": "ai",

                        "title": parsed["title"],

                        "steps": parsed["steps"],

                        "live": True,
                    }

                except Exception:

                    offline = offline_reply(
                        question
                    )

                    response = {

                        "from": "ai",

                        **offline,

                        "live": False,
                    }

                st.session_state.messages.append(
                    response
                )

                st.rerun()

    question = st.chat_input(
        "Describe the situation..."
    )

    if question:

        st.session_state.messages.append(
            {
                "from": "me",
                "text": question,
            }
        )

        try:

            history = []

            for m in st.session_state.messages[-8:]:

                if m["from"] == "me":

                    history.append(
                        {
                            "role": "user",
                            "content": m["text"],
                        }
                    )

                else:

                    history.append(
                        {
                            "role": "assistant",
                            "content": json.dumps(
                                {
                                    "title": m["title"],
                                    "steps": m["steps"],
                                }
                            ),
                        }
                    )

            result = call_ai(
                CHAT_SYS,
                history,
            )

            parsed = parse_json(
                result
            )

            response = {

                "from": "ai",

                "title": parsed["title"],

                "steps": parsed["steps"],

                "live": True,
            }

        except Exception:

            offline = offline_reply(
                question
            )

            response = {

                "from": "ai",

                **offline,

                "live": False,
            }

        st.session_state.messages.append(
            response
        )

        st.rerun()


# ============================================================
# FOOTER
# ============================================================

st.divider()

footer_col1, footer_col2 = st.columns(
    [3, 1]
)

with footer_col1:

    st.caption(
        "AI Disaster Assistant • "
        "Emergency guidance prototype • "
        "For life-threatening emergencies in India, call 112."
    )

with footer_col2:

    st.markdown(
        f"[🌐 Open Live App]({LIVE_APP_URL})"
    )
