#!/usr/bin/env python3
"""Build the designed OIF administrator handbook PDF.

The three Markdown manuals remain the source of truth. This build step uses
Pandoc for semantic HTML, injects print-native diagrams and photography at
chapter boundaries, and asks Chromium to produce the final tagged A4 PDF.
"""

from __future__ import annotations

import html
import base64
import mimetypes
import shutil
import subprocess
import time
from pathlib import Path


DOCS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = DOCS_DIR.parent
OUTPUT = DOCS_DIR / "OIF_PLATFORM_ADMINISTRATOR_MANUAL.pdf"
SOURCES = [
    DOCS_DIR / "ADMINISTRATOR_MANUAL.md",
    DOCS_DIR / "MODULES_MANUAL.md",
    DOCS_DIR / "ROLES_MANUAL.md",
]
ASSETS_DIR = DOCS_DIR / "manual_assets"


def asset(name: str) -> str:
    path = ASSETS_DIR / name
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return html.escape(f"data:{media_type};base64,{encoded}", quote=True)


def photo_feature(name: str, eyebrow: str, title: str, body: str) -> str:
    return f"""
<figure class="manual-photo-feature">
  <img src="{asset(name)}" alt="">
  <figcaption>
    <span>{eyebrow}</span>
    <strong>{title}</strong>
    <p>{body}</p>
  </figcaption>
</figure>
"""


PLATFORM_DIAGRAM = """
<figure class="manual-diagram system-map" aria-label="OIF platform operating model">
  <figcaption><span>Operating model</span><strong>One platform, four connected layers</strong><p>Public experience, role-aware operations, core workflows, and trusted records work as one system.</p></figcaption>
  <div class="system-audiences">
    <div><b>Public</b><small>Website · policies · giving</small></div>
    <div><b>Members</b><small>Events · applications · profile</small></div>
    <div><b>OIF teams</b><small>Dashboard · reports · administration</small></div>
  </div>
  <div class="diagram-connector"><span>Role-aware access</span></div>
  <div class="system-capabilities">
    <div><b>Content</b><small>CMS &amp; media</small></div>
    <div><b>Engagement</b><small>Events &amp; mentorship</small></div>
    <div><b>Operations</b><small>People &amp; enquiries</small></div>
    <div><b>Stewardship</b><small>Giving &amp; finance</small></div>
  </div>
  <div class="diagram-connector"><span>Controlled records</span></div>
  <div class="system-foundation"><b>Django platform</b><span>Accounts · database · audit · notifications · integrations</span></div>
</figure>
"""


SETUP_ROADMAP = """
<figure class="manual-diagram roadmap" aria-label="Initial setup roadmap">
  <figcaption><span>Launch sequence</span><strong>Build the operating foundation in order</strong></figcaption>
  <div class="roadmap-steps">
    <div><i>01</i><b>Secure</b><small>Environment, database, HTTPS</small></div>
    <div><i>02</i><b>Identify</b><small>Brand profile and contacts</small></div>
    <div><i>03</i><b>Authorize</b><small>Accounts, roles, least privilege</small></div>
    <div><i>04</i><b>Publish</b><small>Programs, policies, events</small></div>
    <div><i>05</i><b>Verify</b><small>Payments, email, backups</small></div>
  </div>
</figure>
"""


ACCESS_DIAGRAM = """
<figure class="manual-diagram access-chain" aria-label="Role and capability access chain">
  <figcaption><span>Access model</span><strong>Authentication answers who; capabilities answer what</strong></figcaption>
  <div class="access-flow">
    <div><i>1</i><b>Account</b><small>Identity is authenticated</small></div><em>→</em>
    <div><i>2</i><b>Role</b><small>Approved responsibility</small></div><em>→</em>
    <div><i>3</i><b>Capabilities</b><small>Named permissions</small></div><em>→</em>
    <div><i>4</i><b>Protected action</b><small>View or mutation allowed</small></div>
  </div>
  <p class="diagram-note"><b>Governance rule:</b> a technical permission never replaces organizational authorization, evidence, or review.</p>
</figure>
"""


