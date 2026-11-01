import os
import re
import time
import httpx
from dotenv import load_dotenv
from gtts import gTTS
from google import genai
from google.genai import types

from tools import (
    LIVE_API_TRACE,
    compute_crop_stress_and_irrigation,
    execute_autonomous_supply_swarm,
    fetch_live_agro_telemetry,
    optimize_smart_grid_and_water_allocation,
    resolve_location_gps,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

http_client = httpx.Client(trust_env=False, headers={"Connection": "close"})
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
    http_options=types.HttpOptions(
        httpx_client=http_client,
        timeout=45000,
        retry_options=types.HttpRetryOptions(attempts=1),
    ),
)

MODEL_POOL = [
    "gemini-3.5-flash-lite",
    "gemini-3.6-flash",
    "gemini-3.8-flash",
    "gemini-3.1-flash-lite",
]

LATEST_TELEMETRY_STORE = {}

STATE_LANGUAGE_MAP = {
    "andhra pradesh": ("Telugu", "te"),
    "telangana": ("Telugu", "te"),
    "maharashtra": ("Marathi", "mr"),
    "goa": ("Marathi", "mr"),
    "tamil nadu": ("Tamil", "ta"),
    "puducherry": ("Tamil", "ta"),
    "pondicherry": ("Tamil", "ta"),
    "karnataka": ("Kannada", "kn"),
    "kerala": ("Malayalam", "ml"),
    "lakshadweep": ("Malayalam", "ml"),
    "west bengal": ("Bengali", "bn"),
    "tripura": ("Bengali", "bn"),
    "gujarat": ("Gujarati", "gu"),
    "dadra": ("Gujarati", "gu"),
    "daman": ("Gujarati", "gu"),
    "punjab": ("Punjabi", "pa"),
    "odisha": ("Odia", "or"),
    "orissa": ("Odia", "or"),
    "assam": ("Assamese", "as"),
    "jammu": ("Urdu", "ur"),
    "kashmir": ("Urdu", "ur"),
    "rajasthan": ("Hindi", "hi"),
    "uttar pradesh": ("Hindi", "hi"),
    "madhya pradesh": ("Hindi", "hi"),
    "bihar": ("Hindi", "hi"),
    "haryana": ("Hindi", "hi"),
    "delhi": ("Hindi", "hi"),
    "himachal pradesh": ("Hindi", "hi"),
    "uttarakhand": ("Hindi", "hi"),
    "jharkhand": ("Hindi", "hi"),
    "chhattisgarh": ("Hindi", "hi"),
    "chandigarh": ("Hindi", "hi"),
}


def detect_languages_for_state(state_name: str) -> dict:
    clean_state = (state_name or "").strip().lower()
    local_lang, local_code = ("Hindi", "hi")

    for key, (lang_name, lang_code) in STATE_LANGUAGE_MAP.items():
        if key in clean_state:
            local_lang, local_code = lang_name, lang_code
            break

    if local_lang != "Hindi":
        active_languages = [
            {"role": "Local State Language", "name": local_lang, "code": local_code, "tag": "LOCAL"},
            {"role": "National Link Language", "name": "Hindi", "code": "hi", "tag": "HINDI"},
            {"role": "Global / Technical Language", "name": "English", "code": "en", "tag": "ENGLISH"},
        ]
    else:
        active_languages = [
            {"role": "Local State & National Language", "name": "Hindi", "code": "hi", "tag": "LOCAL"},
            {"role": "Global / Technical Language", "name": "English", "code": "en", "tag": "ENGLISH"},
        ]

    return {
        "detected_state": state_name or "India",
        "local_language": local_lang,
        "local_code": local_code,
        "active_languages": active_languages,
    }


# ---------------- 4 AGENT TOOLS MAPPED TO THE 4 THEME 2 PROBLEMS ----------------
def tool_resolve_location_gps(location_name: str) -> dict:
    """[Problem 1] Resolves Indian city/village GPS coordinates and auto-detects state language."""
    res = resolve_location_gps(location_name)
    lang_routing = detect_languages_for_state(res.get("state_or_region", ""))
    res["language_routing"] = lang_routing
    LATEST_TELEMETRY_STORE["gps"] = res
    LATEST_TELEMETRY_STORE["language_routing"] = lang_routing
    return res


