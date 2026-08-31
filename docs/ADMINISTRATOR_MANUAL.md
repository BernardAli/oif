---
title: "OIF Platform Administrator Manual"
subtitle: "Complete Administration, Operations, Access, Finance, and Governance Handbook"
author: "Onesimus Impact Foundation"
date: "21 August 2026"
lang: "en"
---

\newpage

# About this handbook

## Purpose

This handbook is the complete operating reference for administrators of the
Onesimus Impact Foundation (OIF) platform. It explains how to administer the
organization's website, accounts, programmes, events, engagement, donations,
communications, finance, reporting, integrations, security, and technical
operations.

The handbook combines three layers of guidance:

1. **Administrator runbooks** — what an administrator should do and in what
   order.
2. **Module reference** — how every functional area works, including record
   lifecycles and troubleshooting.
3. **Role reference** — what every role can access and how access should be
   assigned and reviewed.

The final two references are incorporated in full into the PDF edition. The
maintained source files are `MODULES_MANUAL.md` and `ROLES_MANUAL.md`.

## Intended readers

This handbook is written primarily for:

- Super Administrators;
- Executive Directors and authorized directors;
- system owners and deployment operators;
- finance, content, event, communications, and member administrators;
- auditors and governance reviewers.

Not every administrator should perform every procedure. The role and capability
rules in this handbook always apply.

## Document control

| Item | Value |
|---|---|
| Document | OIF Platform Administrator Manual |
| Edition | 1.3 |
| Effective date | 29 August 2026 |
| System | Onesimus Impact Foundation Django Platform |
| Classification | Internal operating documentation |
| Review trigger | Role, workflow, integration, security, or deployment change |
| Recommended review | At least every six months |

### Changes in edition 1.3

- The public Programs mega-navigation and dashboard now follow the same three
  pillars. Dashboard content is separated into Virtual Conferences, Mentorship
  Program, Events, and Legacy Program Wings tabs.
- Operational Event creation/editing now uses a four-step wizard: Basics,
  Logistics, Public Details, and Review & Publish.
- Each operational Event now has a structured Speakers & Facilitators roster
  with manual profile creation, picture upload, contribution type, role,
  organization, session topic, biography, profile link, ordering, and public
  visibility controls.
- PythonAnywhere deployment checks now include migration-drift detection and
  consistent virtual-environment selection. Media guidance explicitly covers
  event-contributor pictures.

### Changes in edition 1.2

- The Programs page is now organized around Virtual Conferences, Mentorship
  Program, and Events, with six seeded dedicated initiative pages.
- The Programs dashboard now manages conference editions and speaker flyers,
  eight-session mentorship curricula and Phase 2 tracks, SDG focus cards, and
  expandable outreach/in-person event archives.
- Programme initiative archives are documented separately from operational
  Events, which continue to manage capacity, registrations, attendance,
  calendars, and event-recipient messaging.

### Changes in edition 1.1

- New member sign-ups now require staff approval before they can sign in (an
  account-activation gate, not a role change) — see "User and access
  administration runbook" and MODULES_MANUAL.md section 4.3.
- Two new site-wide CMS sections, Page Photos and Page Copy, put every
  remaining public-site hero photo and headline/paragraph writeup under
  administrator control — see "Public website and CMS runbook" and
  MODULES_MANUAL.md section 5.8.
- Privacy, Terms, and Donation policies are now seeded automatically so their
  public pages and footer links never 404 on a fresh deployment.
- The public event detail page adds a live countdown, a registration status
  indicator, and a seat-fill meter; programme detail pages show a full photo
  gallery instead of a single image; the Contact page adds a location map.

## Terminology

| Term | Meaning |
|---|---|
| Administrator | A person granted one or more operational capabilities |
| Super Administrator | The platform role with every defined capability |
| Django Admin | The technical `/admin/` interface, distinct from the OIF dashboard |
| Dashboard | The role-aware workspace at `/dashboard/` |
| CMS | The Site Content management functions in the dashboard |
| Capability | A named permission checked by protected views |
| Public user | A visitor who is not signed in |
| Member | Both a standard platform role and, in general prose, an account holder |
| Production | The live organization environment and data |
| Demo mode | A deliberate simulation mode that can mark donations successful without Paystack |

# Administrator mandate

## Core objectives

An administrator is responsible for keeping the platform:

- accurate;
- available;
- secure;
- appropriately permissioned;
- operationally useful;
- financially controlled;
- auditable;
- compliant with OIF policy and applicable obligations.

Administration is not merely data entry. Every administrative action may affect
public information, participant experience, communications, financial records,
or access to personal data.

## Administrative principles

### Least privilege

Grant the narrowest role that supports a person's authorized work. Do not use
Super Administrator as a convenience role.