PUBLISHING_DIAGRAM = """
<figure class="manual-diagram publishing-loop" aria-label="Content publishing workflow">
  <figcaption><span>Publishing control</span><strong>Every public change follows a visible quality loop</strong></figcaption>
  <div class="publishing-steps">
    <div><i>01</i><b>Prepare</b><small>Purpose, copy, imagery</small></div>
    <div><i>02</i><b>Review</b><small>Accuracy, consent, links</small></div>
    <div><i>03</i><b>Publish</b><small>Save through the CMS</small></div>
    <div><i>04</i><b>Verify</b><small>Inspect the public page</small></div>
    <div><i>05</i><b>Maintain</b><small>Update, hide, or archive</small></div>
  </div>
</figure>
"""


DONATION_DIAGRAM = """
<figure class="manual-diagram donation-flow" aria-label="Verified online donation lifecycle">
  <figcaption><span>Verified giving</span><strong>A donation becomes successful only after trusted confirmation</strong></figcaption>
  <div class="donation-steps">
    <div><i>1</i><b>Donor submits</b><small>Pending record + reference</small></div><em>→</em>
    <div><i>2</i><b>Paystack</b><small>Secure hosted payment</small></div><em>→</em>
    <div><i>3</i><b>Verify</b><small>Callback or signed webhook</small></div><em>→</em>
    <div><i>4</i><b>Reconcile</b><small>Amount · currency · reference</small></div><em>→</em>
    <div><i>5</i><b>Record</b><small>Receipt + accounting journal</small></div>
  </div>
  <div class="donation-branch"><b>Verification fails</b><span>Keep pending or mark failed · investigate · never infer success</span></div>
</figure>
"""


FINANCE_DIAGRAM = """
<figure class="manual-diagram finance-controls" aria-label="Finance control cycle">
  <figcaption><span>Stewardship cycle</span><strong>Evidence, approval, posting, and review reinforce one another</strong></figcaption>
  <div class="control-ring">
    <div><i>1</i><b>Evidence</b><small>Receipt · statement · reference</small></div>
    <div><i>2</i><b>Authorize</b><small>Role · approval · period</small></div>
    <div><i>3</i><b>Post</b><small>Balanced journal · fund</small></div>
    <div><i>4</i><b>Reconcile</b><small>Cash · bank · gateway</small></div>
    <div><i>5</i><b>Review</b><small>Reports · audit · exceptions</small></div>
  </div>
</figure>
"""


def insert_after_heading(document: str, heading_id: str, visual: str) -> str:
    section_marker = f'<section id="{heading_id}" class="level1">'
    section_start = document.find(section_marker)
    if section_start < 0:
        raise RuntimeError(f"Could not find chapter section: {heading_id}")
    start = document.find("<h1>", section_start)
    if start < 0:
        raise RuntimeError(f"Could not find chapter heading: {heading_id}")
    end = document.find("</h1>", start)
    if end < 0:
        raise RuntimeError(f"Malformed heading: {heading_id}")
    end += len("</h1>")
    return document[:end] + visual + document[end:]


def chromium_binary() -> str:
    for candidate in ("chromium", "chromium-browser", "google-chrome"):
        path = shutil.which(candidate)
        if path:
            return path
    snap = Path("/snap/bin/chromium")
    if snap.exists():
        return str(snap)
    raise RuntimeError("Chromium is required to build the manual PDF.")