def tool_fetch_live_agro_telemetry(
    latitude: float,
    longitude: float,
    rain_override_mm: float = 0.0,
    temp_override_c: float = 0.0,
) -> dict:
    """[Problem 2] Fetches satellite root-zone soil moisture, 7-day forecast, and 24-hour solar radiation."""
    res = fetch_live_agro_telemetry(latitude, longitude, rain_override_mm, temp_override_c)
    LATEST_TELEMETRY_STORE["telemetry"] = res
    return res


def tool_compute_crop_stress_and_irrigation(
    crop_name: str,
    root_soil_moisture_m3: float,
    forecast_7d_rain_mm: float,
    forecast_7d_et0_mm: float,
    peak_temp_c: float,
    farm_acres: float = 2.5,
    pump_hp: float = 5.0,
) -> dict:
    """[Problem 1 & 2] Computes FAO-56 water balance, micro-climate yield protection (Quintals & INR), and pump runtime."""
    res = compute_crop_stress_and_irrigation(
        crop_name, root_soil_moisture_m3, forecast_7d_rain_mm, forecast_7d_et0_mm, peak_temp_c, farm_acres, pump_hp
    )
    LATEST_TELEMETRY_STORE["agronomy"] = res
    return res


def tool_smart_grid_and_logistics_swarm(crop_name: str, farm_acres: float = 2.5, pump_hp: float = 5.0) -> dict:
    """[Problem 3 & 4] Executes Smart Grid Solar PV Load Controller AND OSRM Autonomous Supply Chain Logistics Swarm."""
    gps = LATEST_TELEMETRY_STORE.get("gps", {})
    telemetry = LATEST_TELEMETRY_STORE.get("telemetry", {})
    agronomy = LATEST_TELEMETRY_STORE.get("agronomy", {})

    grid_res = optimize_smart_grid_and_water_allocation(
        hourly_times_24h=telemetry.get("hourly_times_24h", []),
        hourly_solar_w_m2=telemetry.get("hourly_solar_radiation_w_m2", []),
        hourly_temp_24h_c=telemetry.get("hourly_temp_24h_c", []),
        required_pump_runtime_hours_7d=agronomy.get("required_pump_runtime_hours_7d", 0.0),
        pump_hp=pump_hp,
    )
    LATEST_TELEMETRY_STORE["smart_grid"] = grid_res

    swarm_res = execute_autonomous_supply_swarm(
        origin_city=gps.get("resolved_name", "Village"),
        origin_lat=float(gps.get("latitude", 16.8147)),
        origin_lon=float(gps.get("longitude", 81.5272)),
        crop_name=crop_name,
        forecast_7d_rain_mm=float(telemetry.get("forecast_7d_total_rain_mm", 0.0)),
        root_soil_moisture_m3=float(telemetry.get("root_zone_soil_moisture_3_9cm_m3_m3", 0.25)),
        baseline_yield_quintals=float(agronomy.get("baseline_farm_yield_quintals", 40.0)),
    )
    LATEST_TELEMETRY_STORE["logistics_swarm"] = swarm_res

    return {
        "smart_grid_summary": {
            "solar_coverage_pct": grid_res["solar_microgrid_coverage_pct"],
            "optimal_solar_hours": grid_res["optimal_solar_dispatch_windows"],
            "transformer_lockout_hours": grid_res["transformer_lockout_windows"],
            "grid_kwh_saved": grid_res["grid_electricity_saved_7d_kwh"],
        },
        "logistics_swarm_summary": {
            "dispatch_id": swarm_res["dispatch_id"],
            "destination_hub": swarm_res["selected_hub_name"],
            "highway_distance_km": swarm_res["highway_distance_km"],
            "eta_minutes": swarm_res["estimated_transit_minutes"],
            "dispatch_mode": swarm_res["dispatch_mode"],
            "cargo_manifest": swarm_res["cargo_manifest"],
        },
    }


