# OIF Platform Module and Operations Manual

## 1. Purpose and audience

This manual explains how the Onesimus Impact Foundation (OIF) platform is
organized, what each module does, how the modules exchange information, and how
an operator should use the principal workflows.

It is intended for:

- OIF administrators and directors;
- programme, events, communications, partnerships, and finance teams;
- content editors and member-support personnel;
- developers, maintainers, auditors, and deployment operators.

For access rights and instructions for each user role, see
[`ROLES_MANUAL.md`](ROLES_MANUAL.md).

## 2. Platform at a glance

The platform is a server-rendered Django application with one shared database.
It combines five business modules:

| Module | Main responsibility | Primary users |
|---|---|---|
| `accounts` | Identity, login, profiles, roles, and capabilities | Everyone |
| `pages` | Public website and content-managed information | Visitors and content team |
| `engagement` | Events, applications, mentorship, enquiries, and newsletter | Visitors, members, programme teams |
| `donations` | Giving, Paystack verification, receipts, and donor history | Donors and finance team |
| `dashboard` | Operations, reporting, messaging, finance, CMS, and audit | Authenticated users and staff |

Shared project services live in `oif_site`. HTML is in `templates`, styling is
in `static/css/site.css`, and development uploads are stored in `media`.

The public website starts at `/`. The authenticated workspace starts at
`/dashboard/`. Django's technical administration interface is at `/admin/` and
should normally be used only by a Super Administrator.

## 3. Common concepts

### 3.1 Authentication

Visitors can browse published public content, submit contact and partnership
forms, subscribe to the newsletter, register for an event as a guest, and make
a donation.

An account is required to:

- maintain a personal profile;
- see personal registrations, applications, mentorship, and donations;
- cancel a member event registration;
- submit an application;
- use any staff capability.

Public signup always creates a `Member`. Staff roles must be assigned
internally. Password-reset email is available from the login screen.

### 3.2 Authorization

The platform authorizes actions through named capabilities rather than by
scattering role-name checks through the code. A role supplies a set of
capabilities; views then require the relevant capability.

This creates three practical levels:

1. **Personal access** — authenticated users see their own activity.
2. **Organization read access** — capabilities such as `view_donations`,
   `view_message_reports`, or `view_org_analytics` expose organization-wide
   information.
3. **Operational write access** — capabilities such as `manage_events`,
   `manage_donations`, or `manage_content` allow changes.

A missing navigation link is not the security boundary. The server checks
capabilities again when a protected URL is requested.

### 3.3 Status-driven records

Many records follow an explicit lifecycle:

- registration: Registered → Attended or Cancelled;
- application: Pending review → Approved or Not selected;
- donation: Pending → Successful or Failed;
- contact message: New → Read → Resolved;
- partner enquiry: New → In review → Engaged → Closed;
- expense: Draft → Approved → Paid, or Void;
- journal: Draft → Posted → Reversed;
- budget: Draft → Approved → Locked;
- bank reconciliation: Draft → Reconciled;
- campaign: Draft → Processing → Sent, Partially sent, or Failed.

Operators should change status through the dashboard actions instead of editing
database records directly. Dashboard actions apply validation, notifications,
accounting automation, and audit logging.

### 3.4 Audit trail

Significant administrative changes create an `AuditLog` entry containing the
actor, action, target, detail, and timestamp. Examples include event changes,
application decisions, donation reconciliation, member role changes, content
changes, campaign sends, integration changes, accounting actions, and exports.

Audit logging is deliberately best-effort: failure to write an audit entry does
not break the user's primary operation. Infrastructure monitoring and database
backups therefore remain necessary.

## 4. Accounts module

### 4.1 Responsibilities

The accounts module owns:

- the custom `User` model;
- usernames and passwords;
- personal and staff roles;
- role-to-capability mapping;
- signup, login, logout, profile editing, and password reset;
- member avatars, professional information, and public-profile preference.

### 4.2 User information

A user can hold a name, username, email, phone number, professional title,
location, avatar, biography, role, marketing preference, public-profile flag,
and Django active/staff flags.

The normal user profile permits changes to:

- first and last name;
- email and phone;
- title and location;
- avatar and biography;
- public-profile preference.

It does not permit a user to change their own role, active status, or staff
status.

### 4.3 Signup and account administration

New public signups:

1. provide a name, username, email, optional phone, and password;
2. must use an email not already assigned to an account;
3. receive the `Member` role;
4. are created **inactive**, pending staff approval, and are not signed in.

Django's authentication backend refuses to authenticate an inactive account, so
a new signup cannot sign in — to the dashboard or anywhere else — until a
member administrator approves them. This is enforced by the framework itself,
not by a separate check in the view layer.

At signup, the platform sends two best-effort notifications: a confirmation to
the new member that their account is pending review, and an internal
notification to the OIF inbox flagging the account for approval. The login
screen shows a specific "pending approval" message (rather than a generic
inactive-account error) if someone tries to sign in before approval.

A user with `manage_members` approves a pending account from **Members**:

1. open the pending member's record (a "Members awaiting approval" work-queue
   entry appears on Overview, and the Members page shows a "Pending approval"
   total and a `status=pending` filter to list them);
2. review the account for legitimacy before approving;
3. open the Admin tab and check **Active account (approved to sign in)**;
4. save.

Only a user with `manage_users` sees the role and Django staff fields. When an
Applicant becomes a Member, or an inactive account is activated, the platform
sends a membership-accepted email containing the sign-in link — this is the
first email that includes one, since the initial pending-approval email
deliberately does not.

Staff-created accounts (added directly through the Members admin form rather
than public self-signup) are not subject to this gate — the administrator
creating the record controls `is_active` directly at creation time.

### 4.4 Passwords and staff safety

- Passwords are never sent in account notification emails.
- Use the password-reset flow rather than asking users to disclose passwords.
- Grant Django `is_staff` only when access to `/admin/` is genuinely required.
- A platform role and Django staff status are separate controls.
- Deactivating a user blocks authentication without deleting their history.

## 5. Pages and public CMS module

### 5.1 Public pages

The public site provides:

- Home;
- About;
- Leadership;
- Speakers;
- Programs & Initiatives overview, six dedicated initiative pages, and legacy
  programme detail;
- Event detail;
- Impact;
- Get Involved;
- Donate;
- Gallery;
- Contact;
- Privacy, Terms, and Donation policies;
- sitemap (including active initiative pages) and `robots.txt`;
- custom 404 and 500 pages.

Only published or active records are intended to appear publicly.

### 5.2 Site branding

`SiteBranding` is a singleton organization profile used by public and dashboard
templates. It controls:

- organization and short names;
- tagline, founded year, and location;
- contact email, phone, and website;
- footer summary;
- full logo, compact logo, and favicon;
- Instagram, LinkedIn, X, YouTube, and Facebook links;
- heading and body Google fonts.

Because branding is global, verify changes on both the public site and
dashboard. Uploaded logo variants should be optimized for the web and remain
legible on light and dark backgrounds.

### 5.3 Programs & Initiatives

The public `/programs/` page is organized into three pillars:

1. **Virtual Conferences**;
2. **Mentorship Program**;
3. **Events**.

The overview cards link to matching tab panels on the same page. Each panel
contains dedicated initiative cards. Selecting an initiative opens its own
public page under `/programs/initiatives/<slug>/`.

Six initiative pages are created automatically by migration:

| Pillar | Dedicated page | Page type |
|---|---|---|
| Virtual Conferences | The Emerging Leader | The Forge virtual conference |
| Virtual Conferences | The Emerging Lady | The Hadassah Project virtual conference |
| Mentorship Program | Forge Mentorship Program | Two-phase mentorship |
| Mentorship Program | Bloom 360 Mentorship Program | Two-phase mentorship for young women |
| Events | Onesimus Community Outreach Initiative (OCOI) | Humanitarian outreach |
| Events | In-Person Events & Gatherings | Event archive |

An initiative stores its pillar, page type, title, URL slug, eyebrow, approved
description, optional frequency badge and hero image, display order, active
state, and optional Phase 1/Phase 2 headings and introductions. An inactive
initiative does not resolve publicly.

#### 5.3.1 Virtual conference pages