### Separation of duties

Where staffing permits, separate preparation, approval, payment, reconciliation,
and review. The application does not enforce a different person for every
finance transition, so OIF's operating policy must supply this control.

### Evidence before status

Do not mark a donation successful, expense paid, application approved, event
attended, or reconciliation complete without appropriate evidence.

### Preserve history

Deactivate accounts instead of deleting them. Reverse posted journals instead
of altering history. Close or hide records when that preserves operational
context better than deletion.

### Verify public changes

After a CMS or event change, inspect the public page and its links. A successful
save confirms database storage, not visual or editorial correctness.

### Protect personal and financial data

Use platform data only for authorized OIF purposes. Keep exports, attachments,
credentials, and delivery reports secure.

## Authority boundaries

A platform capability allows a technical action; it does not replace
organizational authorization. For example:

- `manage_donations` permits a status change but does not itself prove funds
  were received;
- `send_messages` permits a campaign but does not establish lawful consent or
  approve its wording;
- `manage_content` permits publication but does not replace editorial or legal
  approval;
- `manage_users` permits role changes but does not authorize unapproved access.

# Administrator access and navigation

## Main locations

| Area | Path | Purpose |
|---|---|---|
| Public site | `/` | Public-facing website |
| Dashboard | `/dashboard/` | Personal and administrative workspace |
| Account profile | `/accounts/profile/` | Personal profile and avatar |
| Login | `/accounts/login/` | Authentication |
| Password reset | `/accounts/password-reset/` | Self-service password recovery |
| Django Admin | `/admin/` | Technical model administration |
| Sitemap | `/sitemap.xml` | Search-engine sitemap |
| Robots file | `/robots.txt` | Crawler instructions |
| Programs & Initiatives | `/programs/` | Public three-pillar programme overview |
| Programs manager | `/dashboard/programs/` | Initiative pages, structured content, and legacy programme records |
| Event manager | `/dashboard/events/` | Operational events, attendance, analytics, and communications |
| New event wizard | `/dashboard/events/new/` | Four-step operational event creation |

Dashboard navigation adapts to capabilities. Overview, Events, Donations,
Applications, Mentorship, and Profile contain personal information for every
authenticated user. Staff functions appear when the role grants the necessary
capability.

## Recommended administrator browser practices

- Use a supported, updated browser.
- Do not save platform passwords on shared computers.
- Sign out when leaving an unattended device.
- Avoid simultaneous edits to the same record.
- Do not use browser Back to repeat payment, campaign-send, or state-changing
  submissions.
- Treat CSV exports and downloaded financial attachments as confidential.
- Use a separate browser profile for production administration where practical.

# Initial system setup

## Pre-launch sequence

Complete these tasks before the platform is used in production:

1. Configure a strong production secret key.
2. disable debug mode;
3. configure allowed hosts and trusted CSRF origins;
4. configure the production database;
5. configure persistent media storage and backups;
6. configure SMTP and test delivery;
7. configure Paystack and ensure demo mode is off;
8. configure messaging providers only if they will be used;
9. run database migrations and collect static files;
10. create the first Super Administrator;
11. set organization branding and contact details;
12. replace placeholder phone numbers, policies, and sample assets;
13. verify all six Programs & Initiatives pages and replace session/content
    placeholders as approved material becomes available;
14. create or verify legacy programmes, resources, and operational events;
15. review public pages and responsive presentation;
16. test signup, login, password reset, and profile updates;
17. test event registration and email confirmation;
18. test Paystack with the appropriate test environment;
19. open accounting and review the default chart/fund;
20. assign staff roles;
21. run the production checks and complete the launch checklist.

## Organization profile setup

Open **Site CMS** and configure:

- official organization name and short name;
- tagline, founded year, and location;
- monitored contact email and phone;
- public website URL;
- footer description;
- social URLs;
- full logo, compact mark, and favicon;
- heading and body fonts;
- one coordinated color palette for the public site and dashboard.

The branding form provides 17 palette presets and previews a selection
immediately. Save the form to publish it, then confirm the result on the public
header/footer, browser tab, and dashboard. Check text and controls over both
light and dark sections before considering the palette approved.

## First staff accounts

For each staff member:

1. use an individual account rather than a shared account;
2. confirm the person's name and email;
3. select the role using the role-selection table in this handbook;
4. leave Django staff status disabled unless `/admin/` is required;
5. require the user to set and keep their own password;
6. verify active status;
7. ask the user to confirm their expected dashboard access;
8. document authorization according to OIF policy.

## Initial content setup

Review every public content family:

- programmes;
- Programs & Initiatives pages, including conference editions, mentorship
  sessions/tracks, SDG cards, and event/outreach archives;
