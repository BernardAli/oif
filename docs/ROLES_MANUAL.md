# OIF Platform Roles and Access Manual

## 1. Purpose

This manual describes every OIF platform role, its implemented access, normal
responsibilities, boundaries, and recommended assignment criteria.

It is the companion to [`MODULES_MANUAL.md`](MODULES_MANUAL.md), which explains
the platform's functional modules and workflows.

## 2. How role-based access works

Each account has one role. The role grants named capabilities. Protected views
check capabilities, not the role label. A Django superuser bypasses the normal
role mapping and receives every capability.

All authenticated roles receive two baseline capabilities:

- `register_events`;
- `give_donations`.

They can also use the personal dashboard, profile, personal events,
applications, mentorship information relevant to them, personal donation
history, and personal analytics where implemented.

Role assignment should follow least privilege: give a user the narrowest role
that supports their current work.

## 3. Capability glossary

| Capability | What it permits |
|---|---|
| `view_org_analytics` | Organization summary and broad executive/event/people/content/engagement reporting |
| `manage_users` | Change platform roles and Django staff status; full user administration authority |
| `manage_members` | Search, inspect, activate, and update member operational profiles |
| `manage_events` | Create/edit events and administer registrations/attendance |
| `manage_donations` | Verify/reconcile donations and manage finance/accounting records |
| `view_donations` | Read organization-wide donations, finance, ledger, and statements |
| `manage_applications` | Review and decide applications |
| `manage_mentorship` | Create and update mentorship enrollments |
| `view_mentees` | See mentorships assigned to the current mentor |
| `view_assignments` | See personal assignments/mentorship context |
| `manage_content` | Manage programmes, resources, speakers, leadership, branding, stats, testimonials, gallery, and policies |
| `manage_media` | Media-management authority in the role model; current CMS routes principally require `manage_content` |
| `manage_speakers` | Speaker-management authority in the role model; current speaker routes principally require `manage_content` |
| `manage_testimonials` | Testimonial-management authority in the role model; current CMS routes principally require `manage_content` |
| `manage_contact` | Read and process contact enquiries and view the Enquiries workspace |
| `manage_partners` | Change partnership enquiry status |
| `view_partners` | Partnership/reporting visibility without status-changing authority |
| `approve_content` | Content-approval authority represented in the role model; current CMS does not implement a separate approval state |
| `configure_integrations` | Edit SMS, WhatsApp, email enablement, and Paystack CMS configuration |
| `send_messages` | Create templates/campaigns and initiate delivery |
| `view_message_reports` | View campaigns and per-recipient delivery reporting |
| `view_audit` | View the administrative audit trail |

The three media/speaker/testimonial capabilities and `approve_content` express
policy intent, but current content URLs are gated by `manage_content`. They
should not be interpreted as standalone access to those screens until route
guards are separated.

## 4. Role capability matrix

`✓` means the role receives the capability. Baseline event registration and
giving are omitted because every role receives them.

| Role | Analytics | Members | Events | Donations | Applications | Mentorship | Content | Enquiries/Partners | Messaging | Integrations | Audit |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Super Administrator | Full | Users + members | Manage | Manage + view | Manage | Manage + view | Full | Full | Send + reports | Configure | View |
| Global Lead | View | — | — | View | — | — | Approve policy only | View partners | Reports | — | View |
| Executive Director | View | Manage | Manage | View | Manage | Manage + view | Manage + approve | Contact + partner view | Send + reports | — | View |
| Director / Staff | View | Manage | Manage | View | Manage | Manage + view | Manage + approve | Contact + partner view | Send + reports | — | — |
| Director of Programmes | View | — | Manage | — | — | Manage + view | Manage/media | — | Send + reports | — | — |
| Director of Operations & Volunteer Engagement | View | Manage | — | — | Manage | Assignment + mentee view | — | Contact | — | — | — |
| Director of Communications, Media & Digital | — | — | — | — | — | — | Manage/media/speakers/testimonials | — | Send + reports | — | — |
| Director of Partnerships & Resource Mobilisation | View | — | — | View | — | — | — | Contact + manage/view partners | Send + reports | — | — |
| Finance / Donations Manager | — | — | — | Manage + view | — | — | — | — | — | — | — |
| Content Editor | — | — | — | — | — | — | Manage/media/speakers/testimonials | — | Send + reports | — | — |
| Event Manager | — | — | Manage | — | — | — | — | — | Send + reports | — | — |
| Mentor | — | — | — | — | — | Assigned mentees + assignments | — | — | — | — | — |
| Volunteer | — | — | — | — | — | Personal assignments | — | — | — | — | — |
| Applicant | — | — | — | — | Personal only | Personal only | — | — | — | — | — |
| Donor | — | — | — | Personal only | Personal only | Personal only | — | — | — | — | — |
| Member | — | — | — | Personal only | Personal only | Personal only | — | — | — | — | — |