def _ensure_all_4_pillars_executed(
    location: str,
    crop: str,
    farm_acres: float,
    pump_hp: float,
    rain_override_mm: float,
    temp_override_c: float,
):
    """Self-healing guard: ensures all 4 Theme 2 tools have live data populated even if LLM abbreviates tool calls."""
    if "gps" not in LATEST_TELEMETRY_STORE:
        tool_resolve_location_gps(location)
    gps = LATEST_TELEMETRY_STORE["gps"]

    if "telemetry" not in LATEST_TELEMETRY_STORE:
        tool_fetch_live_agro_telemetry(
            float(gps.get("latitude", 16.8147)),
            float(gps.get("longitude", 81.5272)),
            rain_override_mm,
            temp_override_c,
        )
    t = LATEST_TELEMETRY_STORE["telemetry"]

    if "agronomy" not in LATEST_TELEMETRY_STORE:
        tool_compute_crop_stress_and_irrigation(
            crop,
            float(t.get("root_zone_soil_moisture_3_9cm_m3_m3", 0.25)),
            float(t.get("forecast_7d_total_rain_mm", 0.0)),
            float(t.get("forecast_7d_fao_evapotranspiration_mm", 20.0)),
            float(t.get("forecast_7d_peak_temp_c", 30.0)),
            farm_acres,
            pump_hp,
        )

    if "smart_grid" not in LATEST_TELEMETRY_STORE or "logistics_swarm" not in LATEST_TELEMETRY_STORE:
        tool_smart_grid_and_logistics_swarm(crop, farm_acres, pump_hp)


def generate_voice_mp3(text: str, lang_name: str, lang_code: str, city_slug: str) -> str | None:
    try:
        clean_speech = re.sub(r"[#*`_~>-]", "", text).strip()
        if not clean_speech:
            return None
        filename = f"voice_{city_slug}_{lang_name.lower()}.mp3"
        output_path = os.path.join(BASE_DIR, filename)
        tts_code = lang_code if lang_code in ["te", "hi", "mr", "ta", "kn", "ml", "bn", "gu", "pa", "ur", "en"] else "hi"
        tts = gTTS(text=clean_speech, lang=tts_code, slow=False)
        tts.save(output_path)
        LIVE_API_TRACE.append(f"[P1 • VOICE SYNTHESIS] Generated {lang_name} audio ({filename})")
        return output_path
    except Exception:
        return None


def extract_section(text: str, tag: str) -> str:
    pattern = rf"\[{tag}_START\](.*?)\[{tag}_END\]"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else ""