def build() -> None:
    for path in [*SOURCES, DOCS_DIR / "admin_manual.css"]:
        if not path.exists():
            raise FileNotFoundError(path)

    render_html = DOCS_DIR / ".manual-render.html"
    render_pdf = DOCS_DIR / ".OIF_PLATFORM_ADMINISTRATOR_MANUAL.render.pdf"
    try:
        pandoc = subprocess.run(
            [
                "pandoc",
                *(str(path) for path in SOURCES),
                "--standalone",
                "--section-divs",
                "--toc",
                "--toc-depth=2",
                "--metadata=pagetitle:OIF Platform Administrator Manual",
            ],
            check=True,
            cwd=PROJECT_DIR,
            capture_output=True,
            text=True,
        )

        document = pandoc.stdout
        styles = (DOCS_DIR / "admin_manual.css").read_text(encoding="utf-8")
        styles = styles.replace("__COVER_IMAGE__", asset("cover-collaboration.jpg"))
        document = document.replace("</head>", f"<style>\n{styles}\n</style>\n</head>")

        visuals = {
            "administrator-mandate": PLATFORM_DIAGRAM,
            "initial-system-setup": SETUP_ROADMAP,
            "user-and-access-administration-runbook": ACCESS_DIAGRAM,
            "public-website-and-cms-runbook": photo_feature(
                "virtual-conference.jpg",
                "Public experience",
                "Content is an operational responsibility",
                "Use the CMS to tell a coherent story, then verify every change where visitors will experience it.",
            ) + PUBLISHING_DIAGRAM,
            "event-administration-runbook": photo_feature(
                "leadership-conference.jpg",
                "Event operations",
                "From invitation to attendance",
                "Clear public information and disciplined registration management create a dependable participant experience.",
            ),
            "application-and-mentorship-runbook": photo_feature(
                "mentorship-cohort.jpg",
                "People development",
                "Progress is personal and measurable",
                "Application decisions, mentor assignment, and session progress should remain accurate, timely, and respectful.",
            ),
            "enquiry-and-partnership-runbook": photo_feature(
                "humanitarian-outreach.jpg",
                "Community relationships",
                "Every enquiry represents trust",
                "Respond with ownership, protect personal information, and preserve a clear operational trail.",
            ),
            "donation-and-paystack-runbook": DONATION_DIAGRAM,
            "messaging-runbook": photo_feature(
                "volunteer-planning.jpg",
                "Responsible communications",
                "Plan the audience before pressing send",
                "Purpose, consent, provider readiness, and post-send review are part of every campaign.",
            ),
            "finance-and-accounting-runbook": FINANCE_DIAGRAM,
            "module-reference": photo_feature(
                "hadassah-workshop.jpg",
                "Reference library",
                "How the platform fits together",
                "The module and role references that follow connect daily procedures to system behavior and access boundaries.",
            ),
        }
        for heading_id, visual in visuals.items():
            document = insert_after_heading(document, heading_id, visual)

        render_html.write_text(document, encoding="utf-8")
        render_pdf.unlink(missing_ok=True)
        subprocess.run(
            [
                chromium_binary(),
                "--headless",
                "--no-sandbox",
                "--disable-gpu",
                "--allow-file-access-from-files",
                "--no-pdf-header-footer",
                f"--print-to-pdf={render_pdf}",
                render_html.resolve().as_uri(),
            ],
            check=True,
            cwd=PROJECT_DIR,
        )

        deadline = time.monotonic() + 45
        previous_size = -1
        stable_checks = 0
        while time.monotonic() < deadline:
            if render_pdf.exists():
                size = render_pdf.stat().st_size
                stable_checks = stable_checks + 1 if size == previous_size else 0
                previous_size = size
                if size > 100_000 and stable_checks >= 2:
                    break
            time.sleep(0.5)
        else:
            raise RuntimeError("Chromium did not produce a complete PDF within 45 seconds.")

        pdf_info = subprocess.run(
            ["pdfinfo", str(render_pdf)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        pages_line = next(line for line in pdf_info.splitlines() if line.startswith("Pages:"))
        page_count = int(pages_line.split(":", 1)[1])
        if page_count < 20:
            raise RuntimeError(f"Render validation failed: only {page_count} page(s).")

        render_pdf.replace(OUTPUT)
        print(f"Built {OUTPUT} ({page_count} pages)")
    finally:
        render_html.unlink(missing_ok=True)
        render_pdf.unlink(missing_ok=True)


if __name__ == "__main__":
    build()
