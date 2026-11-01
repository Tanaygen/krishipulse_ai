import json
import os
import re
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image
from agent import run_krishipulse_agent

try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

st.set_page_config(
    page_title="KrishiPulse AI // Orbital & Mobile Command Console",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==============================================================================
# ADAPTIVE WATCHDOG & URL QUERY PARAMETER ROUTER
# ==============================================================================
if "ui_mode" not in st.session_state:
    st.session_state["ui_mode"] = "full_3d"
if "fallback_reason" not in st.session_state:
    st.session_state["fallback_reason"] = None

qp_mode = st.query_params.get("ui_mode", "")
qp_reason = st.query_params.get("reason", "")
if qp_mode == "turbo":
    st.session_state["ui_mode"] = "turbo_3d_vector"
    if qp_reason:
        st.session_state["fallback_reason"] = qp_reason
elif qp_mode == "full":
    st.session_state["ui_mode"] = "full_3d"
    st.session_state["fallback_reason"] = None


def inject_watchdog_and_device_probe(timeout_ms: int = 2800):
    """Automatically switches to 3D Vector Turbo Mode ONLY if page load exceeds timeout_ms or 2G Data Saver is on."""
    if st.session_state["ui_mode"] == "turbo_3d_vector":
        return

    probe_html = f"""
    <script>
    (function() {{
        try {{
            const parentUrl = new URL(window.parent.location.href);
            if (parentUrl.searchParams.get("probed") === "1") return;

            let triggerTurbo = false;
            let reason = "";

            const conn = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
            if (conn) {{
                if (conn.saveData === true) {{
                    triggerTurbo = true;
                    reason = "Mobile_Data_Saver_Active";
                }} else if (conn.effectiveType === "slow-2g" || conn.effectiveType === "2g") {{
                    triggerTurbo = true;
                    reason = "2G_Network_Detected";
                }} else if (conn.rtt && conn.rtt > 500) {{
                    triggerTurbo = true;
                    reason = "High_Latency_RTT_" + conn.rtt + "ms";
                }}
            }}

            const navEntries = window.parent.performance.getEntriesByType("navigation");
            if (!triggerTurbo && navEntries && navEntries.length > 0) {{
                const domLoadMs = navEntries[0].domContentLoadedEventEnd - navEntries[0].startTime;
                if (domLoadMs > {timeout_ms}) {{
                    triggerTurbo = true;
                    reason = "Watchdog_Timeout_" + Math.round(domLoadMs) + "ms";
                }}
            }}

            if (triggerTurbo) {{
                parentUrl.searchParams.set("ui_mode", "turbo");
                parentUrl.searchParams.set("reason", reason);
                parentUrl.searchParams.set("probed", "1");
                window.parent.location.replace(parentUrl.toString());
            }}
        }} catch (err) {{
            console.log("Watchdog probe skipped:", err);
        }}
    }})();
    </script>
    """
    components.html(probe_html, height=0)


# ==============================================================================
# 3D TEXTURED ISOMETRIC SVG ENGINE (LIGHTWEIGHT VECTOR 3D FOR BOTH LAPTOP & PHONE)
# ==============================================================================
def get_3d_textured_svg(icon_type: str, size: int = 46) -> str:
    """Returns multi-layered 3D shaded & textured isometric SVGs (renders in <1ms on both phone & laptop)."""
    svgs = {
        "satellite": f"""
        <svg width="{size}" height="{size}" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
            <defs>
                <filter id="glow_sat" x="-20%" y="-20%" width="140%" height="140%">
                    <feDropShadow dx="0" dy="5" stdDeviation="3.5" flood-color="#000000" flood-opacity="0.65"/>
                </filter>
                <linearGradient id="gold_foil" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0%" stop-color="#fde047"/><stop offset="45%" stop-color="#eab308"/><stop offset="100%" stop-color="#713f12"/>
                </linearGradient>
                <linearGradient id="titanium_body" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0%" stop-color="#f8fafc"/><stop offset="50%" stop-color="#64748b"/><stop offset="100%" stop-color="#0f172a"/>
                </linearGradient>
                <linearGradient id="pv_wing" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#38bdf8"/><stop offset="50%" stop-color="#0284c7"/><stop offset="100%" stop-color="#082f49"/>
                </linearGradient>
                <radialGradient id="lens_orb" cx="35%" cy="35%" r="65%">
                    <stop offset="0%" stop-color="#a7f3d0"/><stop offset="55%" stop-color="#10b981"/><stop offset="100%" stop-color="#064e3b"/>
                </radialGradient>
            </defs>
            <g filter="url(#glow_sat)">
                <polygon points="4,22 20,14 24,22 8,30" fill="url(#pv_wing)" stroke="#7dd3fc" stroke-width="0.9"/>
                <polygon points="40,42 56,34 60,42 44,50" fill="url(#pv_wing)" stroke="#7dd3fc" stroke-width="0.9"/>
                <polygon points="32,14 44,21 32,28 20,21" fill="url(#titanium_body)" stroke="#cbd5e1" stroke-width="0.8"/>
                <polygon points="20,21 32,28 32,44 20,37" fill="url(#gold_foil)" stroke="#fef08a" stroke-width="0.7"/>
                <polygon points="44,21 32,28 32,44 44,37" fill="url(#titanium_body)" stroke="#475569" stroke-width="0.7"/>
                <circle cx="32" cy="34" r="5.5" fill="url(#lens_orb)" stroke="#6ee7b7" stroke-width="1"/>
                <circle cx="30" cy="32" r="1.6" fill="#ffffff" fill-opacity="0.85"/>
                <polygon points="28,44 36,44 44,60 20,60" fill="url(#lens_orb)" fill-opacity="0.28"/>
            </g>
        </svg>
        """,
        "soil_cube": f"""
        <svg width="{size}" height="{size}" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
            <defs>
                <linearGradient id="turf_top" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0%" stop-color="#4ade80"/><stop offset="55%" stop-color="#16a34a"/><stop offset="100%" stop-color="#14532d"/>
                </linearGradient>
                <linearGradient id="loam_left" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#a16207"/><stop offset="50%" stop-color="#713f12"/><stop offset="100%" stop-color="#0284c7"/>
                </linearGradient>
                <linearGradient id="loam_right" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#854d0e"/><stop offset="50%" stop-color="#422006"/><stop offset="100%" stop-color="#0369a1"/>
                </linearGradient>
            </defs>
            <polygon points="32,8 56,20 32,32 8,20" fill="url(#turf_top)" stroke="#86efac" stroke-width="0.8"/>
            <polygon points="8,20 32,32 32,56 8,44" fill="url(#loam_left)" stroke="#ca8a04" stroke-width="0.6"/>
            <polygon points="56,20 32,32 32,56 56,44" fill="url(#loam_right)" stroke="#a16207" stroke-width="0.6"/>
            <polyline points="8,34 32,46 56,34" stroke="#38bdf8" stroke-width="2" stroke-opacity="0.85"/>
        </svg>
        """,
        "yield_sphere": f"""
        <svg width="{size}" height="{size}" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
            <defs>
                <radialGradient id="orb_glass" cx="35%" cy="30%" r="70%">
                    <stop offset="0%" stop-color="#ecfeff"/><stop offset="35%" stop-color="#22d3ee"/><stop offset="75%" stop-color="#0e7490"/><stop offset="100%" stop-color="#083344"/>
                </radialGradient>
                <linearGradient id="gold_grain" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0%" stop-color="#fef08a"/><stop offset="50%" stop-color="#f59e0b"/><stop offset="100%" stop-color="#78350f"/>
                </linearGradient>
            </defs>
            <circle cx="32" cy="32" r="23" fill="url(#orb_glass)" stroke="#67e8f9" stroke-width="1.2"/>
            <polygon points="32,15 43,26 32,49 21,26" fill="url(#gold_grain)" stroke="#fef9c3" stroke-width="0.9"/>
            <ellipse cx="23" cy="21" rx="7" ry="3.5" transform="rotate(-30 23 21)" fill="#ffffff" fill-opacity="0.65"/>
        </svg>
        """,
        "solar_grid": f"""
        <svg width="{size}" height="{size}" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
            <defs>
                <radialGradient id="sun_orb" cx="40%" cy="35%" r="65%">
                    <stop offset="0%" stop-color="#fffbeb"/><stop offset="40%" stop-color="#fbbf24"/><stop offset="80%" stop-color="#d97706"/><stop offset="100%" stop-color="#78350f"/>
                </radialGradient>
                <linearGradient id="panel_3d" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0%" stop-color="#38bdf8"/><stop offset="50%" stop-color="#1d4ed8"/><stop offset="100%" stop-color="#1e1b4b"/>
                </linearGradient>
            </defs>
            <circle cx="44" cy="18" r="11" fill="url(#sun_orb)" stroke="#fde68a" stroke-width="1"/>
            <polygon points="6,38 38,26 54,42 22,54" fill="url(#panel_3d)" stroke="#93c5fd" stroke-width="1.2"/>
            <line x1="17" y1="34" x2="33" y2="50" stroke="#bae6fd" stroke-width="0.8" stroke-opacity="0.7"/>
            <line x1="28" y1="30" x2="44" y2="46" stroke="#bae6fd" stroke-width="0.8" stroke-opacity="0.7"/>
        </svg>
        """,
        "logistics_pod": f"""
        <svg width="{size}" height="{size}" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
            <defs>
                <linearGradient id="pod_top" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0%" stop-color="#e9d5ff"/><stop offset="50%" stop-color="#a855f7"/><stop offset="100%" stop-color="#581c87"/>
                </linearGradient>
                <linearGradient id="pod_side" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#9333ea"/><stop offset="100%" stop-color="#3b0764"/>
                </linearGradient>
                <linearGradient id="pod_front" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0%" stop-color="#38bdf8"/><stop offset="100%" stop-color="#0369a1"/>
                </linearGradient>
            </defs>
            <path d="M6 52 L32 58 L58 44" stroke="#22d3ee" stroke-width="2.2" stroke-dasharray="4 3"/>
            <polygon points="30,12 52,22 32,32 10,22" fill="url(#pod_top)" stroke="#f3e8ff" stroke-width="0.9"/>
            <polygon points="10,22 32,32 32,48 10,38" fill="url(#pod_side)" stroke="#c084fc" stroke-width="0.8"/>
            <polygon points="52,22 32,32 32,48 52,38" fill="url(#pod_front)" stroke="#7dd3fc" stroke-width="0.8"/>
            <circle cx="31" cy="22" r="4" fill="#34d399" stroke="#ffffff" stroke-width="1"/>
        </svg>
        """,
        "acoustic_dome": f"""
        <svg width="{size}" height="{size}" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
            <defs>
                <radialGradient id="mic_mesh" cx="35%" cy="30%" r="68%">
                    <stop offset="0%" stop-color="#f8fafc"/><stop offset="40%" stop-color="#38bdf8"/><stop offset="80%" stop-color="#0f172a"/><stop offset="100%" stop-color="#020617"/>
                </radialGradient>
                <linearGradient id="mic_body" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stop-color="#334155"/><stop offset="50%" stop-color="#94a3b8"/><stop offset="100%" stop-color="#0f172a"/>
                </linearGradient>
            </defs>
            <circle cx="32" cy="26" r="22" stroke="#22d3ee" stroke-width="1.2" stroke-opacity="0.35" stroke-dasharray="4 3"/>
            <rect x="24" y="26" width="16" height="22" rx="4" fill="url(#mic_body)" stroke="#cbd5e1" stroke-width="0.8"/>
            <circle cx="32" cy="24" r="11" fill="url(#mic_mesh)" stroke="#7dd3fc" stroke-width="1.2"/>
        </svg>
        """,
        "beacon_warn": """
        <svg width="32" height="32" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
            <defs>
                <radialGradient id="strobe_red" cx="38%" cy="35%" r="65%">
                    <stop offset="0%" stop-color="#fff1f2"/><stop offset="35%" stop-color="#fb7185"/><stop offset="75%" stop-color="#e11d48"/><stop offset="100%" stop-color="#4c0519"/>
                </radialGradient>
            </defs>
            <circle cx="24" cy="24" r="20" fill="#e11d48" fill-opacity="0.22"/>
            <circle cx="24" cy="24" r="14" fill="url(#strobe_red)" stroke="#fda4af" stroke-width="1.2"/>
        </svg>
        """,
        "beacon_ok": """
        <svg width="32" height="32" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
            <defs>
                <radialGradient id="strobe_em" cx="38%" cy="35%" r="65%">
                    <stop offset="0%" stop-color="#ecfdf5"/><stop offset="35%" stop-color="#34d399"/><stop offset="75%" stop-color="#059669"/><stop offset="100%" stop-color="#064e3b"/>
                </radialGradient>
            </defs>
            <circle cx="24" cy="24" r="20" fill="#10b981" fill-opacity="0.22"/>
            <circle cx="24" cy="24" r="14" fill="url(#strobe_em)" stroke="#6ee7b7" stroke-width="1.2"/>
        </svg>
        """,
    }
    return svgs.get(icon_type, svgs["satellite"]).strip()


def clean_emoji_text(text: str) -> str:
    return re.sub(r"[\U00010000-\U0010ffff]|[\u2600-\u27ff]", "", str(text)).strip()


# ==============================================================================
# AUTO-RESIZING, TOUCH-FRIENDLY WEBGL 3D SOIL CORE (WORKS ON PHONE & LAPTOP)
# ==============================================================================
def render_webgl_3d_soil_core(soil_m: float, soil_t: float, rain_7d: float, solar_w: float, crop_name: str):
    sat_ratio = min(1.0, max(0.05, soil_m / 0.50))
    rain_particles = min(150, int(rain_7d * 1.1)) if rain_7d > 5 else 0
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
        <style>
            body {{ margin: 0; overflow: hidden; background: #050a12; font-family: 'JetBrains Mono', monospace; touch-action: pan-y; }}
            #canvas-wrap {{
                width: 100%; height: 325px; position: relative;
                border-radius: 14px; border: 1px solid rgba(56, 189, 248, 0.38);
                background: radial-gradient(circle at 50% 35%, #0d2137 0%, #050a12 85%);
                touch-action: pan-y;
            }}
            .hud-tag {{
                position: absolute; top: 10px; left: 12px; z-index: 10;
                background: rgba(4, 10, 18, 0.86); border: 1px solid rgba(52, 211, 153, 0.45);
                border-left: 3px solid #10b981; padding: 7px 11px; border-radius: 6px;
                color: #cbd5e1; font-size: 10.5px; line-height: 1.45; pointer-events: none;
            }}
            .hud-legend {{
                position: absolute; bottom: 8px; right: 10px; z-index: 10;
                background: rgba(4, 10, 18, 0.82); border: 1px solid rgba(148, 163, 184, 0.25);
                padding: 4px 8px; border-radius: 5px; color: #94a3b8; font-size: 9.5px;
                pointer-events: none;
            }}
        </style>
    </head>
    <body>
        <div id="canvas-wrap">
            <div class="hud-tag">
                <b style="color:#34d399;">3D VOLUMETRIC SOIL CORE // WEBGL</b><br>
                CROP: {crop_name.upper()} | MOISTURE: {soil_m:.3f} m³/m³ ({int(sat_ratio*100)}%)<br>
                SOIL TEMP: {soil_t} C | PEAK SOLAR: {solar_w} W/m²
            </div>
            <div class="hud-legend">DRAG HORIZONTALLY TO ROTATE 3D CORE</div>
        </div>
        <script>
            const container = document.getElementById('canvas-wrap');
            const scene = new THREE.Scene();
            const camera = new THREE.PerspectiveCamera(40, container.clientWidth / 325, 0.1, 1000);
            camera.position.set(4.3, 3.3, 4.7);
            camera.lookAt(0, 0, 0);

            const renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: true }});
            renderer.setSize(container.clientWidth, 325);
            renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
            container.appendChild(renderer.domElement);

            function createSoilTexture(satRatio) {{
                const canvas = document.createElement('canvas');
                canvas.width = 256; canvas.height = 256;
                const ctx = canvas.getContext('2d');
                const grad = ctx.createLinearGradient(0, 0, 0, 256);
                grad.addColorStop(0.0, '#15803d');
                grad.addColorStop(0.14, '#3f2e18');
                const r = Math.round(95 * (1 - satRatio * 0.55));
                const g = Math.round(65 + satRatio * 55);
                const b = Math.round(35 + satRatio * 135);
                grad.addColorStop(0.55, `rgb(${{r}},${{g}},${{b}})`);
                grad.addColorStop(1.0, '#0369a1');
                ctx.fillStyle = grad; ctx.fillRect(0, 0, 256, 256);
                for (let i = 0; i < 3800; i++) {{
                    ctx.fillStyle = Math.random() > 0.5 ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.22)';
                    ctx.fillRect(Math.random() * 256, Math.random() * 256, 2, 2);
                }}
                ctx.strokeStyle = 'rgba(56, 189, 248, 0.78)';
                ctx.lineWidth = 3;
                ctx.beginPath(); ctx.moveTo(0, 145); ctx.lineTo(256, 145); ctx.stroke();
                return new THREE.CanvasTexture(canvas);
            }}

            const sideTex = createSoilTexture({sat_ratio});
            const mat = new THREE.MeshStandardMaterial({{ map: sideTex, roughness: 0.45, metalness: 0.15 }});
            const coreGroup = new THREE.Group();
            const cube = new THREE.Mesh(new THREE.BoxGeometry(2.1, 2.2, 2.1), mat);
            coreGroup.add(cube);

            const stemMat = new THREE.MeshStandardMaterial({{ color: 0x4ade80, roughness: 0.4 }});
            for (let x = -0.62; x <= 0.62; x += 0.62) {{
                for (let z = -0.62; z <= 0.62; z += 0.62) {{
                    const stem = new THREE.Mesh(new THREE.ConeGeometry(0.15, 0.52, 7), stemMat);
                    stem.position.set(x, 1.35, z);
                    coreGroup.add(stem);
                }}
            }}
            const edges = new THREE.EdgesGeometry(new THREE.BoxGeometry(2.18, 2.28, 2.18));
            coreGroup.add(new THREE.LineSegments(edges, new THREE.LineBasicMaterial({{ color: 0x38bdf8, transparent: true, opacity: 0.35 }})));
            scene.add(coreGroup);

            scene.add(new THREE.AmbientLight(0xffffff, 0.8));
            const dirLight = new THREE.DirectionalLight(0xfef08a, 1.35);
            dirLight.position.set(5, 8, 6);
            scene.add(dirLight);

            const rainCount = {rain_particles};
            let rainSystem;
            if (rainCount > 0) {{
                const rainGeo = new THREE.BufferGeometry();
                const pos = [];
                for (let i = 0; i < rainCount; i++) {{
                    pos.push((Math.random() - 0.5) * 4.2, Math.random() * 3.8 - 1.0, (Math.random() - 0.5) * 4.2);
                }}
                rainGeo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
                rainSystem = new THREE.Points(rainGeo, new THREE.PointsMaterial({{ color: 0x38bdf8, size: 0.06, transparent: true, opacity: 0.75 }}));
                scene.add(rainSystem);
            }}

            let isDragging = false, prevX = 0;
            container.addEventListener('pointerdown', (e) => {{ isDragging = true; prevX = e.clientX; }});
            window.addEventListener('pointerup', () => {{ isDragging = false; }});
            window.addEventListener('pointermove', (e) => {{
                if (isDragging) {{
                    coreGroup.rotation.y += (e.clientX - prevX) * 0.012;
                    prevX = e.clientX;
                }}
            }});

            new ResizeObserver(() => {{
                const w = container.clientWidth || 320;
                camera.aspect = w / 325;
                camera.updateProjectionMatrix();
                renderer.setSize(w, 325);
            }}).observe(container);

            function animate() {{
                requestAnimationFrame(animate);
                if (!isDragging) coreGroup.rotation.y += 0.005;
                if (rainSystem) {{
                    const arr = rainSystem.geometry.attributes.position.array;
                    for (let i = 1; i < arr.length; i += 3) {{
                        arr[i] -= 0.045;
                        if (arr[i] < -1.1) arr[i] = 2.5;
                    }}
                    rainSystem.geometry.attributes.position.needsUpdate = true;
                }}
                renderer.render(scene, camera);
            }}
            animate();
        </script>
    </body>
    </html>
    """
    components.html(html_code, height=335)


def render_satellite_and_corridor_hud(origin_lat: float, origin_lon: float, city_name: str, hub_lat: float, hub_lon: float, hub_name: str, road_km: float):
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <style>
            body {{ margin: 0; padding: 0; background: #04080e; font-family: 'JetBrains Mono', monospace; }}
            #map {{ width: 100%; height: 355px; border-radius: 14px; border: 1px solid rgba(56, 189, 248, 0.42); }}
            .hud-overlay {{
                position: absolute; top: 10px; left: 10px; right: 10px; max-width: 340px; z-index: 999;
                background: rgba(4, 10, 18, 0.9); border: 1px solid rgba(16, 185, 129, 0.55);
                border-left: 3px solid #10b981; padding: 8px 12px; border-radius: 6px;
                color: #6ee7b7; font-size: 10.5px; line-height: 1.45; pointer-events: none;
            }}
        </style>
    </head>
    <body>
        <div style="position:relative;">
            <div class="hud-overlay">
                <b>ESRI OPTICAL SATELLITE // OSRM VECTOR</b><br>
                ORIGIN: {city_name.upper()} ({origin_lat:.3f}N, {origin_lon:.3f}E)<br>
                HUB: {hub_name.upper()} ({road_km} KM)
            </div>
            <div id="map"></div>
        </div>
        <script>
            // scrollWheelZoom: false ensures scrolling up/down the webpage never gets trapped inside the map!
            var map = L.map('map', {{ zoomControl: true, scrollWheelZoom: false }}).setView([{origin_lat}, {origin_lon}], 8);
            L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}').addTo(map);
            L.circleMarker([{origin_lat}, {origin_lon}], {{ radius: 9, color: '#10b981', fillColor: '#34d399', fillOpacity: 0.95 }}).addTo(map);
            L.circleMarker([{hub_lat}, {hub_lon}], {{ radius: 9, color: '#38bdf8', fillColor: '#0284c7', fillOpacity: 0.95 }}).addTo(map);
            var line = L.polyline([[{origin_lat}, {origin_lon}], [{hub_lat}, {hub_lon}]], {{ color: '#38bdf8', weight: 3, dashArray: '8, 8' }}).addTo(map);
            map.fitBounds(line.getBounds(), {{ padding: [40, 40] }});
        </script>
    </body>
    </html>
    """
    components.html(html_code, height=370)