- resources;
- speakers;
- leadership;
- statistics;
- testimonials;
- gallery;
- policies;
- events;
- page imagery (Site CMS → Page Photos) — replace placeholder hero photos with
  real OIF photography where available;
- page copy (Site CMS → Page Copy) — replace default headlines/writeups with
  organization-approved wording where the default text should not go live
  as-is.

Use active/published controls deliberately. Remove demonstration content from
production and verify every download and external URL.

## Initial finance setup

1. Open **Statements & Ledger** to create default ledger accounts and the
   General Fund.
2. Review account names, types, and posting controls.
3. Create any additional funds with accurate restrictions.
4. create a non-overlapping fiscal period;
5. create and link operational cash/bank/payment-gateway accounts;
6. record verified opening balances and dates;
7. establish the expense evidence and approval procedure;
8. establish Paystack clearing and bank reconciliation procedures;
9. create budgets if used;
10. export and retain an approved opening configuration report.

# Operating cadence

## Daily checks

An administrator or designated operational owner should review:

- failed logins or infrastructure alerts supplied by the hosting environment;
- new contact messages;
- new partnership enquiries;
- new and pending applications;
- members awaiting approval;
- upcoming event registration counts and capacity;
- Pending or Failed donations;
- receipt-delivery exceptions;
- failed or partially sent campaigns;
- accounting exceptions arising from newly confirmed donations or expenses;
- backup/monitoring alerts.

The exact list should be divided among roles. A Super Administrator need not
personally process every queue.

## Weekly checks

- Review inactive or stale operational queues.
- Reconcile Paystack and relevant cash/bank accounts.
- Ensure recent events have accurate attendance.
- Update mentorship progress.
- review public event and programme information;
- inspect campaign delivery rates and recurring failures;
- inspect accounting health;
- review audit entries for sensitive changes;
- confirm scheduled backups completed.

## Monthly checks

- Reconcile all material cash and bank accounts.
- Review donation, expense, cash, and ledger totals.
- produce management reports for the month;
- review budget variance;
- review membership and engagement trends;
- inspect unsuccessful notifications;
- review active staff accounts and broad roles;
- confirm policy and contact information remains current;
- test a restore or follow the approved backup verification process.

## Quarterly checks

- Perform a formal access review.
- Review Super Administrators and Django staff accounts.
- rotate credentials according to provider/security policy;
- review integration configuration and unused providers;
- review data retention and unnecessary exports;
- inspect audit and finance exceptions;
- review disaster-recovery readiness;
- update this handbook for implemented workflow changes.

## Annual or fiscal-period checks

- Confirm the period contains all expected source transactions.
- resolve unbalanced drafts and unposted source records;
- complete bank reconciliations;
- produce and approve final statements;
- close the fiscal period only after review;
- create the next non-overlapping period;
- establish and approve the new budget;
- archive approved exports and evidence;
- review policies, branding, leadership, and programme information.

# User and access administration runbook

## Creating or accepting an account

Public users can self-register and become Members. A self-registered account
is created inactive and cannot sign in until approved — Django itself refuses
to authenticate an inactive account, so this is a real gate, not a courtesy
notice. Approve a pending member from Members (a "Members awaiting approval"
work-queue item and a "Pending approval" filter make them easy to find):

1. confirm the account appears legitimate;
2. open the record;
3. on the Admin tab, check **Active account (approved to sign in)**;
4. save — the member receives a sign-in email automatically.

When an account is created or accepted internally instead (staff, or a Member
outside the public flow):

- verify identity using the organization's approved process;
- avoid duplicate accounts by checking username and email;
- confirm email and phone spelling;
- assign a role only with authorization;
- activate the account;
- use password reset for secure password creation;
- never email a password.

## Changing a role

Only a user with `manage_users` can edit role and Django staff fields in the
dashboard. Under the implemented mapping, this is the Super Administrator.

Before a role change:

1. obtain authorization;
2. compare current and proposed capabilities;
3. review whether finance, message delivery, member, or audit data will become
   visible;
4. apply the change;
5. verify navigation and one representative protected screen;
6. confirm an audit entry exists;
7. tell the user what responsibilities changed.

Approving a Mentor or Volunteer application can automatically promote a Member
or Applicant. Review these decisions with the same care as a manual role
change.

## Deactivation and offboarding

1. Set the account inactive.
2. remove Django staff/superuser access if present;
3. reassign operational work;
4. rotate any provider credentials known to the person;
5. preserve the account for historical attribution;
6. recover or securely delete local exports according to OIF policy;
7. record completion of the offboarding process.

Do not delete a person merely to remove access.

## Access incident

If an account may be compromised:

1. deactivate it immediately if authorized;
2. preserve logs and relevant audit information;
3. reset credentials;
4. terminate or invalidate hosting sessions where supported;
5. inspect role, integration, content, message, donation, and accounting
   changes;
6. rotate exposed secrets;
7. notify the responsible OIF owner;
8. follow the incident-response and legal notification procedure;
9. restore access only after verification.

# Public website and CMS runbook

For a hero photo or headline that is not tied to a specific programme,
speaker, leader, testimonial, gallery item, or event, use **Site CMS → Page
Photos** or **Site CMS → Page Copy** instead of searching for a content
record that does not exist — these two sections cover every remaining public
page image and writeup (MODULES_MANUAL.md section 5.8).

## Standard content change

1. Identify the owning content record.
2. confirm approved wording and asset rights;
3. edit the record in the relevant Content Library area;
4. set order and active/published flags;
5. save;
6. open the public page in a new tab;
7. check desktop and mobile layout;
8. check links, files, images, dates, and contact details;
9. correct or unpublish promptly if verification fails.

## Programs & Initiatives publishing

Open **Programs** in the dashboard to manage the public three-pillar programme
experience. The screen has four tabs: **Virtual Conferences**, **Mentorship
Program**, **Events**, and **Legacy Program Wings**. The first three contain the
six dedicated pages; the legacy tab retains programme records used by
registrations, resources, galleries, and mentorship enrollments. Tab URLs use
hash fragments, so filtered legacy results and direct links return to the
correct section.

The six dedicated pages are:

| Pillar | Page |
|---|---|
| Virtual Conferences | The Emerging Leader; The Emerging Lady |
| Mentorship Program | Forge Mentorship Program; Bloom 360 Mentorship Program |
| Events | Onesimus Community Outreach Initiative; In-Person Events & Gatherings |

Use **Edit page** for the page title, slug, eyebrow, description, hero,
frequency badge, phase copy, display order, or active state. Use **Manage
content** for the records inside the page:

- conference pages: Upcoming/Past editions and up to four speaker flyers per
  edition;
- mentorship pages: Sessions 01–08 and Phase 2 tracks or mentor pairing;
- OCOI: SDG focus cards and past outreach activities;
- in-person events: past gathering/archive entries.

### Conference edition procedure

1. Open the appropriate conference page and select **Manage content**.
2. add or edit a Conference edition;
3. choose Upcoming or Past;
4. enter the approved edition label, name/theme, narrative, and date;
5. upload the main flyer;
6. for an upcoming conference, add the supplied Google Form URL;
7. save, then add up to four speaker/personality flyers;
8. verify publication state and order;
9. preview the public page and test the Google Form in a new tab.

The page supports any number of past editions. Do not publish placeholder
attendance, speaker, or event claims. When the next conference concludes,
change or recreate it as a Past record with the final approved archive copy.

### Mentorship curriculum procedure

1. Open Forge Mentorship or Bloom 360 and select **Manage content**.
2. replace each seeded "Session title to be announced" value when approved;
3. keep session numbers unique and within 01–08;
4. use track labels for Forge Sessions 1–4 and 5–8 as required; Bloom sessions
   may remain sequential without labels;
5. store a supplied video URL only after checking it;
6. maintain Phase 2 track/pairing descriptions and the four-session count;
7. preview both phases after saving.

The public Watch buttons remain disabled and say **Coming soon**, even when a
video URL is stored. Do not promise video playback until that future feature is
implemented. Mentor scheduling is coordinated outside the website.

### OCOI and in-person archive procedure

- Add an SDG card only after OIF confirms the goal number, goal name, and
  contribution statement. Valid goal numbers are 1–17.
- Add past activities/events with an approved label, name, narrative, date,
  and flyer/photo. Include venue, attendance, or impact counts only when they
  are verified.
- Use publication/active controls instead of deletion when content may need to
  be retained or corrected.
- Preview card ordering and mobile presentation after every batch update.

### Important event distinction

Conference editions and past outreach/in-person archive entries are editorial
CMS records. They do not provide platform registration, capacity, attendance,
calendar files, or event-recipient messaging. Create an operational Event when
those functions are required. A supplied Google Form belongs on the conference
edition; an OIF-platform registration form belongs to an operational Event.

## Media standards

- Use descriptive, appropriate images.
- Obtain permission or licensing before publication.
- Resize/compress images before upload.
- Avoid placing confidential data in filenames or embedded imagery.
- Supply captions/attribution according to OIF policy.
- Do not use the CMS as the only archive of original media.

## Policy publishing

Policy text should be approved by the responsible governance/legal owner.
Clear the placeholder flag only when final text is in place. Record the approval
outside the CMS if the application has no separate approval workflow.

## Emergency public correction

For materially wrong or unsafe public information:

1. unpublish or deactivate the affected record;
2. preserve the previous wording where required for evidence;
3. notify the content owner;
4. publish approved corrected information;
5. verify caches/public rendering;
6. record the incident and resolution.

# Event administration runbook

This runbook applies to operational, registration-capable Events. Programme
initiative conference editions and past-activity archives are maintained in
the Programs CMS runbook above.

## Creating an event

Open **Events → New event** and complete the guided steps:

1. **Basics** — select the event type and related programme; enter the title,
   theme, summary, full description, and flyer.
2. **Logistics** — enter the start date/time, location, venue address and/or
   online URL, capacity, and contact email. Use zero capacity only for an
   intentionally unlimited event.
3. **Public details** — specify audience, outcomes, agenda, preparation,
   accessibility information, and the registration note.
4. **Review & Publish** — confirm virtual/in-person mode, registration-open
   state, and publication state; then create the event.

The wizard validates required fields before advancing, retains access to
completed steps, and reopens the step containing a server-side validation
error. After saving:

5. open the event's **Speakers & Facilitators** tab;
6. manually add each speaker, facilitator, keynote, panelist, moderator, host,
   mentor, or guest;
7. upload the approved portrait and provide role/title, organization, session
   topic, concise biography, useful image alt text, optional public profile
   URL, display order, and publication state;
8. preview the public event page and check the roster on desktop and mobile;
9. test registration and calendar download.

Use the roster's **Hidden** state when a person is not ready for public release.
Once an event has structured roster records, the old free-text speaker field is
not used as a public fallback; this prevents hidden profiles from leaking
through legacy copy. The legacy field remains in the data model for older
events that have not yet adopted structured profiles.

The system assumes a two-hour duration in generated calendar entries because
only the start time is stored.

## Managing registration

- Monitor capacity and active registrations.
- Close registration before capacity is exceeded or logistics require it.
- Treat accessibility and dietary information as sensitive.
- Update attendee status accurately.
- Use event-recipient messaging only for relevant communications.
- Avoid exporting attendee data unless necessary.

## Post-event closure

1. Mark attendance accurately.
2. close registration;
3. retain or unpublish the page according to event/publication policy;
4. review attendance and cancellation metrics;
5. resolve event-related enquiries;
6. update related gallery/impact content if approved;
7. retain necessary participant records according to policy.

# Application and mentorship runbook

## Reviewing applications

1. Review applicant identity, type, interest, and motivation.
2. follow the approved selection process outside the software where needed;
3. choose Approve or Reject;
4. understand that Mentor and Volunteer approval can change the account role;
5. verify the decision email result if delivery monitoring is available;
6. create mentorship enrollment separately for an approved mentee;
7. preserve fair and confidential handling.

Do not use application notes or decisions for purposes unrelated to the
application.

## Managing mentorship

1. Select the correct mentee.
2. assign an approved mentor or leave unassigned temporarily;
3. select the programme and cohort;
4. confirm total sessions;
5. update sessions completed;
6. progress through Phase 1, Phase 2, and Completed;
7. correct assignment or totals promptly;
8. ensure mentors see only their assigned mentees.

# Enquiry and partnership runbook

## Contact messages

- New means unprocessed.
- Read means acknowledged/reviewed.
- Resolved means the required response or action is complete.
- Reopen to New when further handling is required.

Assign internal responsibility outside the platform if more than one team is
involved. The `handled_by` field records the last administrator who changed the
status, not a full case-management history.

## Partnership enquiries

Use:

- **New** when received;
- **In review** during qualification;
- **Engaged** during active discussion;
- **Closed** when concluded or no longer active.

Only `manage_partners` changes these statuses. Keep substantive partnership
documents in the approved organizational repository, not in free-text messages
alone.

# Donation and Paystack runbook

## Before enabling online giving

1. Confirm the Paystack account and settlement details.
2. use keys for the correct live/test environment;
3. configure the callback and webhook URLs;
4. configure the webhook secret;
5. ensure demo mode is disabled in production;
6. perform a controlled test;
7. confirm receipt email and accounting journal behavior;
8. restrict integration settings to authorized administrators.

## Pending donation procedure

1. Open the donation record.
2. verify the reference is present;
3. run Paystack Verify;
4. compare provider reference, amount, currency, and metadata;
5. use bulk reconciliation for multiple pending references;
6. investigate provider errors;
7. mark success manually only with independent settlement evidence.

## Successful donation procedure

Confirm:

- status is Successful;
- donor details are appropriate;
- receipt was sent or the absence is explained;
- source journal exists;
- Paystack clearing/bank process accounts for settlement and fees;
- campaign/fund treatment is correct.

The campaign text on a donation does not automatically assign a restricted
accounting fund.

