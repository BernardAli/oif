# Onesimus Impact Foundation Website & Dashboard

A Django application for the Onesimus Impact Foundation (OIF): a public website,
member portal, role-based operations dashboard, CMS, donation flow, and event
engagement system for a youth-led NGO in Accra, Ghana.

The project is built to be practical for day-to-day OIF operations. Public pages
are content-managed, the dashboard is capability-gated by role, media uploads are
first-class, and analytics are rendered with ECharts.

## Highlights

- Premium public website with Home, About, Leadership, Speakers, Programs,
  Program detail, Event detail, Impact, Get Involved, Donate, Gallery, Contact,
  and policy pages.
- Professional mega navigation, responsive footer, and CMS-managed project
  profile.
- Site Content CMS for project identity, logos, favicon, Google fonts, programs,
  resources, speakers, leadership, impact stats, testimonials, gallery images,
  and policies.
- CMS branding controls for organization name, short name, tagline, location,
  contact details, social links, footer summary, title font, and body font.
- Gallery with uploaded images, dashboard delete action, sample media, and a
  professional click-to-expand lightbox with keyboard navigation.
- Comprehensive engagement app with event detail pages, registrations,
  applications, mentorship, partner enquiries, newsletter signup, event sharing,
  Google Calendar links, and Apple Calendar `.ics` export.
- Dashboard tabs, pagination, role-based navigation, ECharts analytics, audit
  trail, donation management, member management, member avatars, and profile
  image upload.
- Password reset flow and password visibility toggles on password fields.
- Paystack Ghana integration with safe demo behavior when API keys are absent.

## Quick Start

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_demo
python manage.py runserver 8010
```

Open:

- Public site: `http://127.0.0.1:8010/`
- Dashboard: `http://127.0.0.1:8010/dashboard/`
- Login: `http://127.0.0.1:8010/accounts/login/`
- Django admin: `http://127.0.0.1:8010/admin/`

If you use Django's default port instead, run `python manage.py runserver` and
open `http://127.0.0.1:8000/`.

Seeded demo accounts use this password:

```text
oifdemo123
```

Common seeded usernames:

```text
admin
globallead / execdir / director
dirprograms / dirops / dircomms / dirpartners
finance / editor / eventmgr
mentor / mentor2 / volunteer / volunteer2
applicant / donor / member1 ... member10
```

## Public Website

The public website is designed as the first screen of the organization, not just
a brochure. It includes:

- A premium homepage hero, upcoming event feature, metrics, programs, leadership
  preview, speakers preview, and donation CTA.
- Separate Leadership and Speakers pages.
- Program listing and detail pages for The Forge, Hadassah Project,
  Humanitarian Wing, Virtual Conferences, and Mentorship Programme.
- Event detail pages with rich sections, registration, share links, Google
  Calendar, Apple Calendar, and `.ics` download.
- Impact page with metrics, testimonials, cohorts, gallery highlights, and
  speaker context.
- Gallery page with CMS-uploaded images and full-screen lightbox expansion.
- Contact, Donate, Get Involved, and editable policy pages.

## Dashboard

The dashboard is role-aware and organized for repeated administrative work.

Core dashboard areas:

- Overview with tabs and role-specific analytics.
- Events and registrations.
- Donations and Paystack-linked giving.
- Applications.
- Mentorship.
- Members and member detail pages.
- Site CMS.
- Enquiries.
- Audit Trail.

Dashboard UX features:

- Tabs where content naturally groups.
- Pagination for large management tables.
- ECharts visualizations.
- Member profile pictures on member detail pages.
- Avatar upload from the account profile and from admin member detail.
- Protected routes based on capabilities, not just raw role names.

## Site Content CMS

The CMS is available at:

```text
/dashboard/content/
```

It manages:

- Project profile: organization name, short name, tagline, founded year,
  location, email, phone, website URL, footer summary, social links.
- Logos: full logo, compact logo mark, favicon.
- Typography: selectable Google fonts for title and body text.
- Programs and downloadable resources.
- Speakers.
- Leadership team.
- Site stats.
- Testimonials.
- Gallery/media images.
- Policies.

The selected profile, logo, favicon, and fonts affect both the public website
and dashboard through the global context processor.

## Roles And Access

Roles are defined in `accounts.models.Role` and mapped to capabilities in
`accounts.models.ROLE_CAPABILITIES`.

Implemented roles include:

- Super Administrator
- Global Lead
- Executive Director
- Director / Staff
- Director of Programmes
- Director of Operations & Volunteer Engagement
- Director of Communications, Media & Digital
- Director of Partnerships & Resource Mobilisation
- Finance / Donations Manager
- Content Editor
- Event Manager
- Mentor
- Volunteer
- Applicant
- Donor
- Member

Views use `capability_required(...)`, keeping permissions centralized and easier
to audit.

## Payments

Donations support:

- Mobile Money / Card through Paystack.
- Bank transfer instructions.
- Demo-success mode when Paystack keys are not configured.
- Donation status pages.
- Email receipts.
- Dashboard reconciliation and status controls.
- Signed Paystack webhook reconciliation when donors do not return to the callback.
- CMS-managed Paystack enablement, public/secret keys, webhook secret, and demo mode.

Configure Paystack in `.env`:

```env
PAYSTACK_SECRET_KEY=sk_test_xxx
PAYSTACK_PUBLIC_KEY=pk_test_xxx
```

Alternatively, an account with `configure_integrations` can use **Site CMS →
Integrations**. Configure the Paystack dashboard webhook with the URL shown on
that screen (`/donations/webhook/`). Pending donations can also be reconciled in
bulk from the Donations dashboard.

## Messaging

The role-aware Messaging Centre supports:

- Email, SMS, WhatsApp, or combined multi-channel campaigns.
- Arkesel and Hubtel SMS providers with selectable sender ID.
- WhatsApp Cloud API text delivery.
- Reusable templates and recipient placeholders.
- All-member, marketing-consent, role, event-registration, newsletter, and
  custom-recipient audiences.
- Per-recipient sent, failed, and skipped delivery records with provider IDs.
- Draft campaigns, immediate delivery, repeat sends, and audit logging.

Communications staff can compose campaigns, leadership can receive reporting
access, and only users with `configure_integrations` can edit provider secrets.
SMS, WhatsApp, Email, and Paystack settings live in **Site CMS → Integrations**.

## Finance, Accounting, and Management Reporting

The finance workspace combines operational cash control with a double-entry
accounting ledger. It includes:

- A configurable chart of accounts with asset, liability, net asset, income,
  and expense classifications.
- Unrestricted, temporarily restricted, and permanently restricted funds.
- Non-overlapping fiscal periods, closing controls, and posting locks.
- Balanced general journals with approval, posting, and auditable reversals.
- Idempotent accounting automation for successful donations and approved
  expenses.
- Account-level budgets by fiscal period and fund, including budget-versus-
  actual variance reporting.
- Bank reconciliation preparation and zero-difference approval controls.
- Trial balance, income and expenditure, statement of financial position,
  operating margin, current ratio, and accounting exception reporting.
- Finance and management-report CSV exports with two-decimal monetary values.

Finance users manage day-to-day records under **Finance & Accounting** and open
formal statements and ledger controls under **Statements & Ledger**.

## Email

Local development defaults to console email output.

For production, configure SMTP:

```env
DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.your-provider.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-username
EMAIL_HOST_PASSWORD=your-password
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=Onesimus Impact Foundation <hello@onesimusimpact.org>
OIF_NOTIFY_EMAIL=hello@onesimusimpact.org
```

Email is used for password resets, donation receipts, applications, contact
messages, and partner enquiries.

## Media

Media uploads are stored under `media/` in development.

Supported upload areas:

- Project logos, logo marks, and favicon.
- Member avatars.
- Event flyers.
- Program images.
- Speaker photos.
- Leadership photos.
- Testimonial photos.
- Gallery images.
- Program resource files.

When `DEBUG=True`, media is served by Django via `oif_site.urls`.

## Technology

- Python
- Django
- SQLite by default
- PostgreSQL via `DATABASE_URL`
- Pillow for media uploads
- Vanilla JavaScript for tabs, navigation, password toggles, sharing, countdowns,
  and gallery lightbox
- ECharts for dashboard analytics
- Paystack for payments
- Custom responsive CSS

## Environment Variables

The app runs locally with SQLite and no extra configuration. Production should
set at least:

```env
DJANGO_SECRET_KEY=replace-with-a-long-random-string
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
DATABASE_URL=postgres://user:password@host:5432/dbname
```

Optional production hardening is auto-enabled when `DJANGO_DEBUG=False`; see
`oif_site/settings.py` and `.env.example`.

Simulated successful donations are controlled separately. Keep
`PAYSTACK_DEMO_MODE=False` outside an intentional demo environment. If Paystack
is unavailable while demo mode is disabled, online donations fail closed rather
than being recorded as successful.

## Project Layout

```text
oif_site/      settings, root URLs, sitemap wiring, notification helpers
accounts/     custom user model, roles, auth, profile, password reset
pages/        public pages, CMS content models, policies, gallery, seed data
engagement/   event registration, applications, mentorship, contact, newsletter
donations/    donation model, Paystack client, receipt/status flow
dashboard/    role-based admin dashboard, CMS, analytics, audit log
templates/    public, dashboard, accounts, engagement, donation templates
static/css/   responsive site and dashboard design system
media/        local uploaded/generated development media
```

Dashboard reporting and cash-balance calculations live in
`dashboard/reporting.py`. New reporting and accounting calculations should stay
there so the HTTP view layer remains focused on request handling.

## Useful Commands

```sh
python manage.py migrate
python manage.py seed_demo
python manage.py createsuperuser
python manage.py runserver 8010
python manage.py test
python manage.py collectstatic
```

## Tests

Run:

```sh
python manage.py test
```

Coverage includes public page rendering, role capabilities, dashboard access,
events, applications, donations, member management, CMS profile/branding,
gallery lightbox markup, gallery delete behavior, password reset, avatar upload,
contact/partner/newsletter flows, email notifications, and audit logging.

## Deployment Notes

The app is suitable for PythonAnywhere or any standard Django host.

Recommended production checklist:

- Set `DJANGO_DEBUG=False`.
- Set a strong `DJANGO_SECRET_KEY`.
- Configure `DJANGO_ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`.
- Use PostgreSQL through `DATABASE_URL`.
- Configure SMTP email.
- Configure Paystack keys.
- Set `PAYSTACK_DEMO_MODE=False`.
- Run `python manage.py check --deploy` and resolve every error.
- Run `python manage.py makemigrations --check --dry-run`.
- Run `python manage.py test`.
- Run `python manage.py migrate`.
- Run `python manage.py collectstatic`.
- Configure persistent media storage/backups.
- Replace placeholder policies and sample media with final organization assets.

The included `Dockerfile` runs the project with Gunicorn, the `Procfile`
supports process-based hosts, and `.github/workflows/test.yml` runs checks,
migration drift detection, and the full test suite for pushes and pull requests.

## Notes

- Sample gallery images are included for development/demo use and can be managed
  from the CMS.
- Policy pages are editable placeholders until final legal copy is supplied.
- Third-party costs such as hosting, domain, email, SSL, PostgreSQL, and Paystack
  fees are external to the application.