The Emerging Leader and The Emerging Lady use the same public layout. Content
differences are data, not separate templates. Each page contains:

- **Upcoming Conference** — one or more upcoming edition records with edition
  label, conference name/theme, description, optional date, main flyer,
  publication state, display order, and optional Google Form registration URL;
- **Speaker/personality flyers** — image and optional caption records attached
  to an edition, limited to four per edition;
- **Past Conferences** — an unlimited archive of past edition records using
  the same name, description, date, flyer, order, and publication fields.

If no upcoming or past record exists, the public page displays a deliberate
"coming soon" or archive-ready state. Do not create invented editions merely
to fill the layout. Add real records as OIF supplies approved themes, dates,
attendance, speaker details, and media.

#### 5.3.2 Mentorship programme pages

Forge Mentorship and Bloom 360 share one mentorship layout:

- Phase 1 displays up to eight numbered session records;
- each session stores a number from 1–8, title, optional track label, optional
  future video URL, display order, and publication state;
- Phase 2 displays one or more track/pairing records with a label, name,
  session count, description, and order.

Forge is seeded with eight session placeholders grouped as Career Development
(Sessions 1–4) and Entrepreneurship (Sessions 5–8), plus Career Development
and Entrepreneurship Phase 2 tracks. Bloom 360 is seeded with eight sequential
session placeholders without required sub-track labels and one one-to-one
mentor-pairing record for Weeks 9–12.

The public **Watch** controls are intentionally disabled and labelled "Coming
soon". A video URL may be stored now for the future learning experience, but
the current website does not embed or play it. Phase 2 scheduling remains an
offline coordinator responsibility; the page does not provide scheduling.

#### 5.3.3 Events and outreach initiative pages

OCOI contains two editable content families:

- SDG focus cards with a UN goal number from 1–17, goal name, OIF contribution
  statement, order, and active state;
- past outreach entries with label, activity name, narrative, optional date,
  image, order, and publication state.

Until OIF approves specific SDGs, the public page states that the priorities
are still being decided. In-Person Events & Gatherings uses the same expandable
archive-entry structure for workshop, networking, venue, date, attendance, and
event-summary content. Both archives accept additional records without a
redesign.

These archive entries are editorial public content. They are not operational
`Event` records and do not accept registrations. See section 6 for the
registration-capable event module.

#### 5.3.4 Managing initiative content

Users with `manage_content` open **Programs** from the dashboard. The page now
has two content layers:

1. **Dedicated public pages** — the six initiative pages. Use **Manage
   content** to add or edit the content family appropriate to that page, and
   **Edit page** to change its identity, introductory copy, hero, phases,
   order, or active state.
2. **Legacy program wings** — records still used by operational events,
   resources, galleries, and mentorship enrollments.

The available **Manage content** sections depend on page type:

| Page type | Managed records |
|---|---|
| Virtual conference | Conference editions and speaker flyers |
| Mentorship program | Phase 1 sessions and Phase 2 tracks/pairing |
| Humanitarian outreach | SDG focus areas and past activities |
| In-person events | Past event/archive entries |

After every change, use **Preview page** and verify images, wording, links,
ordering, publication state, and mobile presentation. A stored Google Form or
video URL is still external content and must be checked separately.

#### 5.3.5 Legacy programs and resources

Legacy `Program` records represent The Forge, The Hadassah Project,
Humanitarian Wing, Virtual Conferences, and Mentorship Programme. They remain
in place because existing operational events, downloadable resources, gallery
items, and mentorship enrollments reference them.

Each legacy programme has a tagline, headline, description, image, accent,
display order, and active flag. Resources belong to a legacy programme and may
link to an uploaded file or external URL. Its original detail page continues
to show related operational events, resources, and published Gallery images.
Do not delete a legacy programme solely because its new initiative page exists;
deletion can unlink operational records and remove attached resources.

### 5.4 Speakers and leadership

Speakers have a name, role, photograph, featured flag, and display order.
Leadership records have a name, position, title, credentials, biography,
photograph, and display order.

The available leadership positions are Global Lead, Executive Director,
Director, and Company Secretary. Leadership CMS records are public content;
they do not automatically create user accounts or grant matching roles.