## Failed donation procedure

- Confirm the provider result.
- Do not treat failure as income.
- allow the donor to retry using a new transaction;
- avoid exposing provider internals to the donor;
- investigate repeated failures or configuration problems.

## Refunds and reversals

The current application does not provide a complete Paystack refund workflow.
Handle refunds through the authorized provider/finance process, retain
evidence, and record the necessary accounting entries or reversals. Do not
simply relabel a previously successful donation and assume the ledger has been
corrected.

# Messaging runbook

## Provider readiness

Before sending:

- verify Email is enabled and SMTP works;
- verify the selected SMS provider and sender ID;
- verify WhatsApp token and phone-number ID;
- confirm provider balance/quota;
- never place credentials in message content.

## Campaign preparation checklist

1. Define the business purpose and owner.
2. select Email, SMS, WhatsApp, or all channels;
3. select the smallest correct audience;
4. use Marketing opt-ins for promotional member messaging;
5. choose an event audience only for that event;
6. review custom recipients carefully;
7. enter subject and body;
8. validate `{name}`, `{first_name}`, `{email}`, `{phone}`, and `{org_name}`;
9. proofread dates, links, phone numbers, and calls to action;
10. test with a small/custom audience when risk is high;
11. obtain content approval;
12. send once and wait for completion.

## After sending

- Inspect Sent, Failed, and Skipped deliveries.
- calculate whether failures indicate data quality or provider problems;
- correct source contact data through the authorized workflow;
- do not resend the entire campaign casually;
- retain campaign evidence according to communications policy;
- respond to opt-out requests and update consent/subscription status.

## High-volume caution

Delivery is synchronous. A large multi-channel audience can hold the web request
open. Do not refresh or click Send repeatedly. For materially larger operations,
schedule a technical enhancement using a background job queue.

# Finance and accounting runbook

## Expense procedure

1. Create a Draft expense.
2. record title, category, payee, description, amount, currency, date, method,
   reference, and receipt;
3. verify evidence and budget authority;
4. approve under OIF policy;
5. mark Paid only after payment;
6. confirm the automated source journal;
7. link or record the corresponding cash movement as required;
8. use Void for cancelled records and review any existing journal.

Approved expenses credit Accounts Payable; Paid expenses credit Cash in the
automated source journal. Because source posting is idempotent, changing an
already posted Approved expense to Paid does not automatically replace its
original journal. Finance must review and enter the appropriate settlement
entry.

## Cash account procedure

- Create accounts with the correct type and currency.
- Record verified opening balance and date.
- mask and protect account information.
- link the appropriate asset ledger account;
- use Active, Inactive, and Closed deliberately;
- do not delete an account that has movements;
- update statement balance through reconciliation.

## Cash movement procedure

- Draft movements do not affect balances.
- Posted Money in increases the source account.
- Posted Money out reduces the source account.
- Posted Transfer reduces the source and increases the destination.
- Transfers require different accounts in the same currency.
- Use Void for invalidated movements and confirm reporting effects.
- Attach appropriate evidence.

## Journal procedure

1. Choose entry date, description, reference, period, and fund.
2. add posting-account lines;
3. put each amount on exactly one side;
4. confirm total debits equal credits above zero;
5. save Draft for review or Post;
6. verify the generated journal number;
7. use Reverse for correction after posting.

Never change accounting meaning by directly editing or deleting a posted entry.

## Fiscal period procedure

Before closing:

- all expected transactions are recorded;
- draft journals are posted or removed;
- reconciliations are complete;
- accounting exceptions are resolved;
- reports have been reviewed and retained;
- governance approval has been obtained.

Closing blocks posting into the period. Reopening should be exceptional,
authorized, and followed by renewed close review.

## Budget procedure

1. Select fiscal period and optional fund.
2. add each income/expense account once;
3. enter non-negative amounts;
4. review totals and assumptions;
5. approve;
6. lock when final;
7. review variance regularly;
8. return to Draft only through an authorized revision process.

## Bank reconciliation procedure

1. Select the cash/bank account and statement date.
2. enter statement and book balance;
3. enter outstanding deposits and payments;
4. enter documented adjustments;
5. review the calculated adjusted statement balance;
6. investigate until difference is exactly zero;
7. obtain independent review where possible;
8. approve reconciliation;
9. retain the statement and reconciliation evidence.

## Accounting health review

Investigate:

- unbalanced draft journals;
- absence of an open fiscal period;
- draft/unapproved reconciliations;
- successful donations without source journals;
- approved/paid expenses without source journals;
- unexpected clearing balances;
- cash-to-ledger differences;
- trial-balance inequality.

# Reports, audit, and exports

## Report use

Select the appropriate date range and report area. Check whether totals are:

- personal or organization-wide;
- status-filtered;
- cash-based or journal-based;
- limited by fund;
- based on creation date, transaction date, or event date.

Report access varies by capability. A successful CSV export is audit logged.

## Audit review

Review actor, time, action, target, and detail. Focus on:

- role changes;
- member activation;
- event publication and registration changes;
- donation status and reconciliation;
- accounting posting, reversal, period, budget, and reconciliation actions;
- campaign sends;
- integration changes;
- CMS changes and deletes;
- exports.

Audit logs are not a substitute for hosting, provider, database, and security
logs.

## Export handling

- Export only what is necessary.
- Store files in an approved encrypted location.
- Do not email sensitive exports casually.
- restrict access to the same or narrower audience as the platform view;
- delete working copies when no longer needed;
- retain official reports according to OIF policy.

# Security administration

## Application security controls

When debug is disabled, the settings enable:

- HTTPS redirect by default;
- secure session and CSRF cookies;
- HSTS;
- content-type sniffing protection;
- proxy HTTPS awareness;
- frame denial;
- trusted-origin configuration.

These controls depend on correct deployment and proxy settings.

## Credential handling

- Keep `.env` outside source control.
- Use separate test and production credentials.
- restrict CMS integration configuration;
- rotate exposed or departed-user credentials;
- avoid credential reuse;
- never include secrets in logs, audit detail, support tickets, or manuals.

## Data minimization

Collect only needed participant information. Accessibility, dietary, contact,
application, mentorship, donation, and financial data require particular care.
Do not retain exports merely because storage is available.

## Security incident checklist

1. Identify and contain.
2. preserve evidence;
3. disable affected access;
4. rotate credentials;
5. assess records and integrations affected;
6. restore trusted configuration/data;
7. notify internal owners and external parties as required;
8. document the incident;
9. implement corrective action;
10. review access and monitoring.

# Backup, recovery, and continuity

## Backup scope

Back up:

- the production database;
- uploaded media;
- environment and deployment configuration through a secure process;
- approved financial exports and reconciliation evidence;
- any external provider configuration required for recovery.

Static source files can be rebuilt from the repository; user media and the
database cannot.

## Backup controls

- Encrypt backups.
- restrict backup access;
- keep more than one recovery point;
- store at least one copy separately from the live host;
- monitor completion;
- test restoration;
- document retention and deletion.

## Recovery order

1. Establish a clean, supported runtime.
2. restore application source at the intended version;
3. restore environment configuration and secrets;
4. restore the database;
5. restore media;
6. run migrations appropriate to the source version;
7. collect static files;
8. run checks;
9. test authentication, public pages, uploads, email, Paystack, and dashboard;
10. reconcile transactions that occurred around the outage.

# Release and deployment runbook

## Before deployment

```text
Back up database and media
Review the change and migration plan
Run Django checks
Check for missing migrations
Run the full test suite
Confirm production configuration
Plan rollback/recovery
```

## Standard commands

```sh
python manage.py check --deploy
python manage.py makemigrations --check --dry-run
python manage.py test
python manage.py migrate
python manage.py collectstatic --noinput
```

## After deployment

Smoke-test:

- homepage and core public pages;
- static images/styles and uploaded media;
- login, logout, and password reset;
- dashboard role access;
- one non-destructive CMS view;
- event detail and registration;
- event creation wizard and one non-destructive Speakers & Facilitators view;
- uploaded event-contributor portrait through the `/media/` mapping;
- email delivery;
- Paystack configuration/status without creating an unintended live charge;
- reports and accounting;
- error logs.

## Rollback principle

Code rollback does not automatically reverse a database migration. Use a
planned, tested recovery procedure. Never use destructive version-control or
database commands against production without an explicit target, backup, and
authorization.

# Administrator troubleshooting matrix

| Symptom | First checks | Escalate when |
|---|---|---|
| User cannot sign in | Active status, username, password reset, allowed host/cookies | Multiple users affected or security incident suspected |
| New member cannot sign in | This is expected until approved — check Members → Pending approval, then activate | Member appears already active but still cannot sign in |
| Function missing | Role, capability, personal vs organization scope | Mapping does not match approved policy |
| Public record missing | Published/active flag, date, slug, related record | Database or template error |
| Upload fails | File size/type, media path, storage permission | Storage unavailable or data at risk |
| Email missing | Address, backend, SMTP, spam/provider log | Repeated or organization-wide failure |
| Event registration rejected | Published/open state, capacity, duplicate record, form fields | Valid users consistently fail |
| Donation Pending | Paystack enabled, reference, verify, webhook | Provider mismatch or settlement dispute |
| Donation incorrectly Successful | Evidence, demo mode, provider record, source journal | Refund/reversal or security issue |
| Campaign failures | Channel enabled, credential, quota, destination | Broad failure, duplication, or provider incident |
| Cash balance wrong | Opening balance, Posted movements, transfers, date filters | Evidence and calculated balance cannot reconcile |
| Journal will not post | Balance, posting account, open period, source uniqueness | Correction requires policy/accounting judgment |
| Reconciliation will not approve | Difference calculation and evidence | Difference cannot be resolved |
| Dashboard error | Logs, database, recent release, affected role/path | 500 error, data loss risk, or broad outage |

