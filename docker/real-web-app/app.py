import hashlib
import json
import os
from datetime import datetime, timezone
from uuid import uuid4

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template_string,
    request,
    session,
    url_for,
    g,
    has_request_context,
)
from markupsafe import escape

app = Flask(__name__)
app.secret_key = os.getenv("PORTAL_SECRET_KEY", "soc-real-portal-demo-secret")
app.config["SESSION_COOKIE_NAME"] = "real_portal_session"

PORTAL_NAME = "Sentinel Access Portal"
PORTAL_STYLE = """
:root {
  --bg: #07111f;
  --panel: rgba(8, 22, 40, 0.78);
  --panel-strong: rgba(7, 17, 31, 0.92);
  --line: rgba(132, 173, 214, 0.18);
  --text: #edf4ff;
  --muted: #a6bbd5;
  --accent: #2dd4bf;
  --accent-soft: rgba(45, 212, 191, 0.16);
  --accent-strong: #7dd3fc;
  --danger: #fb7185;
  --warning: #fbbf24;
  --shadow: 0 32px 80px rgba(0, 0, 0, 0.35);
}
* { box-sizing: border-box; }
body {
  margin: 0;
  min-height: 100vh;
  font-family: "Segoe UI", "Helvetica Neue", sans-serif;
  color: var(--text);
  background:
    radial-gradient(circle at top left, rgba(45, 212, 191, 0.14), transparent 26%),
    radial-gradient(circle at top right, rgba(125, 211, 252, 0.18), transparent 24%),
    linear-gradient(135deg, #07111f 0%, #09182b 48%, #0f2740 100%);
  overflow-x: hidden;
}
.shell {
  width: min(1160px, calc(100% - 32px));
  margin: 0 auto;
  padding: 40px 0 56px;
  position: relative;
}
.orb {
  position: fixed;
  border-radius: 999px;
  filter: blur(8px);
  opacity: 0.55;
  pointer-events: none;
}
.orb-a {
  width: 280px;
  height: 280px;
  right: -80px;
  top: 64px;
  background: rgba(45, 212, 191, 0.18);
}
.orb-b {
  width: 180px;
  height: 180px;
  left: -40px;
  bottom: 64px;
  background: rgba(125, 211, 252, 0.16);
}
.hero {
  display: grid;
  gap: 24px;
  grid-template-columns: minmax(0, 1.4fr) minmax(320px, 0.9fr);
  align-items: stretch;
}
.panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 28px;
  box-shadow: var(--shadow);
  backdrop-filter: blur(18px);
}
.panel-primary {
  padding: 28px;
}
.panel-secondary {
  padding: 24px;
  display: grid;
  gap: 18px;
  align-content: start;
}
.eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  margin: 0 0 14px;
  color: var(--accent-strong);
  font-size: 0.9rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}
.eyebrow::before {
  content: "";
  width: 42px;
  height: 1px;
  background: linear-gradient(90deg, rgba(45, 212, 191, 0), rgba(45, 212, 191, 0.9));
}
.brand-row,
.toolbar,
.metric-grid,
.feature-list,
.action-grid,
.summary-grid {
  display: grid;
  gap: 16px;
}
.brand-row {
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  margin-bottom: 18px;
}
.brand-mark {
  width: 58px;
  height: 58px;
  border-radius: 18px;
  background: linear-gradient(135deg, rgba(45, 212, 191, 0.95), rgba(125, 211, 252, 0.9));
  box-shadow: 0 10px 28px rgba(45, 212, 191, 0.22);
  color: #03131f;
  display: grid;
  place-items: center;
  font-weight: 800;
  font-size: 1.2rem;
}
.brand-copy h1 {
  margin: 0;
  font-size: clamp(2rem, 3vw, 3.1rem);
  line-height: 1.02;
}
.brand-copy p {
  margin: 10px 0 0;
  color: var(--muted);
  max-width: 54ch;
  line-height: 1.6;
}
.mode-pill {
  padding: 10px 16px;
  border-radius: 999px;
  background: rgba(45, 212, 191, 0.14);
  border: 1px solid rgba(45, 212, 191, 0.24);
  color: #d4fff9;
  font-size: 0.86rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.notice {
  margin: 0 0 18px;
  padding: 14px 16px;
  border-radius: 16px;
  border: 1px solid transparent;
  line-height: 1.5;
}
.notice-info {
  background: rgba(125, 211, 252, 0.12);
  border-color: rgba(125, 211, 252, 0.2);
}
.notice-error {
  background: rgba(251, 113, 133, 0.14);
  border-color: rgba(251, 113, 133, 0.24);
}
.surface {
  padding: 22px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.028);
  border: 1px solid rgba(255, 255, 255, 0.06);
}
.surface h2,
.surface h3 {
  margin: 0 0 8px;
}
.surface p,
.surface li {
  color: var(--muted);
  line-height: 1.6;
}
.form-grid {
  display: grid;
  gap: 14px;
  margin-top: 16px;
}
.field-label {
  font-size: 0.95rem;
  margin-bottom: 8px;
  display: block;
  color: #e7f1ff;
}
.field-input {
  width: 100%;
  border: 1px solid rgba(132, 173, 214, 0.18);
  background: rgba(3, 12, 24, 0.62);
  color: var(--text);
  border-radius: 16px;
  padding: 15px 16px;
  font-size: 1rem;
  outline: none;
  transition: border-color 160ms ease, transform 160ms ease, box-shadow 160ms ease;
}
.field-input:focus {
  border-color: rgba(45, 212, 191, 0.72);
  box-shadow: 0 0 0 3px rgba(45, 212, 191, 0.14);
  transform: translateY(-1px);
}
.button-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 6px;
}
.button {
  border: 0;
  border-radius: 16px;
  padding: 14px 18px;
  cursor: pointer;
  text-decoration: none;
  font-weight: 700;
  transition: transform 160ms ease, box-shadow 160ms ease, opacity 160ms ease;
}
.button:hover {
  transform: translateY(-1px);
}
.button-primary {
  background: linear-gradient(135deg, #2dd4bf, #7dd3fc);
  color: #041522;
  box-shadow: 0 18px 30px rgba(45, 212, 191, 0.2);
}
.button-secondary {
  background: rgba(255, 255, 255, 0.05);
  color: var(--text);
  border: 1px solid rgba(255, 255, 255, 0.08);
}
.metric-grid,
.action-grid,
.summary-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.metric,
.action-card {
  padding: 18px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
}
.metric strong,
.action-card strong {
  display: block;
  font-size: 1.7rem;
  margin-bottom: 6px;
}
.feature-list {
  padding: 0;
  margin: 0;
  list-style: none;
}
.feature-list li {
  position: relative;
  padding-left: 18px;
}
.feature-list li::before {
  content: "";
  position: absolute;
  left: 0;
  top: 11px;
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: var(--accent);
}
.action-card a {
  color: inherit;
  text-decoration: none;
}
.summary-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(45, 212, 191, 0.1);
  border: 1px solid rgba(45, 212, 191, 0.18);
  color: #dffdf9;
  font-size: 0.88rem;
}
.table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 14px;
}
.table th,
.table td {
  text-align: left;
  padding: 12px 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  color: var(--muted);
}
.table th {
  color: #d9e9ff;
}
.footer-note {
  margin-top: 22px;
  color: var(--muted);
  font-size: 0.92rem;
}
@media (max-width: 900px) {
  .hero { grid-template-columns: 1fr; }
  .brand-row { grid-template-columns: auto 1fr; }
  .mode-pill { grid-column: 1 / -1; justify-self: start; }
}
@media (max-width: 640px) {
  .shell { width: min(100% - 20px, 1160px); padding-top: 18px; }
  .panel-primary,
  .panel-secondary,
  .surface { padding: 18px; }
  .metric-grid,
  .action-grid,
  .summary-grid { grid-template-columns: 1fr; }
}
"""