### 5.5 Impact content and gallery

Site statistics are short label/value/suffix records used for public metrics.
Testimonials include source, attribution, quotation, photo, publication flag,
and display order. Sources are Conference, Mentorship, and Humanitarian
Outreach.

Gallery images can be associated with a programme and have a caption,
publication flag, and order. The public gallery includes a lightbox. Programme
association also enables relevant images to appear on event pages.

### 5.6 Policies

The CMS manages Privacy Policy, Terms of Use, and Donation Policy records. All
three are seeded automatically by migration with placeholder text, so
`/policy/privacy/`, `/policy/terms/`, and `/policy/donation/` — and the footer
links to them — always resolve, even on a freshly migrated database with no
other content added. `is_placeholder` identifies unfinished legal text. Before
production launch:

- replace placeholder copy with approved text;
- clear the placeholder flag;
- verify headings, links, and contact details;
- have the final policy reviewed by the appropriate adviser.

### 5.7 Content operating procedure

For a normal content update:

1. open the relevant Content Library screen;
2. create or edit the record;
3. upload an appropriately sized asset if needed;
4. set display order and publication/active flags;
5. save and inspect the public page at desktop and mobile widths;
6. check that links and files open;
7. use the audit trail when confirmation of the change is required.

Deletion is permanent at the application level. Avoid deleting records that
should simply be hidden; use active or published flags when available.

### 5.8 Page imagery and page copy

Beyond the record-based content families above (programmes, speakers, gallery,
and so on), two singleton CMS sections give administrators direct control over
every hero photo and every headline/paragraph "writeup" on the public site
that is not already sourced from a program, speaker, leader, testimonial,
gallery, or event record.

**Page imagery** (`Site CMS → Page Photos`) manages the hero, portrait, and
side-panel photo used on every major public page: Home, About, Programs
(three hero photos), Impact, Leadership, Speakers, Gallery, Donate, Contact,
Get Involved (three portraits), and the side photo on the Give, Apply,
Login/password-reset, and Create-account pages — 19 image slots in total.

**Page copy** (`Site CMS → Page Copy`) manages the hero and section
eyebrow/headline/paragraph writeup on the same set of pages, plus the
site-wide footer call-to-action — 85 text fields, grouped by page in the
dashboard editing form so the section stays usable at that scale.

Both sections behave the same way:

- every field is optional;
- until a field is filled in, the public page falls back to its original
  built-in default — the public site cannot go blank or break while these are
  empty;
- the Site CMS overview shows how many of each are customized versus using
  the default, so an administrator can see coverage at a glance;
- changes take effect immediately on save, with no publish/approval step.

This is the mechanism to use for rebranding a headline, swapping a stock hero
photo for real OIF photography, or adjusting marketing copy without a code
change or deployment.

## 6. Events module

This module governs dated, registration-capable operational `Event` records.
It is separate from the conference-edition and past-activity archive content
described in section 5.3. Use an operational Event when visitors must register,
capacity or attendance must be tracked, calendar links are needed, or staff
must communicate with registrants. Use an initiative archive/edition when the
purpose is editorial programme storytelling or a Google Form registration
link supplied by OIF.

### 6.1 Event content

An event can be a Conference, Mentorship Cohort, Humanitarian Outreach, or
Workshop/Gathering. It may contain:

- title and automatically generated unique slug;
- associated programme and theme;
- summary and full description;
- intended audience, outcomes, agenda, and speaker list;
- preparation and accessibility information;
- flyer;
- start date/time;
- location, venue address, and online URL;
- virtual/in-person indicator;
- capacity, where zero means unlimited;
- registration note and contact email;
- publication and registration-open controls.

Published controls public visibility. Registration-open controls whether the
registration form accepts submissions. These flags are independent.

### 6.2 Public event experience

A published event page displays logistics, programme context, related media,
registration information, related events, social sharing, Google Calendar, and
an Apple/standard `.ics` download. Calendar entries use a two-hour event
duration because the data model currently stores only a start time.