# Administrator checklists

## New member approval checklist

- [ ] Account appears legitimate (name, email, no obvious spam pattern)
- [ ] No duplicate account already exists for this person
- [ ] Reviewed under Members → Pending approval
- [ ] Active account box checked and saved
- [ ] Membership-accepted email delivery not showing as failed

## New event checklist

- [ ] Approved title and programme
- [ ] Accurate date/time and time zone
- [ ] Venue and/or online link
- [ ] Capacity
- [ ] Accessibility and contact information
- [ ] Flyer and content rights
- [ ] Speaker/facilitator names, roles, organizations, and session topics approved
- [ ] Portrait permission confirmed and useful alt text supplied
- [ ] Profile publication state and display order checked
- [ ] Public page verified
- [ ] Registration tested
- [ ] Calendar file tested
- [ ] Communications owner identified

## Programs & Initiatives publishing checklist

- [ ] Correct pillar and dedicated page selected
- [ ] Approved title/theme and narrative
- [ ] Main flyer/photo rights confirmed
- [ ] Date, venue, attendance, and impact claims verified
- [ ] Google Form URL tested when applicable
- [ ] No more than four conference speaker flyers
- [ ] Mentorship session number is unique and within 01–08
- [ ] Watch feature described as coming soon
- [ ] SDG number and contribution statement approved
- [ ] Order and publication/active state checked
- [ ] Public desktop and mobile page previewed
- [ ] Operational Event created separately if platform registration is needed

## Campaign checklist

- [ ] Authorized purpose
- [ ] Correct audience and consent basis
- [ ] Correct channel
- [ ] Proofread subject/body
- [ ] Placeholders tested
- [ ] Links and dates tested
- [ ] Provider ready
- [ ] Approval obtained
- [ ] Send initiated once
- [ ] Delivery report reviewed

## Donation reconciliation checklist

- [ ] Provider reference matches
- [ ] Amount matches
- [ ] Currency matches
- [ ] Metadata/record matches
- [ ] Settlement evidence exists
- [ ] Receipt status reviewed
- [ ] Source journal exists
- [ ] Clearing/bank treatment reviewed
- [ ] Exceptions documented

## Fiscal-period close checklist

- [ ] All transactions recorded
- [ ] Draft journals resolved
- [ ] Source-journal exceptions resolved
- [ ] Bank/cash reconciliations complete
- [ ] Trial balance balances
- [ ] Budget variance reviewed
- [ ] Statements approved
- [ ] Backup completed
- [ ] Close authorized
- [ ] Next period created

## Staff offboarding checklist

- [ ] Account deactivated
- [ ] Staff/superuser access removed
- [ ] Responsibilities reassigned
- [ ] Provider secrets rotated where necessary
- [ ] Local/exported data recovered or deleted
- [ ] Historical attribution preserved
- [ ] Offboarding recorded

## Production readiness checklist

- [ ] Debug disabled
- [ ] Strong secret key
- [ ] Hosts and CSRF origins correct
- [ ] HTTPS/security headers verified
- [ ] Production database configured
- [ ] SMTP tested
- [ ] Paystack configured
- [ ] Demo mode disabled
- [ ] Messaging providers tested or disabled
- [ ] Persistent media and backups configured
- [ ] Policies and contact details finalized
- [ ] Demo content removed
- [ ] Checks, migrations, tests, and static collection complete
- [ ] Administrator and role access reviewed
- [ ] Recovery procedure documented and tested

# Escalation and change control

Escalate to the responsible OIF owner when:

- authorization is missing or disputed;
- a role would expose materially broader data;
- a payment, refund, settlement, or accounting treatment is uncertain;
- legal/privacy wording or consent is uncertain;
- an incident may require notification;
- data could be lost or overwritten;
- a migration or deployment cannot be safely reversed;
- a provider credential may be compromised;
- an operation requires direct database modification.

Direct database edits should be exceptional, backed up, reviewed, recorded, and
performed by a qualified maintainer. Changes to capabilities, accounting
automation, payment verification, or communications should include tests and an
update to this handbook.

# Module reference

The following section is incorporated from the maintained OIF Platform Module
and Operations Manual.