BASE_TEMPLATE = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{{ title }}</title>
    <style>{{ style }}</style>
  </head>
  <body data-page="{{ page_name }}">
    <div class="orb orb-a"></div>
    <div class="orb orb-b"></div>
    <main class="shell">
      <section class="hero">
        <article class="panel panel-primary">
          <div class="brand-row">
            <div class="brand-mark">SA</div>
            <div class="brand-copy">
              <p class="eyebrow">{{ eyebrow }}</p>
              <h1>{{ heading }}</h1>
              <p>{{ subtitle }}</p>
            </div>
            <span class="mode-pill">{{ badge }}</span>
          </div>
          {% if notice %}
            <div class="notice {{ notice_class }}">{{ notice }}</div>
          {% endif %}
          {{ body_html | safe }}
        </article>
        <aside class="panel panel-secondary">
          {{ side_html | safe }}
        </aside>
      </section>
    </main>
    <script>
      const sendTelemetry = (eventName, context) => {
        fetch("/telemetry", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ event: eventName, context })
        }).catch(() => {});
      };

      window.addEventListener("DOMContentLoaded", () => {
        sendTelemetry("page_loaded", {
          page: document.body.dataset.page,
          title: document.title
        });

        const form = document.querySelector("[data-track-form]");
        if (form) {
          form.addEventListener("submit", () => {
            sendTelemetry(form.dataset.trackForm, {
              page: document.body.dataset.page,
              action: form.getAttribute("action") || window.location.pathname
            });
          });
        }

        document.querySelectorAll("[data-track]").forEach((node) => {
          node.addEventListener("click", () => {
            sendTelemetry(node.dataset.track, {
              page: document.body.dataset.page,
              label: node.dataset.label || node.textContent.trim(),
              href: node.getAttribute("href") || ""
            });
          });
        });
      });
    </script>
  </body>