def run_krishipulse_agent(
    location: str,
    crop: str,
    farm_acres: float = 2.5,
    pump_hp: float = 5.0,
    rain_override_mm: float = 0.0,
    temp_override_c: float = 0.0,
    image_part=None,
    farmer_query: str = "Execute full 4-pillar agro-climate, yield, smart-grid, and supply-chain swarm analysis.",
) -> dict:
    """Runs the unified 4-problem Theme 2 autonomous agent loop."""
    LIVE_API_TRACE.clear()
    LATEST_TELEMETRY_STORE.clear()

    system_instruction = (
        "You are KrishiPulse AI, an autonomous 4-Pillar Command Agent for Theme 2 (Climate, Resource Infrastructure & Global Supply Resilience). "
        "Execute all four tools in exact sequence before writing your response:\n"
        "1. `tool_resolve_location_gps` (Problem 1: Geocoding & Auto-State Language Router)\n"
        "2. `tool_fetch_live_agro_telemetry` (Problem 2: Satellite Soil Moisture & Solar Radiation Telemetry)\n"
        "3. `tool_compute_crop_stress_and_irrigation` (Problem 1 & 2: FAO-56 Water Balance & Yield Revenue Protection)\n"
        "4. `tool_smart_grid_and_logistics_swarm` (Problem 3: Smart Grid Solar Load Controller & Problem 4: OSRM Highway Logistics Swarm)\n\n"
        "CRITIC RULE: Cite exact tool numbers across all 4 pillars: GPS coordinates, root-zone soil moisture, 7-day rain, "
        "Quintals & INR yield protected, Smart Grid solar PV hours, and OSRM highway dispatch ID & distance (km).\n\n"
        "Structure your output using these exact 4 tagged blocks:\n\n"
        "[TECHNICAL_REPORT_START]\n"
        "(Write a structured Markdown report with 4 sections: 1. Multilingual Resource & Irrigation Plan, "
        "2. Micro-Climate & Yield Protection Forecast, 3. Smart Grid & Solar Pump Dispatch Schedule, "
        "4. Autonomous Supply Chain & Emergency Logistics Swarm)\n"
        "[TECHNICAL_REPORT_END]\n\n"
        "[LOCAL_ADVISORY_START]\n"
        "(4-sentence farmer voice advisory in the auto-detected local state language script covering irrigation, yield, solar pump hours, and mandi/relief logistics)\n"
        "[LOCAL_ADVISORY_END]\n\n"
        "[HINDI_ADVISORY_START]\n"
        "(4-sentence farmer voice advisory in Hindi Devanagari script covering irrigation, yield, solar pump hours, and mandi/relief logistics)\n"
        "[HINDI_ADVISORY_END]\n\n"
        "[ENGLISH_ADVISORY_START]\n"
        "(4-sentence farmer voice advisory in clear English covering irrigation, yield, solar pump hours, and mandi/relief logistics)\n"
        "[ENGLISH_ADVISORY_END]"
    )

    user_payload = [
        f"Location: {location}\n"
        f"Crop: {crop}\n"
        f"Farm Size: {farm_acres} Acres | Pump Rating: {pump_hp} HP\n"
        f"Climate Shock Overrides -> Rain: +{rain_override_mm} mm, Temp: +{temp_override_c} °C\n"
        f"Mission Objective: {farmer_query}"
    ]
    if image_part:
        user_payload.append(image_part)

    last_error = None
    for model_name in MODEL_POOL:
        try:
            LIVE_API_TRACE.clear()
            LATEST_TELEMETRY_STORE.clear()
            start_time = time.perf_counter()
            print(f"\n[ROUTER] Launching Unified 4-Pillar Agent on {model_name}...")

            chat = client.chats.create(
                model=model_name,
                config=types.GenerateContentConfig(
                    tools=[
                        tool_resolve_location_gps,
                        tool_fetch_live_agro_telemetry,
                        tool_compute_crop_stress_and_irrigation,
                        tool_smart_grid_and_logistics_swarm,
                    ],
                    system_instruction=system_instruction,
                ),
            )

            response = chat.send_message(user_payload)
            _ensure_all_4_pillars_executed(
                location, crop, farm_acres, pump_hp, rain_override_mm, temp_override_c
            )
            full_text = response.text or ""
            total_latency_ms = round((time.perf_counter() - start_time) * 1000, 1)

            report_md = extract_section(full_text, "TECHNICAL_REPORT") or full_text
            local_msg = extract_section(full_text, "LOCAL_ADVISORY")
            hindi_msg = extract_section(full_text, "HINDI_ADVISORY")
            english_msg = extract_section(full_text, "ENGLISH_ADVISORY")

            routing = LATEST_TELEMETRY_STORE.get(
                "language_routing",
                detect_languages_for_state(
                    LATEST_TELEMETRY_STORE.get("gps", {}).get("state_or_region", "India")
                ),
            )
            city_slug = re.sub(r"[^a-z0-9]", "", location.lower()) or "city"

            multilingual_outputs = []
            for lang_item in routing["active_languages"]:
                tag = lang_item["tag"]
                if tag == "LOCAL":
                    msg_text = local_msg or hindi_msg or english_msg
                elif tag == "HINDI":
                    msg_text = hindi_msg or local_msg
                else:
                    msg_text = english_msg or report_md[:400]

                mp3_path = generate_voice_mp3(
                    text=msg_text,
                    lang_name=lang_item["name"],
                    lang_code=lang_item["code"],
                    city_slug=city_slug,
                )
                multilingual_outputs.append(
                    {
                        "role": lang_item["role"],
                        "language_name": lang_item["name"],
                        "language_code": lang_item["code"],
                        "message_text": msg_text,
                        "audio_path": mp3_path,
                    }
                )

            return {
                "status": "success",
                "model_used": model_name,
                "total_latency_ms": total_latency_ms,
                "report_markdown": report_md,
                "language_routing": routing,
                "multilingual_advisories": multilingual_outputs,
                "execution_trace": list(LIVE_API_TRACE),
                "raw_data": dict(LATEST_TELEMETRY_STORE),
            }

        except Exception as err:
            last_error = err
            print(f" -> {model_name} busy ({type(err).__name__}), failing over...")
            time.sleep(1)

    raise RuntimeError(f"All models busy. Last error: {last_error}")