## 5. Shared access for every authenticated role

Every authenticated user can normally:

- open Overview;
- edit their profile and avatar;
- see upcoming published events;
- register for events and manage their own registration;
- cancel their own registration;
- submit Mentor, Volunteer, Mentee, or Speaker applications;
- see their own application statuses;
- see mentorship information in which they are the mentee;
- make donations;
- see donations linked to their account;
- see personal giving analytics;
- log out and use password reset.

The Events, Donations, Applications, and Mentorship navigation items are
therefore visible even to public-facing roles. Their contents adapt to the
current user.

## 6. Super Administrator

### Intended user

The trusted technical/business owner responsible for the whole platform.
Assignment should be rare and reviewed regularly.

### Access

The role receives every capability, including:

- role and Django staff administration;
- member, event, donation, application, mentorship, content, enquiry, partner,
  messaging, integration, and accounting management;
- all organization reporting;
- audit trail;
- Django Admin.

### Normal responsibilities

- create and deactivate staff access;
- assign and review roles;
- maintain production integrations and security configuration;
- resolve cross-module incidents;
- review audit and accounting exceptions;
- supervise backups, releases, and access reviews;
- intervene where a narrower role cannot complete an authorized task.

### Boundaries and cautions

- Do not use this role for routine content or event work.
- Do not share the account.
- Use a unique strong password and organizationally approved MFA where the
  hosting/authentication environment supports it.
- Integration credentials and role changes are especially sensitive.
- A Django superuser has the same effective capability breadth even if its role
  field shows another label.

## 7. Global Lead

### Intended user

Senior governance leadership requiring organization-wide oversight without
routine operational editing.

### Access

- organization analytics and executive reports;
- organization-wide donation and finance read access;
- partnership reporting visibility;
- messaging performance reports;
- audit trail;
- content-approval capability in the policy model.

### Normal responsibilities

- monitor impact, membership, events, giving, and application trends;
- review financial statements and management reports;
- oversee partnerships and communications performance;
- review the audit trail and escalate anomalies;
- provide governance approval outside the system where required.

### Boundaries

This role cannot currently edit events, donations, members, campaigns, content,
or integrations. `approve_content` does not currently expose a separate
approve/reject action in the CMS.

## 8. Executive Director

### Intended user

The senior operational leader coordinating programmes, people, content,
engagement, and reporting.

### Access

- organization analytics and reports;
- member management, excluding role/staff changes;
- event and registration management;
- application decisions;
- mentorship management and assigned-mentee visibility;
- organization donation/finance read access;
- content management and policy approval capability;
- contact enquiry processing and partnership visibility;
- campaign sending and messaging reports;
- audit trail.

### Normal responsibilities

- supervise cross-functional operational queues;
- manage events and programme delivery;
- review applications and mentorship activity;
- maintain member operational records;
- review finance without altering finance records;
- approve or oversee public content;
- coordinate organization communications;
- monitor audit history.

### Boundaries

The Executive Director cannot change user roles, manage accounting/donation
status, change partner status, or configure provider credentials.

## 9. Director / Staff

### Intended user

A broad legacy/general operations role for trusted staff whose work spans
several modules.

### Access

Very similar to Executive Director:

- analytics and reports;
- members, events, applications, and mentorship;
- donation/finance read access;
- content and contact management;
- partner visibility;
- campaign sending and reporting.

### Differences from Executive Director

- no audit-trail access;
- otherwise current capability coverage is broadly operational.

### Assignment guidance

Prefer a functional director role when duties are narrow. Use Director / Staff
only when broad cross-functional access is genuinely necessary.

## 10. Director of Programmes

### Intended user

The person responsible for programme design, programme events, mentorship, and
programme communications.