# ==============================================================================
# DUAL-DEVICE RESPONSIVE CSS (FIXED TOP SCROLL CLEARANCE FOR LAPTOP & MOBILE)
# ==============================================================================
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');

    html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif; }

    /* Translucent top Streamlit header so it never visually blocks content when scrolling up */
    header[data-testid="stHeader"] {
        background: rgba(4, 7, 12, 0.72) !important;
        backdrop-filter: blur(8px);
    }

    .stApp {
        background-color: #04070c;
        background-image:
            radial-gradient(at 12% 8%, rgba(16, 185, 129, 0.14) 0px, transparent 42%),
            radial-gradient(at 88% 15%, rgba(14, 165, 233, 0.13) 0px, transparent 45%),
            linear-gradient(rgba(148, 163, 184, 0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(148, 163, 184, 0.03) 1px, transparent 1px);
        background-size: 100% 100%, 100% 100%, 32px 32px, 32px 32px;
        color: #f8fafc;
    }

    /* 3.8rem top padding guarantees the top bar is completely visible below Streamlit's Deploy header */
    .block-container {
        padding-top: 3.8rem !important;
        padding-bottom: 3rem !important;
        max-width: 1480px;
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #060b13 0%, #09111d 100%);
        border-right: 1px solid rgba(56, 189, 248, 0.22);
    }

    .led-3d-emerald {
        display: inline-block; width: 10px; height: 10px; border-radius: 50%;
        background: radial-gradient(circle at 35% 35%, #d1fae5, #10b981 55%, #064e3b 100%);
        box-shadow: 0 0 10px #10b981; margin-right: 7px; vertical-align: middle;
    }
    .led-3d-cyan {
        display: inline-block; width: 10px; height: 10px; border-radius: 50%;
        background: radial-gradient(circle at 35% 35%, #e0f2fe, #0ea5e9 55%, #082f49 100%);
        box-shadow: 0 0 10px #0ea5e9; margin-right: 7px; vertical-align: middle;
    }
    .led-3d-amber {
        display: inline-block; width: 10px; height: 10px; border-radius: 50%;
        background: radial-gradient(circle at 35% 35%, #fef3c7, #f59e0b 55%, #78350f 100%);
        box-shadow: 0 0 10px #f59e0b; margin-right: 7px; vertical-align: middle;
    }

    .orbital-hero {
        background: linear-gradient(145deg, rgba(15, 25, 40, 0.96) 0%, rgba(7, 14, 24, 0.98) 100%);
        border: 1px solid rgba(148, 163, 184, 0.26);
        border-top: 1px solid rgba(255, 255, 255, 0.22);
        border-bottom: 3px solid #0284c7;
        border-radius: 16px;
        padding: clamp(14px, 2.2vw, 22px) clamp(16px, 2.5vw, 28px);
        margin-bottom: 14px;
        box-shadow: 0 18px 42px rgba(0, 0, 0, 0.72), inset 0 1px 0 rgba(255, 255, 255, 0.14);
    }
    .hero-flex { display: flex; align-items: center; gap: 18px; }
    .hero-main-title {
        font-size: clamp(1.22rem, 2.4vw, 1.98rem);
        font-weight: 700; margin: 0; letter-spacing: -0.02em; color: #f8fafc;
        line-height: 1.25;
    }
    .hero-subtitle {
        color: #94a3b8;
        font-size: clamp(0.78rem, 1.2vw, 0.92rem);
        margin: 5px 0 12px 0;
        line-height: 1.45;
    }
    .hud-pill-row { display: flex; flex-wrap: wrap; gap: 7px; }
    .hud-pill {
        font-family: 'JetBrains Mono', monospace;
        font-size: clamp(0.62rem, 0.9vw, 0.69rem);
        padding: 4px 10px;
        border-radius: 6px;
        background: linear-gradient(180deg, rgba(30, 41, 59, 0.92), rgba(15, 23, 42, 0.96));
        border: 1px solid rgba(148, 163, 184, 0.3);
        color: #e2e8f0;
    }

    .bento-kpi {
        position: relative;
        background: linear-gradient(165deg, #111c2d 0%, #080f1a 65%, #050911 100%);
        border: 1px solid rgba(148, 163, 184, 0.24);
        border-top: 1px solid rgba(255, 255, 255, 0.22);
        border-bottom: 3px solid #10b981;
        border-radius: 14px;
        padding: clamp(14px, 1.8vw, 18px);
        box-shadow: 0 12px 28px rgba(0, 0, 0, 0.65), inset 0 1px 0 rgba(255, 255, 255, 0.12);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        margin-bottom: 10px;
    }
    .bento-kpi:hover {
        transform: translateY(-3px);
        box-shadow: 0 18px 34px rgba(0, 0, 0, 0.8), 0 0 18px rgba(56, 189, 248, 0.16);
    }
    .bento-cyan { border-bottom-color: #0ea5e9; }
    .bento-amber { border-bottom-color: #f59e0b; }
    .bento-purple { border-bottom-color: #a855f7; }

    .bento-top-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
    .bento-serial {
        font-family: 'JetBrains Mono', monospace; font-size: 0.63rem;
        color: #64748b; letter-spacing: 0.08em;
        background: rgba(2, 6, 23, 0.75); padding: 2px 6px; border-radius: 4px;
        border: 1px solid rgba(148, 163, 184, 0.16);
    }
    .bento-label {
        font-size: clamp(0.68rem, 1vw, 0.74rem);
        text-transform: uppercase; letter-spacing: 0.07em;
        color: #94a3b8; font-weight: 600;
    }
    .bento-val {
        font-family: 'JetBrains Mono', monospace;
        font-size: clamp(1.28rem, 2vw, 1.54rem);
        font-weight: 700; color: #f8fafc; margin: 4px 0 3px 0;
    }
    .bento-sub {
        font-family: 'JetBrains Mono', monospace;
        font-size: clamp(0.68rem, 0.95vw, 0.74rem);
        color: #7dd3fc; margin-bottom: 9px;
    }
    .micro-bar-bg {
        width: 100%; height: 7px; background: #030712;
        border-radius: 999px; overflow: hidden;
        border: 1px solid rgba(148,163,184,0.15);
    }
    .micro-bar-fill { height: 100%; border-radius: 999px; }

    .telemetry-strip {
        display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 8px;
        background: linear-gradient(90deg, #091321, #0d1c2e, #091321);
        border: 1px solid rgba(148, 163, 184, 0.25);
        border-left: 4px solid #10b981;
        padding: 10px 15px; border-radius: 10px; margin: 10px 0;
        font-family: 'JetBrains Mono', monospace;
        font-size: clamp(0.68rem, 1vw, 0.77rem); color: #e2e8f0;
    }

    .studio-card {
        background: linear-gradient(160deg, #101c2e 0%, #070d17 100%);
        border: 1px solid rgba(148, 163, 184, 0.25);
        border-top: 1px solid rgba(255, 255, 255, 0.22);
        border-bottom: 3px solid #0ea5e9;
        border-radius: 14px; padding: 16px; margin-bottom: 10px;
        box-shadow: 0 12px 28px rgba(0,0,0,0.6);
    }
    .studio-role {
        font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; color: #7dd3fc;
        text-transform: uppercase; letter-spacing: 0.07em;
        background: rgba(2, 6, 23, 0.8); padding: 3px 8px; border-radius: 4px;
        border: 1px solid rgba(56, 189, 248, 0.3);
    }
    .studio-lang { font-size: 1.08rem; font-weight: 700; color: #f8fafc; margin: 6px 0; }
    .studio-body { font-size: 0.93rem; line-height: 1.58; color: #cbd5e1; }

    .hud-panel {
        background: linear-gradient(165deg, rgba(15, 23, 38, 0.9) 0%, rgba(7, 12, 21, 0.95) 100%);
        border: 1px solid rgba(148, 163, 184, 0.2);
        border-top: 1px solid rgba(255, 255, 255, 0.14);
        border-radius: 14px; padding: clamp(14px, 2vw, 20px); margin-bottom: 14px;
    }

    .section-hdr {
        font-family: 'JetBrains Mono', monospace;
        font-size: clamp(0.7rem, 1.05vw, 0.8rem);
        text-transform: uppercase; letter-spacing: 0.08em; color: #38bdf8;
        border-bottom: 1px solid rgba(56, 189, 248, 0.22);
        padding-bottom: 6px; margin-bottom: 12px; font-weight: 700;
    }

    .hud-alert-crit, .hud-alert-ok {
        display: flex; align-items: center; gap: 12px; padding: 11px 15px;
        border-radius: 10px; margin: 10px 0; font-weight: 500;
        font-size: clamp(0.8rem, 1.1vw, 0.88rem);
    }
    .hud-alert-crit {
        background: linear-gradient(90deg, rgba(136, 19, 55, 0.48) 0%, rgba(15, 23, 42, 0.95) 100%);
        border: 1px solid rgba(244, 63, 94, 0.55); border-left: 5px solid #f43f5e; color: #ffe4e6;
    }
    .hud-alert-ok {
        background: linear-gradient(90deg, rgba(6, 78, 59, 0.48) 0%, rgba(15, 23, 42, 0.95) 100%);
        border: 1px solid rgba(16, 185, 129, 0.5); border-left: 5px solid #10b981; color: #d1fae5;
    }

    div.stButton > button {
        background: linear-gradient(180deg, #132238 0%, #091220 100%);
        border: 1px solid rgba(148, 163, 184, 0.32);
        border-top: 1px solid rgba(255, 255, 255, 0.22);
        border-radius: 9px; font-family: 'JetBrains Mono', monospace;
        font-size: 0.74rem; font-weight: 600; color: #e2e8f0;
        min-height: 44px;
        box-shadow: 0 5px 12px rgba(0,0,0,0.45);
        transition: all 0.2s ease;
    }
    div.stButton > button:hover {
        border-color: #38bdf8; color: #ffffff;
        box-shadow: 0 6px 18px rgba(14, 165, 233, 0.28);
    }

    div[data-testid="stTabs"] button[role="tab"] {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        padding: 8px 14px;
        white-space: nowrap;
    }

    @media (max-width: 768px) {
        .block-container {
            padding-left: 0.65rem !important;
            padding-right: 0.65rem !important;
            padding-top: 3.4rem !important;
        }
        .hero-flex {
            flex-direction: column;
            align-items: flex-start;
            gap: 10px;
        }
        .telemetry-strip {
            flex-direction: column;
            align-items: flex-start;
            gap: 5px;
        }
        .bento-kpi {
            padding: 14px 16px;
            margin-bottom: 8px;
        }
        .studio-card {
            min-height: auto;
        }
        div[data-testid="stTabs"] div[role="tablist"] {
            overflow-x: auto !important;
            flex-wrap: nowrap !important;
            scrollbar-width: thin;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------- SESSION STATE DEFAULTS ----------------
if "loc_val" not in st.session_state:
    st.session_state["loc_val"] = "Tadepalligudem"
if "crop_val" not in st.session_state:
    st.session_state["crop_val"] = "Rice"
if "acres_val" not in st.session_state:
    st.session_state["acres_val"] = 2.5
if "hp_val" not in st.session_state:
    st.session_state["hp_val"] = 5.0

CROP_LIST = [
    "Rice", "Cotton", "Wheat", "Sugarcane", "Tomato",
    "Chilli", "Maize", "Groundnut", "Soybean", "Onion", "Turmeric"
]

# ---------------- TOP ADAPTIVE TELEMETRY & ENGINE BAR ----------------
top1, top2, top3 = st.columns([2.2, 1.1, 1.1])
with top1:
    if st.session_state["ui_mode"] == "full_3d":
        st.markdown(
            '<div style="background:#091526;border:1px solid rgba(56,189,248,0.35);padding:10px 14px;border-radius:8px;font-family:\'JetBrains Mono\',monospace;font-size:0.73rem;color:#7dd3fc;">'
            '<span class="led-3d-emerald"></span><b>RENDER ENGINE:</b> DUAL-DEVICE 3D ORBITAL + WEBGL MODE &nbsp;|&nbsp; '
            '<b>MOBILE &amp; DESKTOP READY</b></div>',
            unsafe_allow_html=True,
        )
    else:
        reason_tag = st.session_state.get("fallback_reason") or "2G_Watchdog_Turbo"
        st.markdown(
            f'<div style="background:#1e1b4b;border:1px solid #38bdf8;padding:10px 14px;border-radius:8px;font-family:\'JetBrains Mono\',monospace;font-size:0.73rem;color:#bae6fd;">'
            f'<span class="led-3d-amber"></span><b>3D VECTOR TURBO MODE ACTIVE ({reason_tag})</b> &nbsp;|&nbsp; '
            f'<b>FULL 3D CARDS KEPT • HEAVY MAPS DEFERRED (18 KB)</b></div>',
            unsafe_allow_html=True,
        )

with top2:
    if st.button("SWITCH TO 3D TURBO MODE (FAST MOBILE)", use_container_width=True):
        st.session_state["ui_mode"] = "turbo_3d_vector"
        st.session_state["fallback_reason"] = "Instant_3D_Vector_Turbo"
        st.query_params["ui_mode"] = "turbo"
        st.rerun()

with top3:
    if st.button("SWITCH TO FULL WEBGL + SATELLITE 3D", use_container_width=True):
        st.session_state["ui_mode"] = "full_3d"
        st.session_state["fallback_reason"] = None
        st.query_params["ui_mode"] = "full"
        st.rerun()

# ---------------- 3D TEXTURED HERO CHASSIS ----------------
st.markdown(
    f"""
    <div class="orbital-hero">
        <div class="hero-flex">
            <div>{get_3d_textured_svg("satellite", 60)}</div>
            <div>
                <p class="hero-main-title">
                    <span class="led-3d-emerald"></span>KrishiPulse AI // 4-Pillar Agro-Telemetry &amp; Supply Console
                </p>
                <p class="hero-subtitle">
                    Responsive Orbital Cockpit (Laptop) &amp; Touch-Native 3D Glass App (Mobile) • Live Satellite Soil • Solar Grid • OSRM Swarm
                </p>
                <div class="hud-pill-row">
                    <span class="hud-pill"><span class="led-3d-emerald"></span>P1 // AUTO-STATE VOICE</span>
                    <span class="hud-pill"><span class="led-3d-cyan"></span>P2 // 3D SOIL &amp; YIELD</span>
                    <span class="hud-pill"><span class="led-3d-emerald"></span>P3 // SOLAR W/m² GRID</span>
                    <span class="hud-pill"><span class="led-3d-cyan"></span>P4 // OSRM SUPPLY SWARM</span>
                </div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ==============================================================================
# ON-SCREEN MOBILE & DESKTOP QUICK COMMAND BAR
# ==============================================================================
quick_run = False
with st.expander("QUICK MISSION CONTROL // CHANGE VILLAGE, CROP OR FARM SIZE (MOBILE & DESKTOP)", expanded=False):
    mc1, mc2, mc3, mc4, mc5 = st.columns([1.4, 1.1, 0.9, 0.9, 1.2])
    with mc1:
        quick_loc = st.text_input("Village / Town / City:", value=st.session_state["loc_val"], key="q_loc")
    with mc2:
        quick_crop = st.selectbox("Target Crop:", CROP_LIST, index=CROP_LIST.index(st.session_state["crop_val"]), key="q_crop")
    with mc3:
        quick_acres = st.number_input("Farm Acres:", min_value=0.5, max_value=50.0, value=float(st.session_state["acres_val"]), step=0.5, key="q_ac")
    with mc4:
        quick_hp = st.selectbox("Pump HP:", [3.0, 5.0, 7.5, 10.0], index=1, key="q_hp")
    with mc5:
        st.markdown("<div style='height:27px;'></div>", unsafe_allow_html=True)
        quick_run = st.button("LAUNCH 4-PILLAR SCAN", type="primary", use_container_width=True, key="q_run_btn")

# ---------------- 1-CLICK SCENARIO PRESETS ----------------
st.markdown('<div class="section-hdr">1-CLICK TACTICAL PRESETS // INSTANT LIVE 4-PILLAR EXECUTION</div>', unsafe_allow_html=True)
sc1, sc2, sc3, sc4 = st.columns(4)

trigger_preset = False
if sc1.button("SECTOR 01 // TADEPALLIGUDEM (RICE)\nMONSOON SWARM • TELUGU + HI + EN", use_container_width=True):
    st.session_state["loc_val"] = "Tadepalligudem"
    st.session_state["crop_val"] = "Rice"
    trigger_preset = True

if sc2.button("SECTOR 02 // PUNE (COTTON)\nDECCAN GRID • MARATHI + HI + EN", use_container_width=True):
    st.session_state["loc_val"] = "Pune"
    st.session_state["crop_val"] = "Cotton"
    trigger_preset = True

if sc3.button("SECTOR 03 // THANJAVUR (RICE)\nDELTA YIELD • TAMIL + HI + EN", use_container_width=True):
    st.session_state["loc_val"] = "Thanjavur"
    st.session_state["crop_val"] = "Rice"
    trigger_preset = True

if sc4.button("SECTOR 04 // BIKANER (WHEAT)\nARID DEFICIT • HINDI + ENGLISH", use_container_width=True):
    st.session_state["loc_val"] = "Bikaner"
    st.session_state["crop_val"] = "Wheat"
    trigger_preset = True

# ---------------- SIDEBAR ADVANCED CONTROLS ----------------
with st.sidebar:
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;">'
        f'{get_3d_textured_svg("satellite", 36)}'
        f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:0.86rem;font-weight:700;color:#f8fafc;">TELEMETRY CONTROL DECK</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    location_input = st.text_input("TARGET SECTOR (VILLAGE / CITY):", value=st.session_state["loc_val"])
    crop_input = st.selectbox("CROP BIOMASS PROFILE:", CROP_LIST, index=CROP_LIST.index(st.session_state["crop_val"]))

    st.divider()
    st.markdown("##### FARM & MICRO-GRID RATING")
    farm_acres_input = st.slider("Cultivated Area (Acres):", 0.5, 25.0, float(st.session_state["acres_val"]), 0.5)
    pump_hp_input = st.selectbox("Submersible / Solar Pump (HP):", [3.0, 5.0, 7.5, 10.0], index=1)

    st.divider()
    st.markdown("##### CLIMATE PERTURBATION SIMULATOR")
    rain_shock = st.slider("Cloudburst Perturbation (+mm):", 0, 150, 0, 10)
    temp_shock = st.slider("Thermal Anomaly Spike (+C):", 0, 8, 0, 1)

    st.divider()
    st.markdown("##### OPTICAL LEAF / SOIL VISION INPUT")
    uploaded_image = st.file_uploader("Upload Field Specimen (JPG/PNG):", type=["jpg", "jpeg", "png"])

    farmer_query = st.text_area(
        "OPERATIONAL DIRECTIVE:",
        value="Execute full 4-pillar agro-climate, yield, smart-grid, and supply-chain swarm analysis.",
        height=65,
    )

    run_btn = st.button("ENGAGE 4-PILLAR AUTONOMOUS ENGINE", type="primary", use_container_width=True)

# ---------------- LIVE EXECUTION ----------------
if run_btn or trigger_preset or quick_run:
    if quick_run:
        st.session_state["loc_val"] = quick_loc
        st.session_state["crop_val"] = quick_crop
        st.session_state["acres_val"] = quick_acres
        st.session_state["hp_val"] = quick_hp
    elif run_btn:
        st.session_state["loc_val"] = location_input
        st.session_state["crop_val"] = crop_input
        st.session_state["acres_val"] = farm_acres_input
        st.session_state["hp_val"] = pump_hp_input

    image_part = None
    if uploaded_image is not None:
        try:
            image_part = Image.open(uploaded_image)
        except Exception:
            pass

    with st.status("EXECUTING 4-PILLAR ORBITAL & LOGISTICS TELEMETRY CHAIN...", expanded=True) as status_box:
        st.write(f"[STAGE 01] Resolving satellite coordinates & state language routing for {st.session_state['loc_val']}...")
        st.write("[STAGE 02] Querying Open-Meteo root-zone soil moisture (3-9 cm), FAO-56 ET0 & yield model...")
        st.write("[STAGE 03] Computing live shortwave solar irradiance (W/m²) & feeder transformer schedule...")
        st.write("[STAGE 04] Calculating OSRM highway vector to regional Agri-Hub & committing SQLite ledger...")
        try:
            st.session_state["krishi_result"] = run_krishipulse_agent(
                location=st.session_state["loc_val"].strip(),
                crop=st.session_state["crop_val"],
                farm_acres=float(st.session_state["acres_val"]),
                pump_hp=float(st.session_state["hp_val"]),
                rain_override_mm=float(rain_shock),
                temp_override_c=float(temp_shock),
                image_part=image_part,
                farmer_query=farmer_query.strip(),
            )
            status_box.update(label="TELEMETRY LOCK CONFIRMED // ALL 4 PILLARS SYNCHRONIZED", state="complete", expanded=False)
        except Exception as err:
            status_box.update(label="TELEMETRY FAULT DETECTED", state="error", expanded=True)
            st.error(f"Live Execution Error: {err}")

# ==============================================================================
# UNIFIED 3D TEXTURED DASHBOARD (ADAPTS FLUIDLY TO BOTH PHONE & LAPTOP)
# ==============================================================================
if "krishi_result" in st.session_state:
    res = st.session_state["krishi_result"]
    raw = res.get("raw_data", {})
    gps = raw.get("gps", {})
    telemetry = raw.get("telemetry", {})
    agro = raw.get("agronomy", {})
    grid = raw.get("smart_grid", {})
    swarm = raw.get("logistics_swarm", {})
    routing = res.get("language_routing", {})
    advisories = res.get("multilingual_advisories", [])

    resolved_city = gps.get("resolved_name", st.session_state["loc_val"])
    resolved_state = gps.get("state_or_region", routing.get("detected_state", "India"))
    active_lang_names = " + ".join([a["language_name"] for a in advisories])

    lat = float(gps.get("latitude", 16.8147))
    lon = float(gps.get("longitude", 81.5272))
    soil_m = float(telemetry.get("root_zone_soil_moisture_3_9cm_m3_m3", 0.0))
    soil_t = float(telemetry.get("root_zone_soil_temp_6cm_c", 26.0))
    rain_7d = float(telemetry.get("forecast_7d_total_rain_mm", 0.0))
    peak_solar_w = float(telemetry.get("peak_solar_radiation_w_m2", 0.0))
    runtime_hrs = agro.get("required_pump_runtime_hours_7d", 0.0)
    yield_saved_q = agro.get("yield_protected_by_ai_quintals", 0.0)
    rev_saved_inr = agro.get("harvest_revenue_protected_inr", 0)
    solar_cov_pct = grid.get("solar_microgrid_coverage_pct", 100.0)
    co2_saved = grid.get("carbon_emissions_avoided_kg_co2", 0.0)
    hub_name = swarm.get("selected_hub_name", "Regional Agri Hub")
    road_km = swarm.get("highway_distance_km", 0.0)
    eta_mins = swarm.get("estimated_transit_minutes", 0.0)

    st.markdown(
        f"""
        <div class="telemetry-strip">
            <span><span class="led-3d-emerald"></span><b>SECTOR:</b> {resolved_city.upper()}, {resolved_state.upper()} ({lat:.4f}N, {lon:.4f}E)</span>
            <span><b>P1 LANGUAGES:</b> {active_lang_names.upper()}</span>
            <span><b>P2 YIELD SHIELD:</b> INR {rev_saved_inr:,}</span>
            <span><b>P3 SOLAR:</b> {solar_cov_pct}%</span>
            <span><b>P4 OSRM ROUTE:</b> {road_km} KM ({swarm.get('dispatch_id', 'ACTIVE')})</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---------------- 4 BENTO KPI CARDS (ALWAYS 3D TEXTURED ON BOTH PHONE & LAPTOP) ----------------
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(
            f"""
            <div class="bento-kpi">
                <div class="bento-top-row">
                    <div>
                        <div class="bento-serial">PILLAR 01 // HYDRO-CORE</div>
                        <div class="bento-label">Root-Zone Soil Moisture</div>
                    </div>
                    {get_3d_textured_svg("soil_cube", 44)}
                </div>
                <div class="bento-val">{soil_m:.3f} m³/m³</div>
                <div class="bento-sub">Pump Run: {runtime_hrs} hrs/wk • {soil_t}°C</div>
                <div class="micro-bar-bg"><div class="micro-bar-fill" style="width:{min(100, int((soil_m/0.5)*100))}%; background:linear-gradient(90deg,#10b981,#38bdf8);"></div></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            f"""
            <div class="bento-kpi bento-cyan">
                <div class="bento-top-row">
                    <div>
                        <div class="bento-serial">PILLAR 02 // BIO-YIELD</div>
                        <div class="bento-label">Harvest Value Protected</div>
                    </div>
                    {get_3d_textured_svg("yield_sphere", 44)}
                </div>
                <div class="bento-val">INR {rev_saved_inr:,}</div>
                <div class="bento-sub">{yield_saved_q} Quintals Saved • {rain_7d:.1f}mm Rain</div>
                <div class="micro-bar-bg"><div class="micro-bar-fill" style="width:{min(100, int(agro.get('yield_stability_score_pct', 90)))}%; background:linear-gradient(90deg,#0ea5e9,#3b82f6);"></div></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with k3:
        st.markdown(
            f"""
            <div class="bento-kpi bento-amber">
                <div class="bento-top-row">
                    <div>
                        <div class="bento-serial">PILLAR 03 // MICRO-GRID</div>
                        <div class="bento-label">Solar PV Pump Share</div>
                    </div>
                    {get_3d_textured_svg("solar_grid", 44)}
                </div>
                <div class="bento-val">{solar_cov_pct}% Solar</div>
                <div class="bento-sub">Peak: {peak_solar_w} W/m² • -{co2_saved}kg CO₂</div>
                <div class="micro-bar-bg"><div class="micro-bar-fill" style="width:{int(solar_cov_pct)}%; background:linear-gradient(90deg,#f59e0b,#fde047);"></div></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with k4:
        st.markdown(
            f"""
            <div class="bento-kpi bento-purple">
                <div class="bento-top-row">
                    <div>
                        <div class="bento-serial">PILLAR 04 // OSRM SWARM</div>
                        <div class="bento-label">Highway Logistics Vector</div>
                    </div>
                    {get_3d_textured_svg("logistics_pod", 44)}
                </div>
                <div class="bento-val">{road_km} km</div>
                <div class="bento-sub">ETA: {eta_mins} mins to {hub_name[:18]}...</div>
                <div class="micro-bar-bg"><div class="micro-bar-fill" style="width:85%; background:linear-gradient(90deg,#a855f7,#ec4899);"></div></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 3D Strobe Alert Banner
    for alert in agro.get("active_risk_alerts", []):
        is_crit = any(w in alert for w in ["CRITICAL", "WATERLOGGING", "HEATWAVE"])
        cls_name = "hud-alert-crit" if is_crit else "hud-alert-ok"
        beacon_svg = get_3d_textured_svg("beacon_warn" if is_crit else "beacon_ok", 32)
        st.markdown(
            f'<div class="{cls_name}">{beacon_svg}<div><b>AUTONOMOUS TELEMETRY DIAGNOSTIC:</b> {clean_emoji_text(alert)}</div></div>',
            unsafe_allow_html=True,
        )

    # ---------------- 5 SWIPEABLE COMMAND TABS ----------------
    tab_p1, tab_p2, tab_p3, tab_p4, tab_proof = st.tabs(
        [
            f"P1 // VOICE STUDIO ({active_lang_names.upper()})",
            "P2 // 3D SOIL & YIELD ENGINE",
            "P3 // SMART SOLAR GRID",
            "P4 // OSRM SUPPLY SWARM",
            "KERNEL // LIVE JSON PROOF",
        ]
    )

    # ---------------- TAB P1: MULTILINGUAL VOICE & ACTION PLAN ----------------
    with tab_p1:
        st.markdown(
            f'<div class="section-hdr">PILLAR 01 // AUTO-ROUTED REGIONAL BROADCAST DECK — {resolved_city.upper()}, {resolved_state.upper()}</div>',
            unsafe_allow_html=True,
        )
        if advisories:
            cols = st.columns(len(advisories), gap="medium")
            for idx, adv in enumerate(advisories):
                with cols[idx]:
                    st.markdown(
                        f"""
                        <div class="studio-card">
                            <div style="display:flex;justify-content:space-between;align-items:center;">
                                <span class="studio-role">{adv['role']}</span>
                                {get_3d_textured_svg("acoustic_dome", 34)}
                            </div>
                            <div class="studio-lang">{adv['language_name']} Transducer Channel</div>
                            <div class="studio-body">{clean_emoji_text(adv['message_text'])}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    audio_path = adv.get("audio_path")
                    if audio_path and os.path.isfile(audio_path):
                        with open(audio_path, "rb") as af:
                            audio_bytes = af.read()
                        st.audio(audio_bytes, format="audio/mp3")
                        st.download_button(
                            label=f"EXPORT {adv['language_name'].upper()} AUDIO (.MP3)",
                            data=audio_bytes,
                            file_name=os.path.basename(audio_path),
                            mime="audio/mp3",
                            key=f"dl_{idx}_{adv['language_name']}",
                            use_container_width=True,
                        )

        st.markdown('<div class="hud-panel">', unsafe_allow_html=True)
        st.markdown('<div class="section-hdr">MASTER 4-PILLAR AGRONOMIC & INFRASTRUCTURE DIRECTIVE</div>', unsafe_allow_html=True)
        st.markdown(res.get("report_markdown", ""))
        st.markdown("</div>", unsafe_allow_html=True)

    # ---------------- TAB P2: 3D SOIL CORE & YIELD ENGINE ----------------
    with tab_p2:
        st.markdown('<div class="section-hdr">PILLAR 02 // 3D SOIL STRATA SIMULATION & YIELD PROTECTION ENGINE</div>', unsafe_allow_html=True)
        y1, y2, y3 = st.columns(3)
        y1.metric("Baseline Expected Farm Yield", f"{agro.get('baseline_farm_yield_quintals', 0)} Quintals", f"Mandi Rate: INR {agro.get('mandi_benchmark_inr_per_quintal', 0)}/Q")
        y2.metric("Yield Protected by AI Intervention", f"{yield_saved_q} Quintals", f"Stress Risk Mitigated: {agro.get('unmitigated_climate_yield_risk_pct', 0)}%")
        y3.metric("Total Farmer Revenue Protected", f"INR {rev_saved_inr:,}", f"Urea Washout Saved: INR {agro.get('fertilizer_washout_protection_inr', 0):,}")

        g_col, c_col = st.columns([1.05, 1.55], gap="large")
        with g_col:
            st.markdown('<div class="hud-panel">', unsafe_allow_html=True)
            st.markdown('<div class="section-hdr">3D VOLUMETRIC ROOT-ZONE SIMULATION</div>', unsafe_allow_html=True)
            if st.session_state["ui_mode"] == "full_3d":
                render_webgl_3d_soil_core(soil_m, soil_t, rain_7d, peak_solar_w, st.session_state["crop_val"])
            else:
                st.markdown(
                    f"""
                    <div style="text-align:center;padding:24px 14px;background:#07101e;border:1px solid rgba(56,189,248,0.3);border-radius:12px;">
                        {get_3d_textured_svg("soil_cube", 96)}
                        <div style="font-family:'JetBrains Mono',monospace;font-size:1.1rem;font-weight:700;margin-top:10px;color:#38bdf8;">
                            3D ISOMETRIC VECTOR CORE ({soil_m:.3f} m³/m³)
                        </div>
                        <div style="font-size:0.84rem;color:#94a3b8;margin-top:4px;">
                            6cm Soil Temp: {soil_t}°C • 7d Rain: {rain_7d:.1f} mm • Solar: {peak_solar_w} W/m²
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)

        with c_col:
            st.markdown('<div class="hud-panel">', unsafe_allow_html=True)
            st.markdown('<div class="section-hdr">7-DAY HYDRO-THERMAL TELEMETRY // PRECIPITATION VS. FAO ET0</div>', unsafe_allow_html=True)
            dates = telemetry.get("daily_dates", [])
            rain_series = telemetry.get("daily_rain_mm", [])
            et0_series = telemetry.get("daily_et0_mm", [])
            max_t_series = telemetry.get("daily_max_temp_c", [])
            if dates and len(dates) == len(rain_series):
                chart_df = pd.DataFrame(
                    {"Date": dates, "Rainfall (mm)": rain_series, "FAO ET0 (mm)": et0_series, "Peak Temp (C)": max_t_series}
                )
                if PLOTLY_AVAILABLE and st.session_state["ui_mode"] == "full_3d":
                    fig = go.Figure()
                    fig.add_trace(go.Bar(x=chart_df["Date"], y=chart_df["Rainfall (mm)"], name="Rainfall (mm)", marker_color="#0ea5e9"))
                    fig.add_trace(go.Scatter(x=chart_df["Date"], y=chart_df["FAO ET0 (mm)"], name="FAO ET0 (mm)", line=dict(color="#10b981", width=3)))
                    fig.add_trace(go.Scatter(x=chart_df["Date"], y=chart_df["Peak Temp (C)"], name="Peak Temp (C)", line=dict(color="#f59e0b", width=2, dash="dot")))
                    fig.update_layout(height=330, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(7,13,22,0.7)", font=dict(color="#e2e8f0"), margin=dict(l=10, r=10, t=25, b=10))
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.dataframe(chart_df, use_container_width=True, hide_index=True)
            st.markdown("</div>", unsafe_allow_html=True)

    # ---------------- TAB P3: SMART GRID & WATER RESOURCE CONTROLLER ----------------
    with tab_p3:
        st.markdown('<div class="section-hdr">PILLAR 03 // SMART AGRO-GRID SOLAR IRRADIANCE (W/m²) & TRANSFORMER CONTROLLER</div>', unsafe_allow_html=True)
        sg1, sg2, sg3, sg4 = st.columns(4)
        sg1.metric("Micro-Grid Solar Array", f"{grid.get('microgrid_solar_array_kwp', 0)} kWp", f"Pump Load: {grid.get('pump_power_demand_kw', 0)} kW")
        sg2.metric("Solar Pump Coverage", f"{solar_cov_pct}%", "Zero Grid Draw During Solar Peaks")
        sg3.metric("Grid Electricity Saved (7d)", f"{grid.get('grid_electricity_saved_7d_kwh', 0)} kWh", f"CO2 Avoided: {co2_saved} kg")
        sg4.metric("Optimal Solar Windows", ", ".join(grid.get("optimal_solar_dispatch_windows", [])[:3]) or "Rain Sufficient", grid.get("grid_stability_state", ""))

        matrix_24h = grid.get("hourly_24h_matrix", [])
        if matrix_24h:
            clean_matrix = [
                {k: (clean_emoji_text(v) if isinstance(v, str) else v) for k, v in row.items()}
                for row in matrix_24h
            ]
            grid_df = pd.DataFrame(clean_matrix)
            if PLOTLY_AVAILABLE and st.session_state["ui_mode"] == "full_3d":
                gfig = go.Figure()
                gfig.add_trace(go.Bar(x=grid_df["Hour"], y=grid_df["Solar_Irradiance_W_m2"], name="Solar Irradiance (W/m²)", marker_color="rgba(245, 158, 11, 0.8)"))
                gfig.add_trace(go.Scatter(x=grid_df["Hour"], y=grid_df["Transformer_Load_Pct"], name="Transformer Load (%)", line=dict(color="#f43f5e", width=3)))
                gfig.update_layout(height=305, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(7,13,22,0.7)", font=dict(color="#e2e8f0"), margin=dict(l=10, r=10, t=25, b=10))
                st.plotly_chart(gfig, use_container_width=True)
            st.dataframe(grid_df, use_container_width=True, hide_index=True)

    # ---------------- TAB P4: OSRM SUPPLY CHAIN & SQLITE SWARM ----------------
    with tab_p4:
        st.markdown('<div class="section-hdr">PILLAR 04 // AUTONOMOUS OSRM HIGHWAY ROUTING & SQLITE DISPATCH LEDGER</div>', unsafe_allow_html=True)
        sw1, sw2, sw3, sw4 = st.columns(4)
        sw1.metric("Active Dispatch ID", swarm.get("dispatch_id", "N/A"), swarm.get("priority_level", ""))
        sw2.metric("Target Regional Agri-Hub", swarm.get("selected_hub_name", "N/A")[:24], swarm.get("selected_hub_state", ""))
        sw3.metric("Live OSRM Highway Vector", f"{road_km} km", f"Transit ETA: {eta_mins} mins")
        sw4.metric("Flood Corridor Reroute", "ACTIVE (BYPASSED)" if swarm.get("flood_hazard_reroute_active") else "PRIMARY CLEAR", swarm.get("routing_engine", ""))

        st.markdown(
            f'<div class="hud-alert-ok">{get_3d_textured_svg("logistics_pod", 34)}'
            f'<div><b>SWARM CARGO MANIFEST:</b> {swarm.get("cargo_manifest", "")} ({swarm.get("dispatch_mode", "")})</div></div>',
            unsafe_allow_html=True,
        )

        m_col, db_col = st.columns([1.15, 1.35], gap="large")
        with m_col:
            hub_coords = swarm.get("selected_hub_coords", {"lat": 16.5062, "lon": 80.6480})
            if st.session_state["ui_mode"] == "full_3d":
                render_satellite_and_corridor_hud(lat, lon, resolved_city, float(hub_coords["lat"]), float(hub_coords["lon"]), hub_name, road_km)
            else:
                st.markdown(
                    f"""
                    <div class="hud-panel" style="text-align:center;">
                        {get_3d_textured_svg("logistics_pod", 84)}
                        <div style="font-family:'JetBrains Mono',monospace;font-size:1.05rem;font-weight:700;color:#c084fc;margin-top:8px;">
                            {resolved_city.upper()} ➔ {hub_name.upper()} ({road_km} KM)
                        </div>
                        <div style="font-size:0.84rem;color:#94a3b8;margin-top:4px;">
                            ETA: {eta_mins} mins • Dispatch ID: {swarm.get('dispatch_id')}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        with db_col:
            st.markdown('<div class="section-hdr">LIVE SQLITE DISPATCH LEDGER (KRISHIPULSE_SWARM.DB)</div>', unsafe_allow_html=True)
            ledger_rows = swarm.get("sqlite_ledger_recent", [])
            if ledger_rows:
                st.dataframe(pd.DataFrame(ledger_rows), use_container_width=True, hide_index=True)

    # ---------------- TAB 5: GLASS-BOX EXECUTION PROOF ----------------
    with tab_proof:
        st.markdown('<div class="hud-panel">', unsafe_allow_html=True)
        st.markdown('<div class="section-hdr">4-PILLAR AUTONOMOUS EXECUTION KERNEL // ZERO DUMMY DATA AUDIT</div>', unsafe_allow_html=True)
        for idx, step_log in enumerate(res.get("execution_trace", []), 1):
            st.markdown(
                f'<div style="background:#03060c;border-left:3px solid #10b981;padding:10px 14px;margin-bottom:6px;font-family:\'JetBrains Mono\',monospace;font-size:0.78rem;color:#a7f3d0;"><b>[STEP 0{idx}]</b> {clean_emoji_text(step_log)}</div>',
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)
        st.json(raw)
else:
    st.markdown(
        f"""
        <div class="hud-panel" style="text-align:center; padding:38px 20px;">
            <div style="margin-bottom:12px;">{get_3d_textured_svg("satellite", 66)}</div>
            <h3 style="color:#f8fafc; margin-bottom:8px;">DUAL-DEVICE 3D ORBITAL CONSOLE READY (LAPTOP &amp; MOBILE)</h3>
            <p style="color:#94a3b8; max-width:720px; margin:0 auto; font-size:0.93rem;">
                Tap any of the <b>4 Tactical Presets</b> above or open <b>Quick Mission Control</b> to test a custom village. The 3D textured hardware cards, swipeable tabs, and auto-resizing WebGL soil core automatically adapt to both laptop monitors and mobile phone screens.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Run client-side watchdog timer at the bottom of the DOM so it never adds top spacing
inject_watchdog_and_device_probe(timeout_ms=2800)