For an upcoming event, the page also shows a live countdown to the start time,
a registration status badge ("Registration open", "Filling fast", "Event
full", or "Registration closed" — computed from capacity, active registration
count, and the registration-open flag), and a seat-fill progress meter next to
the capacity figure and again directly above the registration form. These are
computed from existing event and registration data; no extra administrator
input is required beyond capacity and registration-open state being accurate.

### 6.3 Registration

Both members and guests can register. Guests must provide a name and email.
Members use account identity and may provide organization, role/title,
attendance preference, accessibility needs, dietary needs, and a question.

The platform prevents duplicate member/event and guest-email/event records.
Submitting again updates the existing details. Re-registering a cancelled
record restores it to Registered. Capacity counts registered and attended
records, excluding cancellations.

The registration confirmation email includes the event date, location,
attendance mode, event URL, and calendar URL.

### 6.4 Event administration

Users with `manage_events` can:

- create and edit events;
- publish/unpublish;
- open/close registration;
- inspect upcoming and archived events;
- see capacity, fill rate, attendance rate, role mix, and registration timeline;
- change a registration to Registered, Attended, or Cancelled;
- initiate an event-recipient campaign if they also have `send_messages`.

Before opening registration, verify capacity, contact email, venue/online link,
accessibility text, and public visibility. After an event, mark attendance so
reporting reflects actual participation. The registration data model also
contains check-in time and administrative notes, but the current event
dashboard action edits status only.

## 7. Applications and mentorship module

### 7.1 Applications

Authenticated users can apply as:

- Mentor;
- Volunteer;
- Mentee;
- Speaker.

An application records the type, area of interest, motivation, status,
reviewer, and review time. Submission sends a confirmation to the applicant and
an internal notification.

A reviewer with `manage_applications` may approve or reject. The applicant is
notified when the decision changes. Approval automatically promotes a Member or
Applicant to Mentor for a mentor application, or Volunteer for a volunteer
application. Mentee and Speaker approval do not automatically change roles.

### 7.2 Mentorship

This section describes participant enrollment and progress tracking. The eight
public curriculum session cards and Phase 2 track descriptions under Programs
& Initiatives are CMS content (section 5.3.2); they do not automatically create
enrollments, schedule mentor meetings, or update a participant's progress.

An enrollment connects a mentee to an optional mentor and programme. It records
the cohort, current phase, completed sessions, and total sessions.

Phases are:

- Phase 1 — Recorded Sessions;
- Phase 2 — Live Sessions;
- Completed.

Progress is calculated as completed sessions divided by total sessions. The
default plan is 12 sessions.

Users with `manage_mentorship` can create and update all enrollments. Mentors
with `view_mentees` see enrollments assigned to them. A member sees their own
enrollment. Assignment viewers can see their own mentorship assignment on the
overview.

Recommended process:

1. review and approve the relevant application;
2. create the enrollment;
3. choose the mentee, mentor, programme, and cohort;
4. update session counts regularly;
5. advance the phase only when its requirements are complete;
6. set Completed at the end of the programme.

## 8. Enquiries and newsletter module

### 8.1 Contact messages

The public contact form creates a message with New status and sends
best-effort notifications to the internal inbox and the sender. A hidden
honeypot field rejects basic automated spam.

Users with `manage_contact` can move messages between New, Read, and Resolved.
The last operator is stored as `handled_by`.

The Contact page also shows an embedded location map built from the
organization's location text (no separate map configuration is required), a
response-time expectation next to the send button, and a dedicated hero photo
— all editable through Page Copy and Page Photos (5.8) without a code change.

### 8.2 Partnership enquiries

The Get Involved flow accepts Partner, Sponsor, and Institutional Donor
enquiries. The partnerships lifecycle is:

New → In review → Engaged → Closed.

The Enquiries page may be visible to contact managers, but changing partnership
status specifically requires `manage_partners`.

### 8.3 Newsletter

Newsletter signup is public. Email is unique. Submitting an existing address
reactivates the subscription and updates the name. Active subscribers can be
selected as a Messaging audience.

Consent must be respected. General member campaigns should use the Marketing
opt-ins audience when the communication is promotional rather than necessary
for service delivery.

## 9. Donations module

### 9.1 Donation information

A donation records:

- optional linked user;
- donor name and email;
- amount and currency;
- Mobile Money, Card, or Bank Transfer channel;
- Pending, Successful, or Failed status;
- generated transaction reference;
- campaign, donor note, and recurring intention;
- whether a receipt was sent.

The recurring flag records intent; it does not create an automated Paystack
subscription.

### 9.2 Online payment flow

The normal Paystack flow is:

1. the donor submits the form;
2. the application creates a Pending donation with an `OIF-...` reference;
3. Paystack returns an authorization URL;
4. the donor completes payment;
5. the callback verifies the transaction;
6. reference, amount, currency, and optional metadata donation ID must match;
7. the donation becomes Successful;
8. a receipt is attempted once;
9. an idempotent accounting journal is attempted.

The signed webhook performs the same reconciliation when the browser does not
return to the callback. Webhooks accept only a valid HMAC signature and
`charge.success` events.

### 9.3 Demo and failure behavior

When Paystack is unavailable:

- if demo mode is explicitly enabled, the donation is recorded as Successful;
- if demo mode is disabled, online giving fails closed and the donation becomes
  Failed.

Demo mode must be disabled in production. Bank transfers require an operational
offline verification process; selecting the Bank channel alone is not evidence
that funds arrived.

### 9.4 Privacy and access

A donation status page is visible only when:

- its reference is remembered in the donor's current session;
- it belongs to the authenticated user; or
- the user has organization-wide donation access.

Finance readers can inspect organization-wide donations. Donation managers can
verify with Paystack, change status, and reconcile up to 100 pending referenced
donations per bulk run.

Manual success should be used only after independent evidence of settlement.
Changing a Successful donation back to another state does not automatically
reverse its accounting journal.

## 10. Messaging module

### 10.1 Channels and providers

Campaigns support Email, SMS, WhatsApp, or all three. Integrations include:

- Django email backend;
- Arkesel SMS;
- Hubtel SMS;
- WhatsApp Cloud API.

Provider secrets are stored in singleton integration settings when CMS
configuration is selected. Secret fields preserve the current value when an
empty edit form is submitted.

### 10.2 Audiences

Available audiences are:

- all active members/accounts;
- users with marketing consent;
- users in a selected role;
- non-cancelled registrants for a selected event, including guests;
- active newsletter subscribers;
- custom recipients, one email or phone per line.

Supported message placeholders are `{name}`, `{first_name}`, `{email}`,
`{phone}`, and `{org_name}`. An invalid or unknown placeholder causes the
original text to be used, so preview content carefully.

### 10.3 Campaign lifecycle and delivery

A sender can create a reusable template or campaign, save it as Draft, send it
immediately, or resend it from the detail page. Each channel/recipient pair
creates a delivery record:

- Sent: provider accepted the message;
- Failed: provider/backend raised an error;
- Skipped: the recipient lacked an address for that channel.

Campaign status becomes Sent, Partially sent, or Failed based on results.
Delivery reporting records provider name, reference, error, and send time.

Campaign delivery runs synchronously in the web request. For a large audience:

- split campaigns into manageable groups;
- avoid repeated clicks while the request is running;
- inspect delivery results before retrying;
- understand that resending creates another set of deliveries and can duplicate
  messages to successful recipients.

Only integration administrators should change credentials. Campaign senders
should report configuration failures rather than attempting to obtain secrets.

## 11. Dashboard and reporting module

### 11.1 Overview

Every authenticated user has an Overview. It includes personal registration,
giving, and application counts, upcoming published events, and role-dependent
widgets.

Organization analytics, work queues, mentee counts, mentorship assignments, and
finance summaries appear only when the user's capabilities permit them.

### 11.2 Reports

The Reports area builds sections independently according to access:

- executive;
- finance;
- events;
- people;
- content;
- engagement.

Reports accept a date range and support CSV export. If the start date is after
the end date, the application swaps them. Default reporting covers the previous
365 days.

CSV export is an operational data extract. Store it securely, share it only
with authorized recipients, and delete unnecessary copies.

### 11.3 Analytics

ECharts renders donation trends and channels, member growth, registrations by
programme, application status, event attendance, member engagement, campaign
results, and finance charts.