</html>
"""

USERS = {
    "admin": {
        "password": "123",
        "role": "SOC Lead",
        "team": "Blue Team",
        "risk": "trusted_supervised",
    },
    "analyst": {
        "password": "analyst123",
        "role": "Threat Analyst",
        "team": "Tier 1",
        "risk": "trusted_supervised",
    },
}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def credential_fingerprint(username, password):
    raw = f"{username}:{password}".encode("utf-8", errors="ignore")
    return hashlib.sha256(raw).hexdigest()[:16]


def client_ip():
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.remote_addr or "unknown"


def log_event(event, outcome="observe", **details):
    payload = {
        "timestamp": utc_now(),
        "source": "real-web-app",
        "portal_mode": "normal",
        "event": event,
        "outcome": outcome,
    }

    if has_request_context():
        payload.update(
            {
                "method": request.method,
                "path": request.path,
                "request_id": getattr(g, "request_id", None),
                "route_reason": getattr(g, "route_reason", None),
                "client_ip": getattr(g, "client_ip", client_ip()),
                "user_agent": request.headers.get("User-Agent", "unknown"),
                "session_id": session.get("portal_session_id"),
                "portal_identity": session.get("portal_identity"),
            }
        )

    for key, value in details.items():
        if value is not None and value != "":
            payload[key] = value

    print(json.dumps(payload, sort_keys=True), flush=True)


@app.before_request
def attach_request_context():
    session.setdefault("portal_session_id", str(uuid4()))
    g.request_id = request.headers.get("X-Request-ID", str(uuid4()))
    g.route_reason = request.headers.get("X-Route-Reason", "normal_user")
    g.client_ip = client_ip()
    log_event("request_received")


@app.after_request
def decorate_response(response):
    response.headers["X-Portal-Mode"] = "normal"
    response.headers["X-Request-ID"] = getattr(g, "request_id", "untracked")
    log_event("response_sent", http_status=response.status_code)
    return response


def render_shell(
    *,
    page_name,
    heading,
    subtitle,
    badge,
    body_html,
    side_html,
    notice=None,
    notice_class="notice-info",
):
    return render_template_string(
        BASE_TEMPLATE,
        title=f"{PORTAL_NAME} | {heading}",
        style=PORTAL_STYLE,
        page_name=page_name,
        eyebrow="Zero-Trust Supervision Layer",
        heading=heading,
        subtitle=subtitle,
        badge=badge,
        notice=notice,
        notice_class=notice_class,
        body_html=body_html,
        side_html=side_html,
    )


def login_page(message=None, error=False, username=""):
    safe_username = escape(username)
    notice_class = "notice-error" if error else "notice-info"
    notice = (
        message
        or "Every session is supervised. Access is granted only after identity, context, and behavior are checked."
    )

    body_html = f"""
    <section class="surface">
      <h2>Authenticate before you enter the analyst workspace</h2>
      <p>
        This portal keeps the user experience clean while preserving continuous
        telemetry for login attempts, page transitions, and abnormal behavior.
      </p>
      <form method="post" action="/login" class="form-grid" data-track-form="login_attempt_submitted">
        <div>
          <label class="field-label" for="username">Username</label>
          <input class="field-input" id="username" type="text" name="username" value="{safe_username}" autocomplete="username" />
        </div>
        <div>
          <label class="field-label" for="password">Password</label>
          <input class="field-input" id="password" type="password" name="password" autocomplete="current-password" />
        </div>
        <div class="button-row">
          <button class="button button-primary" type="submit">Open Workspace</button>
          <a class="button button-secondary" href="/health" data-track="health_link_clicked" data-label="Health endpoint">Check health</a>
        </div>
      </form>
      <p class="footer-note">Demo accounts: <strong>admin / 123</strong> or <strong>analyst / analyst123</strong>.</p>
    </section>
    <section class="surface" style="margin-top: 18px;">
      <h3>Why this portal is different</h3>
      <div class="summary-grid">
        <div class="metric">
          <strong>2</strong>
          <span>User journeys tracked in parallel: normal workspace and decoy workspace.</span>
        </div>
        <div class="metric">
          <strong>24/7</strong>
          <span>Audit telemetry is emitted on each request and correlated with reverse-proxy request IDs.</span>
        </div>
      </div>
    </section>
    """

    side_html = """
    <section class="surface">
      <h3>Continuous supervision</h3>
      <ul class="feature-list">
        <li>Identity is supervised even after the first successful login.</li>
        <li>Route decisions from Nginx travel with every request for forensic correlation.</li>
        <li>Falco can add host and container behavior alerts on top of the application audit trail.</li>
      </ul>
    </section>
    <section class="surface">
      <h3>Session controls</h3>
      <div class="metric-grid">
        <div class="metric">
          <strong>100%</strong>
          <span>Requests tagged with a session identifier.</span>
        </div>
        <div class="metric">
          <strong>JSON</strong>
          <span>Structured logs flow cleanly into Filebeat, Elasticsearch, and Kibana.</span>
        </div>
      </div>
    </section>
    """

    return render_shell(
        page_name="login",
        heading="Supervised Login Portal",
        subtitle="Modern access for normal users, with full traceability for your SOC team.",
        badge="Normal Interface",
        notice=notice,
        notice_class=notice_class,
        body_html=body_html,
        side_html=side_html,
    )


def require_identity():
    if not session.get("portal_identity"):
        log_event("unauthenticated_redirect", outcome="redirect")
        return False
    return True


def workspace_page():
    user = USERS.get(session["portal_identity"], {})
    username = escape(session["portal_identity"])
    role = escape(user.get("role", "Analyst"))
    team = escape(user.get("team", "SOC"))

    body_html = f"""
    <section class="surface">
      <h2>Welcome back, {username}</h2>
      <p>
        You are signed in as <strong>{role}</strong> in <strong>{team}</strong>.
        This normal environment is intentionally polished, but still monitored
        under a never-trust-default posture.
      </p>
      <div class="action-grid">
        <div class="action-card">
          <a href="/profile" data-track="workspace_profile_opened" data-label="Profile">
            <strong>Profile</strong>
            <span>Review identity context, team membership, and verification posture.</span>
          </a>
        </div>
        <div class="action-card">
          <a href="/reports" data-track="workspace_reports_opened" data-label="Reports">
            <strong>Reports</strong>
            <span>Inspect the day summary, triage queue, and action history.</span>
          </a>
        </div>
      </div>
      <div class="button-row" style="margin-top: 18px;">
        <a class="button button-primary" href="/profile" data-track="profile_button_clicked" data-label="Profile button">Review Profile</a>
        <a class="button button-secondary" href="/logout" data-track="logout_clicked" data-label="Logout">End Session</a>
      </div>
    </section>
    <section class="surface" style="margin-top: 18px;">
      <h3>Current trust signals</h3>
      <div class="metric-grid">
        <div class="metric">
          <strong>Low</strong>
          <span>Current risk posture based on approved credentials and normal route reason.</span>
        </div>
        <div class="metric">
          <strong>Live</strong>
          <span>Session activity is streamed to your SOC pipeline for supervision and anomaly review.</span>
        </div>
      </div>
    </section>
    """

    side_html = f"""
    <section class="surface">
      <h3>Session summary</h3>
      <p class="summary-chip">Route reason: {escape(g.route_reason)}</p>
      <p class="summary-chip">Session ID: {escape(session['portal_session_id'][:12])}</p>
      <p class="summary-chip">Client IP: {escape(g.client_ip)}</p>
      <p class="summary-chip">Identity: {username}</p>
    </section>
    <section class="surface">
      <h3>Supervisor notes</h3>
      <ul class="feature-list">
        <li>Keep this interface close to the decoy so suspicious actors reveal intent naturally.</li>
        <li>Use the structured audit trail to compare user journeys across both environments.</li>
        <li>Correlate Falco alerts with request IDs when container activity looks abnormal.</li>
      </ul>
    </section>
    """

    return render_shell(
        page_name="workspace",
        heading="Analyst Workspace",
        subtitle="Normal-user experience with zero-trust telemetry baked into each action.",
        badge="Authenticated Session",
        notice="The user experience stays smooth, but the session remains continuously verified.",
        body_html=body_html,
        side_html=side_html,
    )


def profile_page():
    user = USERS.get(session["portal_identity"], {})
    username = escape(session["portal_identity"])

    body_html = f"""
    <section class="surface">
      <h2>Identity context</h2>
      <table class="table">
        <tr><th>Username</th><td>{username}</td></tr>
        <tr><th>Role</th><td>{escape(user.get("role", "Analyst"))}</td></tr>
        <tr><th>Team</th><td>{escape(user.get("team", "SOC"))}</td></tr>
        <tr><th>Supervision mode</th><td>Continuous behavioral monitoring</td></tr>
        <tr><th>Trust principle</th><td>Never trust, always verify</td></tr>
      </table>
      <div class="button-row">
        <a class="button button-primary" href="/workspace" data-track="profile_back_to_workspace" data-label="Back to workspace">Back to Workspace</a>
        <a class="button button-secondary" href="/logout" data-track="profile_logout" data-label="Logout from profile">Logout</a>
      </div>
    </section>
    """

    side_html = """
    <section class="surface">
      <h3>Audit coverage</h3>
      <ul class="feature-list">
        <li>Profile access is logged as a privileged observation step.</li>
        <li>Session and client metadata are emitted with each request.</li>
        <li>Credential values are never logged in cleartext.</li>
      </ul>
    </section>
    """

    return render_shell(
        page_name="profile",
        heading="Identity Profile",
        subtitle="Useful context for the real user while preserving clean audit boundaries.",
        badge="Identity View",
        notice="Profile access has been recorded for audit review.",
        body_html=body_html,
        side_html=side_html,
    )


def reports_page():
    body_html = """
    <section class="surface">
      <h2>Daily report queue</h2>
      <table class="table">
        <tr><th>Queue</th><th>Status</th><th>Owner</th></tr>
        <tr><td>Suspicious sign-ins</td><td>Watching</td><td>Blue Team</td></tr>
        <tr><td>Portal activity comparison</td><td>Streaming</td><td>SIEM</td></tr>
        <tr><td>Falco runtime alerts</td><td>Enabled</td><td>Host Sensor</td></tr>
      </table>
      <div class="button-row">
        <a class="button button-primary" href="/workspace" data-track="reports_back_to_workspace" data-label="Back to workspace">Back to Workspace</a>
      </div>
    </section>
    """

    side_html = """
    <section class="surface">
      <h3>Why this matters</h3>
      <ul class="feature-list">
        <li>The normal user path now emits business-friendly telemetry instead of raw debug output.</li>
        <li>The decoy path can mirror these events for attacker behavior comparison.</li>
        <li>Filebeat can ingest both streams without extra agents inside the app containers.</li>
      </ul>
    </section>
    """

    return render_shell(
        page_name="reports",
        heading="Operations Reports",
        subtitle="A lightweight dashboard view that still leaves a strong trail for supervision.",
        badge="Observed View",
        notice="Report access has been attached to the active session record.",
        body_html=body_html,
        side_html=side_html,
    )


@app.get("/")
def home():
    if session.get("portal_identity"):
        log_event("home_redirect_workspace", outcome="redirect")
        return redirect(url_for("workspace"))
    log_event("home_login_view")
    return login_page()


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        log_event("login_view")
        return login_page(username=request.args.get("username", ""))

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    fingerprint = credential_fingerprint(username, password)

    if username in USERS and USERS[username]["password"] == password:
        session["portal_identity"] = username
        log_event(
            "login_attempt",
            outcome="allow",
            attempted_username=username,
            credential_fingerprint=fingerprint,
            password_length=len(password),
        )
        return redirect(url_for("workspace"))

    session.pop("portal_identity", None)
    log_event(
        "login_attempt",
        outcome="deny",
        attempted_username=username or "anonymous",
        credential_fingerprint=fingerprint,
        password_length=len(password),
    )
    return login_page(
        message="The credentials were rejected. The attempt is still recorded and supervised.",
        error=True,
        username=username,
    ), 401


@app.get("/workspace")
def workspace():
    if not require_identity():
        return redirect(url_for("login"))
    log_event("workspace_view", outcome="allow")
    return workspace_page()


@app.get("/profile")
def profile():
    if not require_identity():
        return redirect(url_for("login"))
    log_event("profile_view", outcome="allow")
    return profile_page()


@app.get("/reports")
def reports():
    if not require_identity():
        return redirect(url_for("login"))
    log_event("reports_view", outcome="allow")
    return reports_page()


@app.get("/logout")
def logout():
    identity = session.pop("portal_identity", None)
    log_event("logout", outcome="allow", previous_identity=identity or "anonymous")
    return redirect(url_for("login"))


@app.post("/telemetry")
def telemetry():
    payload = request.get_json(silent=True) or {}
    log_event(
        "frontend_telemetry",
        outcome="observe",
        frontend_event=payload.get("event", "unknown"),
        context=payload.get("context", {}),
    )
    return ("", 204)


@app.get("/health")
def health():
    log_event("health_check")
    return jsonify(status="ok", app="real-web-app", mode="normal"), 200


@app.get("/api/session")
def session_details():
    if not require_identity():
        return jsonify(status="denied", message="Authentication required"), 401

    user = USERS.get(session["portal_identity"], {})
    log_event("api_session_view", outcome="allow")
    return jsonify(
        status="ok",
        source="real-web-app",
        portal_mode="normal",
        user=session["portal_identity"],
        role=user.get("role", "Analyst"),
        team=user.get("team", "SOC"),
        route_reason=g.route_reason,
        request_id=g.request_id,
        session_id=session["portal_session_id"],
    ), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
