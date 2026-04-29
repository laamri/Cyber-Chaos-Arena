import csv
import hashlib
import io
import json
import os
from datetime import datetime, timezone
from uuid import uuid4

from flask import (
    Flask,
    Response,
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
app.secret_key = os.getenv("HONEYPOT_SECRET_KEY", "soc-honeypot-demo-secret")
app.config["SESSION_COOKIE_NAME"] = "honeypot_portal_session"

PORTAL_STYLE = """
:root {
  --bg: #07111f;
  --panel: rgba(8, 22, 40, 0.82);
  --line: rgba(132, 173, 214, 0.18);
  --text: #edf4ff;
  --muted: #a6bbd5;
  --accent: #2dd4bf;
  --accent-soft: rgba(45, 212, 191, 0.16);
  --accent-strong: #7dd3fc;
  --warning: #fbbf24;
  --danger: #fb7185;
  --shadow: 0 32px 80px rgba(0, 0, 0, 0.35);
}
* { box-sizing: border-box; }
body {
  margin: 0;
  min-height: 100vh;
  font-family: "Segoe UI", "Helvetica Neue", sans-serif;
  color: var(--text);
  background:
    radial-gradient(circle at top left, rgba(45, 212, 191, 0.12), transparent 26%),
    radial-gradient(circle at top right, rgba(125, 211, 252, 0.16), transparent 24%),
    linear-gradient(135deg, #07111f 0%, #09182b 48%, #0f2740 100%);
  overflow-x: hidden;
}
.shell {
  width: min(1160px, calc(100% - 32px));
  margin: 0 auto;
  padding: 40px 0 56px;
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
}
.panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 28px;
  box-shadow: var(--shadow);
  backdrop-filter: blur(18px);
}
.panel-primary { padding: 28px; }
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
.brand-row {
  display: grid;
  gap: 16px;
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
  background: rgba(251, 191, 36, 0.12);
  border: 1px solid rgba(251, 191, 36, 0.24);
  color: #fff1c5;
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
.notice-warning {
  background: rgba(251, 191, 36, 0.15);
  border-color: rgba(251, 191, 36, 0.24);
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
.form-grid,
.metric-grid,
.action-grid,
.feature-list {
  display: grid;
  gap: 14px;
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
  background: var(--warning);
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
  border-color: rgba(251, 191, 36, 0.72);
  box-shadow: 0 0 0 3px rgba(251, 191, 36, 0.12);
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
  transition: transform 160ms ease, box-shadow 160ms ease;
}
.button:hover { transform: translateY(-1px); }
.button-primary {
  background: linear-gradient(135deg, #fbbf24, #7dd3fc);
  color: #041522;
  box-shadow: 0 18px 30px rgba(251, 191, 36, 0.18);
}
.button-secondary {
  background: rgba(255, 255, 255, 0.05);
  color: var(--text);
  border: 1px solid rgba(255, 255, 255, 0.08);
}
.metric-grid,
.action-grid {
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
.action-card a {
  color: inherit;
  text-decoration: none;
}
.summary-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  margin: 0 8px 8px 0;
  border-radius: 999px;
  background: rgba(251, 191, 36, 0.1);
  border: 1px solid rgba(251, 191, 36, 0.18);
  color: #fff4cc;
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
.table th { color: #d9e9ff; }
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
  .action-grid { grid-template-columns: 1fr; }
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
        "source": "web-honeypot",
        "portal_mode": "honeypot",
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
    session.setdefault("decoy_actions", 0)
    g.request_id = request.headers.get("X-Request-ID", str(uuid4()))
    g.route_reason = request.headers.get("X-Route-Reason", "suspicious_request")
    g.client_ip = client_ip()
    log_event("request_received", route_target="honeypot")


@app.after_request
def decorate_response(response):
    response.headers["X-Portal-Mode"] = "honeypot"
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
    notice,
    notice_class="notice-warning",
):
    return render_template_string(
        BASE_TEMPLATE,
        title=f"Sentinel Access Portal | {heading}",
        style=PORTAL_STYLE,
        page_name=page_name,
        eyebrow="Adaptive Security Gateway",
        heading=heading,
        subtitle=subtitle,
        badge=badge,
        notice=notice,
        notice_class=notice_class,
        body_html=body_html,
        side_html=side_html,
    )


def increase_decoy_actions():
    session["decoy_actions"] = int(session.get("decoy_actions", 0)) + 1


def ensure_decoy_identity(candidate=None):
    if candidate:
        session["portal_identity"] = candidate[:80]
    session.setdefault("portal_identity", "ops.gateway")


def decoy_login_page(message=None, username="", probed_path=None):
    safe_username = escape(username)
    intro = (
        "Privileged access requires secondary verification. Continue to load the protected workspace."
        if probed_path
        else "Identity verification is required before portal tools are released."
    )
    notice = message or intro

    body_html = f"""
    <section class="surface">
      <h2>Authenticate before you enter the supervised workspace</h2>
      <p>
        This interface intentionally mirrors the production portal so that every
        probe, click, and login attempt can be observed under the same visual flow.
      </p>
      <form method="post" action="/login" class="form-grid" data-track-form="decoy_login_submitted">
        <div>
          <label class="field-label" for="username">Username</label>
          <input class="field-input" id="username" type="text" name="username" value="{safe_username}" autocomplete="username" />
        </div>
        <div>
          <label class="field-label" for="password">Password</label>
          <input class="field-input" id="password" type="password" name="password" autocomplete="current-password" />
        </div>
        <div class="button-row">
          <button class="button button-primary" type="submit">Continue Verification</button>
          <a class="button button-secondary" href="/api/internal/status" data-track="decoy_status_clicked" data-label="Internal status">System status</a>
        </div>
      </form>
      <p class="footer-note">This gateway may request more than one verification stage for elevated modules.</p>
    </section>
    <section class="surface" style="margin-top: 18px;">
      <h3>Verification posture</h3>
      <div class="metric-grid">
        <div class="metric">
          <strong>1</strong>
          <span>Primary sign-in stage captured and tagged for review.</span>
        </div>
        <div class="metric">
          <strong>Live</strong>
          <span>All activity is correlated with route reason and request metadata.</span>
        </div>
      </div>
    </section>
    """

    side_html = f"""
    <section class="surface">
      <h3>Captured context</h3>
      <p class="summary-chip">Route reason: {escape(g.route_reason)}</p>
      <p class="summary-chip">Client IP: {escape(g.client_ip)}</p>
      <p class="summary-chip">Session ID: {escape(session['portal_session_id'][:12])}</p>
      {f'<p class="summary-chip">Probe: {escape(probed_path)}</p>' if probed_path else ''}
    </section>
    <section class="surface">
      <h3>Decoy supervision</h3>
      <ul class="feature-list">
        <li>This environment looks close to the real portal on purpose.</li>
        <li>Every action is retained as structured JSON for Elasticsearch and Kibana.</li>
        <li>Falco can add runtime detection if the web container starts behaving outside its baseline.</li>
      </ul>
    </section>
    """

    return render_shell(
        page_name="login",
        heading="Elevated Access Gateway",
        subtitle="A near-identical security surface for suspicious users and deceptive workflow analysis.",
        badge="Decoy Interface",
        notice=notice,
        body_html=body_html,
        side_html=side_html,
    )


def decoy_workspace_page():
    identity = escape(session.get("portal_identity", "ops.gateway"))
    actions = escape(str(session.get("decoy_actions", 0)))

    body_html = f"""
    <section class="surface">
      <h2>Workspace prepared for {identity}</h2>
      <p>
        Elevated modules are staged below. Continue exploring to validate your
        authorization and load the protected resources.
      </p>
      <div class="action-grid">
        <div class="action-card">
          <a href="/profile" data-track="decoy_profile_opened" data-label="Decoy profile">
            <strong>Profile</strong>
            <span>Review privileged identity mapping and enrolled devices.</span>
          </a>
        </div>
        <div class="action-card">
          <a href="/reports" data-track="decoy_reports_opened" data-label="Decoy reports">
            <strong>Reports</strong>
            <span>Open the staged export history and supervisor notes.</span>
          </a>
        </div>
        <div class="action-card">
          <a href="/admin/users" data-track="decoy_admin_users_opened" data-label="Decoy admin users">
            <strong>Admin Users</strong>
            <span>Inspect the privileged user directory and lock status.</span>
          </a>
        </div>
        <div class="action-card">
          <a href="/download/activity.csv" data-track="decoy_activity_downloaded" data-label="Decoy CSV download">
            <strong>Export Activity</strong>
            <span>Download a staged activity report and trigger deeper observation.</span>
          </a>
        </div>
      </div>
    </section>
    <section class="surface" style="margin-top: 18px;">
      <h3>Engagement score</h3>
      <div class="metric-grid">
        <div class="metric">
          <strong>{actions}</strong>
          <span>Tracked interaction count in this decoy session.</span>
        </div>
        <div class="metric">
          <strong>Review</strong>
          <span>Behavior can be correlated with Falco and Nginx data before you decide to block.</span>
        </div>
      </div>
    </section>
    """

    side_html = f"""
    <section class="surface">
      <h3>Session markers</h3>
      <p class="summary-chip">Identity: {identity}</p>
      <p class="summary-chip">Route reason: {escape(g.route_reason)}</p>
      <p class="summary-chip">Session ID: {escape(session['portal_session_id'][:12])}</p>
      <p class="summary-chip">Captured actions: {actions}</p>
    </section>
    <section class="surface">
      <h3>Analyst usage</h3>
      <ul class="feature-list">
        <li>Keep the wording close to the real portal so suspicious actors stay engaged.</li>
        <li>Use the decoy clicks to identify curiosity, privilege escalation, or exfiltration patterns.</li>
        <li>Make blocking decisions only after behavior from the app, proxy, and Falco align.</li>
      </ul>
    </section>
    """

    return render_shell(
        page_name="workspace",
        heading="Privileged Workspace",
        subtitle="A guided decoy environment designed to look legitimate while maximizing attacker observability.",
        badge="Decoy Session",
        notice="Additional verification is in progress while protected modules are loaded.",
        body_html=body_html,
        side_html=side_html,
    )


def decoy_profile_page():
    identity = escape(session.get("portal_identity", "ops.gateway"))

    body_html = f"""
    <section class="surface">
      <h2>Privileged identity map</h2>
      <table class="table">
        <tr><th>Username</th><td>{identity}</td></tr>
        <tr><th>Role</th><td>Regional Administrator</td></tr>
        <tr><th>Trust tier</th><td>Elevated review required</td></tr>
        <tr><th>Devices</th><td>3 registered endpoints</td></tr>
        <tr><th>Supervisor state</th><td>Active review</td></tr>
      </table>
      <div class="button-row">
        <a class="button button-primary" href="/workspace" data-track="decoy_profile_back" data-label="Back to decoy workspace">Back to Workspace</a>
      </div>
    </section>
    """

    side_html = """
    <section class="surface">
      <h3>Why this page exists</h3>
      <ul class="feature-list">
        <li>Profile access often reveals how far a suspicious user wants to go.</li>
        <li>Keeping believable metadata helps extend the observation window.</li>
        <li>Nothing here exposes a real identity store.</li>
      </ul>
    </section>
    """

    return render_shell(
        page_name="profile",
        heading="Privileged Profile",
        subtitle="Decoy identity details that encourage exploration without exposing production assets.",
        badge="High Observation",
        notice="Profile access has been logged as a privileged decoy interaction.",
        body_html=body_html,
        side_html=side_html,
    )


def decoy_reports_page():
    body_html = """
    <section class="surface">
      <h2>Staged report history</h2>
      <table class="table">
        <tr><th>Dataset</th><th>Status</th><th>Retention</th></tr>
        <tr><td>Identity exports</td><td>Queued</td><td>90 days</td></tr>
        <tr><td>Endpoint inventory</td><td>Ready</td><td>30 days</td></tr>
        <tr><td>Supervisor alerts</td><td>Streaming</td><td>14 days</td></tr>
      </table>
      <div class="button-row">
        <a class="button button-primary" href="/download/activity.csv" data-track="decoy_reports_export" data-label="Export from reports">Export CSV</a>
        <a class="button button-secondary" href="/workspace" data-track="decoy_reports_back" data-label="Return to decoy workspace">Back</a>
      </div>
    </section>
    """

    side_html = """
    <section class="surface">
      <h3>Behavior hints</h3>
      <ul class="feature-list">
        <li>Report downloads are useful to spot exfiltration intent.</li>
        <li>Cross-check these actions with Nginx request IDs and source IPs.</li>
        <li>Falco can help if container behavior changes after the interaction.</li>
      </ul>
    </section>
    """

    return render_shell(
        page_name="reports",
        heading="Report Archive",
        subtitle="Decoy operational data tuned to capture interest in exports and privileged records.",
        badge="Tracked Archive",
        notice="Report activity remains under active observation.",
        body_html=body_html,
        side_html=side_html,
    )


def decoy_probe_page(path):
    probed_path = "/" + path.strip("/")
    body_html = f"""
    <section class="surface">
      <h2>Protected resource</h2>
      <p>
        The requested path <strong>{escape(probed_path)}</strong> requires an
        elevated sign-in. Continue with the access workflow to unlock staged modules.
      </p>
      <div class="button-row">
        <a class="button button-primary" href="/login" data-track="decoy_probe_continue" data-label="Continue from probe">Continue Verification</a>
        <a class="button button-secondary" href="/api/internal/status" data-track="decoy_probe_status" data-label="Probe status endpoint">Status</a>
      </div>
    </section>
    """

    side_html = """
    <section class="surface">
      <h3>Requested capability</h3>
      <ul class="feature-list">
        <li>The gateway will present more resources after the sign-in flow continues.</li>
        <li>Each probe expands the observation trail for the same session.</li>
      </ul>
    </section>
    """

    return render_shell(
        page_name="probe",
        heading="Protected Module Gateway",
        subtitle="The decoy keeps the same look and feel while channeling suspicious users into a supervised flow.",
        badge="Protected Path",
        notice="The requested module is staged behind additional verification.",
        body_html=body_html,
        side_html=side_html,
    )


@app.get("/")
def home():
    log_event("decoy_home_view", outcome="decoy_capture")
    return decoy_login_page()


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        log_event("decoy_login_view", outcome="decoy_capture")
        return decoy_login_page(username=request.args.get("username", ""))

    username = request.form.get("username", "").strip() or "ops.gateway"
    password = request.form.get("password", "")
    fingerprint = credential_fingerprint(username, password)

    ensure_decoy_identity(username)
    increase_decoy_actions()
    log_event(
        "credential_capture",
        outcome="decoy_capture",
        attempted_username=username,
        credential_fingerprint=fingerprint,
        password_length=len(password),
    )
    return redirect(url_for("workspace"))


@app.get("/workspace")
def workspace():
    ensure_decoy_identity()
    increase_decoy_actions()
    log_event("decoy_workspace_view", outcome="decoy_capture")
    return decoy_workspace_page()


@app.get("/profile")
def profile():
    ensure_decoy_identity()
    increase_decoy_actions()
    log_event("decoy_profile_view", outcome="decoy_capture")
    return decoy_profile_page()


@app.get("/reports")
def reports():
    ensure_decoy_identity()
    increase_decoy_actions()
    log_event("decoy_reports_view", outcome="decoy_capture")
    return decoy_reports_page()


@app.get("/admin/users")
def admin_users():
    ensure_decoy_identity()
    increase_decoy_actions()
    log_event("decoy_admin_users_view", outcome="high_interest")

    body_html = """
    <section class="surface">
      <h2>Privileged directory</h2>
      <table class="table">
        <tr><th>User</th><th>Role</th><th>Status</th></tr>
        <tr><td>amartin</td><td>Regional Admin</td><td>Active</td></tr>
        <tr><td>jnguyen</td><td>Compliance Lead</td><td>Pending MFA reset</td></tr>
        <tr><td>svc-billing</td><td>Service Account</td><td>Locked for review</td></tr>
      </table>
      <div class="button-row">
        <a class="button button-primary" href="/workspace" data-track="decoy_admin_back" data-label="Back from admin users">Back to Workspace</a>
      </div>
    </section>
    """

    side_html = """
    <section class="surface">
      <h3>Supervisor interpretation</h3>
      <ul class="feature-list">
        <li>Admin directory access is a stronger signal than a simple login attempt.</li>
        <li>Use this event to escalate analyst review before any blocking decision.</li>
      </ul>
    </section>
    """

    return render_shell(
        page_name="admin-users",
        heading="Privileged Directory",
        subtitle="Decoy user directory intended to keep suspicious users engaged and attributable.",
        badge="Escalated Interest",
        notice="Directory access has been marked for analyst review.",
        body_html=body_html,
        side_html=side_html,
    )


@app.get("/download/activity.csv")
def download_activity():
    ensure_decoy_identity()
    increase_decoy_actions()
    log_event("decoy_download_attempt", outcome="high_interest", artifact="activity.csv")

    rows = [
        ["timestamp", "module", "status"],
        [utc_now(), "identity-export", "queued"],
        [utc_now(), "endpoint-inventory", "ready"],
        [utc_now(), "audit-overview", "streaming"],
    ]
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerows(rows)

    return Response(
        buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=activity.csv"},
    )


@app.get("/api/internal/status")
def internal_status():
    ensure_decoy_identity()
    log_event("decoy_api_status_view", outcome="decoy_capture")
    return jsonify(
        status="degraded",
        source="web-honeypot",
        portal_mode="honeypot",
        route_reason=g.route_reason,
        request_id=g.request_id,
        supervisor="active_review",
        modules=["identity", "exports", "compliance"],
    ), 200


@app.post("/telemetry")
def telemetry():
    payload = request.get_json(silent=True) or {}
    log_event(
        "frontend_telemetry",
        outcome="decoy_capture",
        frontend_event=payload.get("event", "unknown"),
        context=payload.get("context", {}),
    )
    return ("", 204)


@app.get("/health")
def health():
    log_event("health_check")
    return jsonify(status="ok", app="web-honeypot", mode="honeypot"), 200


@app.route("/<path:path>", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
def catch_all(path):
    probed_path = "/" + path.strip("/")

    if request.method not in {"GET", "POST"}:
        increase_decoy_actions()
        log_event(
            "unexpected_method_probe",
            outcome="high_interest",
            probed_path=probed_path,
            attempted_method=request.method,
        )
        return jsonify(
            message="Restricted area",
            status="captured",
            timestamp=utc_now(),
            source="web-honeypot",
            requested_path=probed_path,
            method=request.method,
            client_ip=g.client_ip,
            user_agent=request.headers.get("User-Agent", "unknown"),
            route_reason=g.route_reason,
        ), 200

    if request.method == "POST":
        username = request.form.get("username", "").strip() or request.args.get("username", "").strip()
        password = request.form.get("password", "") or request.args.get("password", "")
        if username or password:
            ensure_decoy_identity(username or "ops.gateway")
            increase_decoy_actions()
            log_event(
                "credential_capture",
                outcome="decoy_capture",
                attempted_username=username or "anonymous",
                credential_fingerprint=credential_fingerprint(username, password),
                password_length=len(password),
                probed_path=probed_path,
            )
            return redirect(url_for("workspace"))

    ensure_decoy_identity()
    increase_decoy_actions()
    log_event("unexpected_path_probe", outcome="decoy_capture", probed_path=probed_path)
    return decoy_probe_page(path)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