The `/dashboard/api/analytics/` endpoint is authenticated and filters panels by
capability. Every user receives personal giving history; organization panels
require organization analytics access.

## 12. Finance and accounting module

### 12.1 Operational finance

The Finance & Accounting workspace contains donations, expenses, cash accounts,
and cash movements.

Expense categories include programmes, events, mentorship, outreach,
operations, media, technology, administration, and other. Approved and Paid
expenses are recognized as posted operational expenditure. Supporting receipts
can be uploaded.

Cash accounts represent cash on hand, bank accounts, mobile-money wallets,
payment gateways, savings/reserves, or other accounts. They include opening and
statement balances, reconciliation date, active state, and controls for
accepting donations or paying expenses.

Cash movements are Money in, Money out, or Transfer. Only Posted movements
affect calculated cash balances. Transfers require a different destination
account in the same currency.

### 12.2 Double-entry ledger

The Statements & Ledger area contains:

- ledger accounts;
- funds;
- fiscal periods;
- journals and journal lines;
- budgets and budget lines;
- bank reconciliations;
- financial statements and accounting health checks.

Default accounts are created when accounting is first opened:

| Code | Account |
|---|---|
| 1000 | Cash and bank |
| 1100 | Paystack clearing |
| 1200 | Accounts receivable |
| 2000 | Accounts payable |
| 3000 | Unrestricted net assets |
| 3100 | Restricted net assets |
| 4000 | Donation income |
| 4100 | Grant and partnership income |
| 5000–5400 | Programme, event, operations, administration, and charge expenses |

A General Fund is also created.

### 12.3 Funds and fiscal periods

Funds may be unrestricted, temporarily restricted, or permanently restricted.
Record donor and restriction details when applicable.

Fiscal periods cannot overlap. A journal cannot be posted into a Closed period.
Closing a period therefore acts as a posting lock; reopen only under an
authorized correction procedure.

### 12.4 Journals

A journal is valid for posting when:

- it is Draft;
- it has at least one line;
- total debits equal total credits and are greater than zero;
- each line uses either debit or credit, not both;
- amounts are non-negative;
- accounts permit direct posting;
- the fiscal period is open.

Posted journals are corrected through reversal. Reversal creates and posts a
new entry with debit/credit sides exchanged, then marks the original Reversed.
Do not delete or directly edit posted journals.

Successful donations automatically debit Paystack clearing and credit Donation
income. Approved expenses debit the mapped expense account and credit Cash, or
Accounts payable if not Paid. Source uniqueness prevents a second automated
journal for the same donation or expense.

### 12.5 Budgets

A budget belongs to a fiscal period and optional fund. Each account may appear
only once in a budget. Amounts cannot be negative. The workflow is Draft →
Approved → Locked, with an available return-to-Draft action for authorized
correction.

Variance reporting compares income and expense actuals with budget lines.

### 12.6 Bank reconciliation

A reconciliation compares:

`book balance` with `statement balance + outstanding deposits - outstanding payments + adjustments`.

Approval is blocked unless the difference is exactly `0.00`. Approval updates
the cash account's statement balance and last-reconciled date.

### 12.7 Statements and controls

The platform calculates:

- trial balance;
- income and expenditure;
- assets, liabilities, and net assets;
- surplus/deficit;
- budget versus actual;
- operating margin and current ratio in management reporting;
- accounting exceptions such as unbalanced drafts, unreconciled accounts, and
  successful donations or posted expenses without source journals.

The finance team should review accounting health after reconciliation and
before closing a reporting period.

## 13. Notifications

Transactional email is used for:

- account registration and membership acceptance;
- event registration;
- application receipt and decisions;
- contact and partnership receipt;
- donation receipts;
- password resets.

These emails are best-effort. A mail failure does not roll back the triggering
web operation. The console backend prints email locally; production requires a
working SMTP backend. Operators should monitor mail delivery independently.

## 14. Configuration and integrations

Application configuration is read from environment variables. Integration
administrators can optionally manage messaging and Paystack values through the
dashboard.

Paystack uses either:

- environment values; or
- CMS configuration when `paystack_use_cms_configuration` is enabled.

Required production controls include:

- `DJANGO_DEBUG=False`;
- a strong `DJANGO_SECRET_KEY`;
- correct allowed hosts and CSRF origins;
- production database credentials;
- SMTP credentials;
- Paystack live/test credentials appropriate to the environment;
- `PAYSTACK_DEMO_MODE=False`;
- persistent media storage and backups.

Never place production credentials in source control, screenshots, audit
details, campaign text, or support messages.

## 15. Media and file handling

Uploads include branding, avatars, events, programmes, resources, speakers,
leadership, testimonials, gallery images, expenses, and cash-movement
attachments.

The configured request/upload memory limit is 5 MB; larger uploads may stream to
a temporary file, but operators should still optimize media. Uploaded files are
not a substitute for a document archive. Production deployments require:

- persistent media storage;
- access restrictions appropriate to financial attachments;
- malware/content checking as operational policy;
- backups and restore testing;
- retention and deletion procedures.

## 16. Maintenance and deployment

Supported deployment paths include PythonAnywhere and a Docker/Gunicorn image.
The application supports MySQL, database URLs, and SQLite fallback.

Normal release checks are:

```sh
python manage.py check --deploy
python manage.py makemigrations --check --dry-run
python manage.py test
python manage.py migrate
python manage.py collectstatic --noinput
```

The repository also provides `python manage.py seed_demo` for disposable local
sample data. Never run it against production.

Before a release:

1. back up the database and media;
2. review configuration and demo-mode flags;
3. run checks and tests;
4. apply migrations;
5. collect static files;
6. perform public, login, dashboard, email, and payment smoke tests;
7. review error logs after deployment.

## 17. Troubleshooting guide

### A newly registered member cannot sign in

This is expected: new self-signups are created inactive pending approval, and
Django refuses to authenticate an inactive account. Confirm the account exists
under Members, filter by "Pending approval", open the record, and check
**Active account (approved to sign in)** on the Admin tab. The member receives
a membership-accepted email with the sign-in link once approved. This does not
apply to accounts created directly by an administrator through the Members
form, which are active immediately unless the administrator leaves the Active
account box unchecked.

### A user cannot see a dashboard function

1. Confirm they are logged in and active.
2. Check their assigned role.
3. Check whether that role has the required capability in the role manual.
4. Distinguish `manage_members` from `manage_users`.
5. Do not solve the issue by granting Super Administrator unless full access is
   intended.

### An event is missing publicly

Check `is_published`, start date, programme state, and the URL slug. If
registration is missing but the page is visible, check `registration_open` and
capacity.

### A Paystack donation remains Pending

1. Confirm Paystack is enabled and credentials are for the correct environment.
2. Open the donation and run Verify.
3. Check reference, amount, currency, and metadata matching.
4. Run bulk reconciliation if several callbacks were missed.
5. Inspect webhook URL and signature-secret configuration.
6. Never mark Successful merely to clear the queue without settlement evidence.

### A receipt or notification was not received

Check the stored recipient address, email backend, SMTP credentials, provider
logs, spam filtering, and application logs. Remember that notification failure
does not undo the underlying registration, application, or donation.

### A campaign has failures

Inspect individual delivery errors. Check channel enablement, provider
credentials, phone formatting, missing addresses, sender ID, and provider
quota. Retry deliberately because resend can duplicate prior successes.

### Accounting will not post

Check that the journal balances above zero, lines use valid posting accounts,
the period is open, and no source journal already exists. For reconciliation,
the difference must be exactly zero.

### Cash and ledger balances differ

Cash movements and general-ledger journals are related operational systems but
are not automatically identical in every workflow. Confirm movement status,
opening balances, transfer destinations, source journals, clearing entries,
and the selected reporting period/fund.

## 18. Data stewardship

The platform stores personal, engagement, communications, and financial data.
Operators must:

- grant least-privilege roles;
- use organization-wide exports only for authorized purposes;
- avoid copying sensitive data into unsecured files;
- respect marketing consent;
- keep payment credentials and financial attachments confidential;
- deactivate accounts when access is no longer required;
- preserve audit and accounting history;
- follow OIF retention, privacy, incident-response, and backup policies.