### Access

- organization analytics;
- event management;
- mentorship management and assigned-mentee visibility;
- content and media management;
- campaign sending and reporting.

### Normal responsibilities

- maintain programme information and resources;
- plan and publish programme events;
- monitor registration and attendance;
- create and update mentorship cohorts;
- track mentee progress;
- communicate with programme and event audiences;
- review programme-related analytics.

### Boundaries

No member administration, application review, donation/finance access,
enquiry/partner processing, integration configuration, or audit trail.

## 11. Director of Operations & Volunteer Engagement

### Intended user

The operations leader responsible for members, volunteer intake, assignments,
and contact follow-up.

### Access

- organization analytics;
- member management, excluding role/staff changes;
- application review;
- personal assignment and mentee visibility;
- contact enquiry processing.

### Normal responsibilities

- maintain member operational profiles and active status;
- review volunteer and other applications;
- coordinate volunteer/member engagement;
- process general contact enquiries;
- monitor people and engagement reports;
- view assignments relevant to their account.

### Boundaries

No event management, organization-wide donations, mentorship administration,
content management, partnership status changes, messaging, integrations, or
audit trail. Although application approval may automatically promote a Member
to Mentor or Volunteer, this role cannot otherwise select arbitrary roles.

## 12. Director of Communications, Media & Digital

### Intended user

The communications owner for the public site, media library, and outbound
campaigns.

### Access

- full current content CMS access;
- media, speaker, and testimonial policy capabilities;
- campaign templates and sending;
- campaign and delivery reports.

### Normal responsibilities

- maintain brand, public copy, programmes, resources, speakers, leadership,
  metrics, testimonials, gallery, and policies;
- optimize and publish media;
- create reusable message templates;
- segment appropriate audiences;
- send and monitor email/SMS/WhatsApp campaigns;
- respect consent and correct failed recipient data through proper processes.

### Boundaries

No organization analytics, events, members, finance, applications, mentorship,
enquiries, integrations, or audit trail. Provider credential changes must be
escalated to a Super Administrator.

## 13. Director of Partnerships & Resource Mobilisation

### Intended user

The leader responsible for partners, sponsors, institutional donors, resource
mobilisation, and related communications.

### Access

- organization analytics;
- donation/finance read access;
- contact enquiry processing;
- partnership read and status management;
- campaign sending and reporting.

### Normal responsibilities

- progress enquiries from New to In review, Engaged, and Closed;
- maintain timely follow-up ownership;
- monitor giving and resource-mobilisation reporting;
- communicate with appropriate member, newsletter, or custom audiences;
- coordinate with Finance on settlement and with Communications on public copy.

### Boundaries

Cannot verify donations, alter accounting records, manage members/events/
applications/content, configure integrations, or view the audit trail.

## 14. Finance / Donations Manager

### Intended user

The finance operator responsible for donations, expenses, cash control, ledger,
budgets, reconciliations, and financial exports.

### Access

- organization-wide donation records;
- Paystack verification and reconciliation;
- expense, cash account, and cash movement management;
- ledger accounts, funds, fiscal periods, journals, budgets, and bank
  reconciliations;
- finance reports, statements, accounting health, and CSV export.

### Normal responsibilities

- reconcile Pending donations against Paystack;
- verify settlement before manual success;
- maintain receipt and reference evidence;
- record and approve/pay expenses according to OIF policy;
- maintain cash accounts and posted movements;
- ensure journals balance and periods are correct;
- use reversals for posted-entry corrections;
- prepare budgets and reconciliations;
- review unposted-source and reconciliation exceptions;
- close periods under approved procedure.

### Boundaries and segregation

- No member, event, application, content, messaging, integration, or audit
  administration.
- The application currently allows one finance manager to prepare and approve
  several finance records. OIF policy should require independent evidence and,
  where staffing allows, a separate reviewer even when the software does not
  enforce two distinct people.
- Never use demo mode or manual success in production to conceal settlement
  failure.
- Successful donations reverted to another status and posted expenses reverted
  to Draft/Void require accounting review; the source journal is not
  automatically reversed.

## 15. Content Editor

### Intended user

A staff member performing routine website and campaign-content maintenance.

### Access

- the same current CMS routes as the Communications Director;
- media, speaker, and testimonial policy capabilities;
- message template/campaign creation and sending;
- messaging reports.

### Normal responsibilities

- update approved public content and assets;
- maintain publication flags and display order;
- check public rendering and links;
- prepare and send authorized communications;
- review delivery results.

### Boundaries

No broader analytics or operations access. This role can send campaigns, so it
must be limited to trusted editors with audience and consent training.
`approve_content` is not granted; use the organization's review procedure
before publication.

## 16. Event Manager

### Intended user

An operator responsible for event setup, registration, attendance, and
event-specific communications.

### Access

- create/edit/publish events;
- open and close registration;
- manage attendee registration status;
- view event reports;
- create and send campaigns;
- view campaign delivery reports.

### Normal responsibilities

- confirm event logistics and capacity;
- publish accurate detail and accessibility information;
- monitor registrations and fill rate;
- keep attendee contact data confidential;
- record attendance after the event;
- message event registrants using the Event audience.

Check-in time and administrative-note fields exist on registration records, but
the current event dashboard action changes registration status only.

### Boundaries

No general member management, organization analytics, finance, applications,
mentorship, CMS library, enquiries, integrations, or audit trail. Editing an
event is not the same as managing programme CMS content.

## 17. Mentor

### Intended user

An approved mentor assigned to one or more mentorship enrollments.

### Access

- personal dashboard functions;
- assigned mentee list and phase summary;
- personal assignment/mentorship context.

### Normal responsibilities

- use assigned mentee information only for programme delivery;
- monitor the mentorship view;
- report progress or assignment corrections to a mentorship manager;
- maintain appropriate confidentiality and safeguarding practices.

### Boundaries

Mentors cannot create/edit enrollment records themselves, browse all members,
or access staff operations. Mentorship managers update session counts and
phases in the current implementation.

## 18. Volunteer

### Intended user

An approved volunteer participating in OIF activities.

### Access

- personal dashboard functions;
- personal assignment/mentorship context.

### Normal responsibilities

- keep profile and contact details current;
- register for relevant events;
- monitor personal applications and assignments;
- follow operational instructions supplied by staff.

### Boundaries

No staff management, reporting, or organization-wide data access.

## 19. Applicant

### Intended user

A prospective participant whose account is awaiting membership or another
decision. Public signup creates a Member role directly (not Applicant), so
Applicant is normally assigned through an internal intake process or migrated
data. Note that a Member created by public signup is separately gated by
account activation (section 21) even though its role is already Member — role
and active status are independent controls.

### Access

- personal profile;
- personal event, application, mentorship, and donation functions;
- baseline registration and giving.

### Transition

When an administrator changes Applicant to Member, the system sends a
membership-accepted email. Application approval may also promote an Applicant
to Mentor or Volunteer when the application type matches.

### Boundaries

No organization-wide or staff access.

## 20. Donor

### Intended user

A public account primarily associated with giving.

### Access

- personal profile;
- giving flow and personal donation history;
- personal events, applications, and mentorship information;
- personal giving analytics.

### Boundaries

The Donor role does not expose other donors or organization-wide fundraising.
Donation records may also be linked by email in member administration, but
organization-wide access still requires a staff capability.

## 21. Member

### Intended user

The standard account created by public signup and the default community role.

### Account activation

A Member created through public signup is created **inactive** and cannot
sign in until a user with `manage_members` approves the account (Members →
open the record → Admin tab → Active account). This is a gate on
authentication, not on role — the account already holds the Member role while
pending. See MODULES_MANUAL.md section 4.3 for the full workflow. A Member
created directly by an administrator through the Members form is active
immediately unless the administrator leaves the box unchecked.

### Access

- all shared personal functions;
- event registration and cancellation;
- applications;
- personal mentorship;
- giving and donation history;
- profile and public-profile preference.

### Progression

A Member may apply as Mentor or Volunteer. Approval automatically changes the
role when appropriate. A Mentee or Speaker application is approved without an
automatic role change.

### Boundaries

No organization-wide data or staff operations.

## 22. Choosing the correct role

Use the following decision guide:

| Need | Recommended role |
|---|---|
| Full platform, roles, credentials, and audit | Super Administrator |
| Governance oversight without editing | Global Lead |
| Broad senior operations and audit | Executive Director |
| Broad operations without audit | Director / Staff |
| Programmes, programme events, mentorship, content | Director of Programmes |
| Members, applications, volunteers, contact queue | Director of Operations & Volunteer Engagement |
| Public content, media, and campaigns | Director of Communications, Media & Digital |
| Partnerships, fundraising visibility, outreach campaigns | Director of Partnerships & Resource Mobilisation |
| Donations, finance, accounting, reconciliation | Finance / Donations Manager |
| Routine CMS and campaign work | Content Editor |
| Events, attendees, and event campaigns | Event Manager |
| Assigned mentees | Mentor |
| Personal volunteer assignments | Volunteer |
| Standard community access | Member |
| Giving-focused public account | Donor |
| Pre-membership/prospective account | Applicant |

When one person performs multiple functions, choose the narrowest existing role
that covers the authorized duties. Do not automatically select Super
Administrator. If no role fits, review the capability mapping with a developer
and governance owner rather than informally sharing accounts.

## 23. Account onboarding procedure

For a staff account:

1. confirm authorization from the appropriate OIF owner;
2. create or identify the individual's account;
3. select the least-privilege role;
4. leave Django `is_staff` off unless `/admin/` is required;
5. verify the email address and active status;
6. have the user set their own password through the secure flow;
7. ask the user to sign in and confirm the expected navigation;
8. provide the relevant sections of this manual;
9. record the approval under OIF's access-control procedure.

Never send a password by email or messaging campaign.

### Public self-signup members

A member who registers through the public sign-up form does not go through
this procedure directly — their account is created automatically with the
Member role, inactive. Approving them is simpler:

1. confirm the account and requester appear legitimate;
2. open the record from Members (filter by "Pending approval");
3. check Active account on the Admin tab and save;
4. no role selection is needed — public signups are always Member.

Use the staff-account procedure above only when creating an account directly
(any other role, or a Member account outside the public signup flow).

## 24. Role-change procedure

Only `manage_users` can expose role and Django staff fields in the member form.
In the current mapping, that means the Super Administrator.

Before changing a role:

1. confirm the request and business owner;
2. compare old and new capabilities;
3. check whether the user has active responsibilities or sensitive exports;
4. apply the role change;
5. verify navigation and a representative protected action;
6. review the audit entry;
7. notify the user of changed responsibilities without sending credentials.

Application approval is a controlled exception: approving a Mentor or
Volunteer application can promote a Member or Applicant automatically.

## 25. Offboarding and temporary suspension

When access should stop:

1. set `is_active` to false instead of deleting the account;
2. revoke Django staff/superuser access where applicable;
3. rotate any shared external provider credentials the person knew;
4. reassign mentorships, enquiries, events, or operational ownership;
5. preserve the account so audits, journals, reviews, and other historical
   records retain attribution;
6. follow OIF policy for retained exports and local copies.

For a temporary leave, deactivate and later reactivate. Reactivation may send a
membership-accepted email.

## 26. Periodic access review

At least quarterly, or according to OIF policy:

- list active accounts by role;
- confirm each staff user's current duties and manager;
- review all Super Administrators and Django staff users;
- remove obsolete broad roles;
- check dormant or departed users;
- review integration access;
- inspect audit entries for role changes and sensitive actions;
- confirm that finance, communications, and member-data access remains
  justified.

## 27. Practical boundaries and known implementation details

- `manage_members` is not `manage_users`; only the latter changes role/staff
  fields.
- `view_donations` exposes finance and ledger screens, not merely donation
  totals.
- `manage_donations` includes broad accounting mutation rights.
- `send_messages` can contact large audiences and must be treated as a
  high-impact permission.
- `view_message_reports` exposes recipient-level delivery information.
- `manage_contact` is required to open Enquiries; `view_partners` alone mainly
  contributes reporting visibility.
- CMS routes currently use `manage_content` even though narrower media,
  speakers, and testimonials capabilities exist.
- `approve_content` does not currently enforce a content approval workflow.
- `view_assignments` currently has limited UI expression; it contributes
  personal assignment/mentorship context rather than a general assignment
  management module.
- Django `is_staff` controls admin-site eligibility separately from platform
  capabilities.
- Django superuser status overrides the normal capability mapping.

These details should be rechecked whenever the role mapping, route decorators,
or dashboard navigation changes.
