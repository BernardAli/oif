"""Seed the OIF site with realistic demo data for every role.

Creates programs, speakers, team, stats, events, users across all 5 roles,
backdated donations / registrations (for 12-month analytics variety),
applications and mentorship enrollments. Idempotent: clears prior demo
records first.

    python manage.py seed_demo
"""
import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from pages.models import (Program, ProgramResource, Speaker, TeamMember,
                          SiteStat, Event, Testimonial, GalleryImage, Policy)
from donations.models import Donation
from engagement.models import (EventRegistration, Application,
                               MentorshipEnrollment, ContactMessage,
                               PartnerEnquiry, NewsletterSubscriber)
from dashboard.models import AuditLog, JournalEntry, log_action

User = get_user_model()
random.seed(2018)

PASSWORD = "oifdemo123"


def backdate(model, pk, dt):
    """Override an auto_now_add field after creation."""
    model.objects.filter(pk=pk).update(created_at=dt)


class Command(BaseCommand):
    help = "Populate the database with OIF demo data."

    @transaction.atomic
    def handle(self, *args, **options):
        now = timezone.now()
        self.stdout.write("Clearing previous demo data…")
        JournalEntry.objects.all().delete()
        Donation.objects.all().delete()
        EventRegistration.objects.all().delete()
        Application.objects.all().delete()
        MentorshipEnrollment.objects.all().delete()
        Event.objects.all().delete()
        ProgramResource.objects.all().delete()
        Program.objects.all().delete()
        Speaker.objects.all().delete()
        TeamMember.objects.all().delete()
        SiteStat.objects.all().delete()
        Testimonial.objects.all().delete()
        GalleryImage.objects.all().delete()
        Policy.objects.all().delete()
        ContactMessage.objects.all().delete()
        PartnerEnquiry.objects.all().delete()
        NewsletterSubscriber.objects.all().delete()
        AuditLog.objects.all().delete()
        # Keep superusers; remove prior demo accounts only.
        User.objects.filter(is_superuser=False).delete()

        # ---------------------------------------------------------------- Programs
        self.stdout.write("Creating programs (wings)…")
        forge = Program.objects.create(
            wing=Program.Wing.FORGE, accent="coffee", order=1,
            tagline="Raising emerging leaders",
            headline="Forging men of conviction and competence",
            description=("The Forge is OIF's leadership crucible for emerging "
                         "young men — building character, capacity and Christ-"
                         "centred conviction through mentorship and live cohorts."))
        hadassah = Program.objects.create(
            wing=Program.Wing.HADASSAH, accent="tan", order=2,
            tagline="Empowering emerging ladies",
            headline="Raising women of purpose and poise",
            description=("The Hadassah Project equips emerging young ladies to "
                         "lead with grace, wisdom and excellence across every "
                         "sphere of influence."))
        human = Program.objects.create(
            wing=Program.Wing.HUMANITARIAN, accent="olive", order=3,
            tagline="Compassion in action",
            headline="Serving communities, restoring dignity",
            description=("The Humanitarian Wing mobilises outreaches, relief and "
                         "community development projects across Ghana and beyond."))
        virtual = Program.objects.create(
            wing=Program.Wing.VIRTUAL, accent="coffee", order=4,
            tagline="Biannual virtual conferences",
            headline="Global voices, one screen at a time",
            description=("OIF's Virtual Conferences convene accomplished leaders "
                         "from Ghana and the diaspora for teaching, dialogue and "
                         "impartation across our flagship wings."))
        mentorship = Program.objects.create(
            wing=Program.Wing.MENTORSHIP, accent="olive", order=5,
            tagline="A structured two-phase pipeline",
            headline="Eight recorded sessions, four live with a mentor",
            description=("The Mentorship Programme pairs emerging leaders with "
                         "experienced mentors through recorded foundations and "
                         "live cohort sessions."))
        programs = [forge, hadassah, human, virtual, mentorship]

        # Downloadable program resources (Section 5.1.3)
        ProgramResource.objects.create(
            program=forge, title="The Forge — Cohort Handbook",
            description="Overview of the leadership crucible and expectations.",
            external_url="https://onesimusimpact.org/resources/forge-handbook",
            order=1)
        ProgramResource.objects.create(
            program=hadassah, title="Hadassah Project — Programme Brief",
            description="What to expect from the women's development track.",
            external_url="https://onesimusimpact.org/resources/hadassah-brief",
            order=1)
        ProgramResource.objects.create(
            program=mentorship, title="Mentorship Pipeline — Session Guide",
            description="The 8 recorded + 4 live session structure.",
            external_url="https://onesimusimpact.org/resources/mentorship-guide",
            order=1)

        # ---------------------------------------------------------------- Speakers
        self.stdout.write("Creating speakers…")
        speakers = [
            ("Dr. Sunday Adelaja", "Founder, Embassy of God · Kyiv"),
            ("Bernard Avle", "Broadcast Journalist · Citi FM/Channel One"),
            ("Dr. Lawrence Tetteh", "Founder, Worldwide Miracle Outreach"),
            ("Hon. John Dumelo", "MP & Entrepreneur"),
        ]
        for i, (n, r) in enumerate(speakers):
            Speaker.objects.create(name=n, role=r, featured=True, order=i)

        # ---------------------------------------------------------------- Team
        self.stdout.write("Creating leadership team…")
        team = [
            ("Onesimus Mensah", TeamMember.Position.GLOBAL_LEAD,
             "Global Lead & Founder", "Visionary, Onesimus Impact Foundation"),
            ("Grace Owusu", TeamMember.Position.EXEC_DIRECTOR,
             "Executive Director", "Operations & Strategy"),
            ("Daniel Asare", TeamMember.Position.DIRECTOR,
             "Director, The Forge", "Leadership & Mentorship"),
            ("Esther Boateng", TeamMember.Position.DIRECTOR,
             "Director, The Hadassah Project", "Women's Development"),
            ("Kwame Adjei", TeamMember.Position.SECRETARY,
             "Company Secretary", "Governance & Compliance"),
        ]
        for i, (n, p, t, c) in enumerate(team):
            TeamMember.objects.create(name=n, position=p, title=t,
                                      credential=c, order=i)

        # ---------------------------------------------------------------- Stats
        self.stdout.write("Creating site stats…")
        stats = [("7", "+", "Years of impact"), ("20", "+", "Events hosted"),
                 ("2000", "+", "Lives touched"), ("3", "", "Active wings")]
        for i, (v, s, l) in enumerate(stats):
            SiteStat.objects.create(value=v, suffix=s, label=l, order=i)

        # ---------------------------------------------------------------- Users
        self.stdout.write("Creating users across all roles…")

        def make_user(username, first, last, role, months_ago=0, **extra):
            u = User.objects.create_user(
                username=username, password=PASSWORD,
                email=f"{username}@onesimusimpact.org",
                first_name=first, last_name=last, role=role, **extra)
            joined = now - timedelta(days=months_ago * 30 + random.randint(0, 20))
            User.objects.filter(pk=u.pk).update(date_joined=joined,
                                                created_at=joined)
            u.refresh_from_db()
            return u

        # Ensure an admin superuser exists.
        admin = User.objects.filter(username="admin").first()
        if not admin:
            admin = User.objects.create_superuser(
                username="admin", password=PASSWORD,
                email="admin@onesimusimpact.org",
                first_name="Site", last_name="Admin")
        admin.role = "ADMIN"
        admin.title = "Platform Administrator"
        admin.save()

        director = make_user("director", "Grace", "Owusu", "DIRECTOR", 14,
                             title="Executive Director")
        mentor1 = make_user("mentor", "Daniel", "Asare", "MENTOR", 11,
                            title="Forge Mentor")
        mentor2 = make_user("mentor2", "Esther", "Boateng", "MENTOR", 9,
                            title="Hadassah Mentor")
        vol1 = make_user("volunteer", "Kofi", "Mensah", "VOLUNTEER", 7,
                         title="Outreach Volunteer")
        vol2 = make_user("volunteer2", "Ama", "Serwaa", "VOLUNTEER", 5,
                         title="Events Volunteer")

        # Functional roles from Schedule B (one login each).
        global_lead = make_user("globallead", "Onesimus", "Mensah",
                                "GLOBAL_LEAD", 16, title="Global Lead & Founder")
        exec_dir = make_user("execdir", "Grace", "Owusu", "EXEC_DIRECTOR", 15,
                             title="Executive Director")
        dir_programs = make_user("dirprograms", "Daniel", "Asare",
                                 "DIR_PROGRAMS", 13, title="Director of Programmes")
        dir_ops = make_user("dirops", "Esther", "Boateng", "DIR_OPS", 12,
                            title="Director of Operations & Volunteer Engagement")
        dir_comms = make_user("dircomms", "Nana", "Adjei", "DIR_COMMS", 12,
                              title="Director of Communications, Media & Digital")
        dir_partners = make_user("dirpartners", "Kojo", "Owusu",
                                 "DIR_PARTNERSHIPS", 11,
                                 title="Director of Partnerships & Resource Mobilisation")
        finance = make_user("finance", "Abena", "Mensah", "FINANCE", 10,
                            title="Finance / Donations Manager")
        editor = make_user("editor", "Yaa", "Asante", "CONTENT_EDITOR", 9,
                           title="Content Editor")
        event_mgr = make_user("eventmgr", "Kwesi", "Darko", "EVENT_MANAGER", 8,
                              title="Event Manager")
        applicant = make_user("applicant", "Kofi", "Ansah", "APPLICANT", 2,
                              title="Prospective volunteer")
        donor = make_user("donor", "Adjoa", "Bediako", "DONOR", 6,
                          title="Recurring donor")

        member_names = [
            ("Yaw", "Boadu"), ("Akosua", "Frimpong"), ("Kwabena", "Osei"),
            ("Adwoa", "Nyarko"), ("Kojo", "Antwi"), ("Abena", "Darko"),
            ("Kwesi", "Appiah"), ("Efua", "Asante"), ("Nana", "Acheampong"),
            ("Yaa", "Gyasi"),
        ]
        members = []
        for i, (f, l) in enumerate(member_names):
            mu = make_user(f"member{i+1}", f, l, "MEMBER",
                           months_ago=random.randint(0, 12))
            members.append(mu)

        all_donors = members + [vol1, vol2, mentor1, director, donor,
                                exec_dir, dir_partners]

        # ---------------------------------------------------------------- Events
        self.stdout.write("Creating events (past + upcoming)…")
        events = []
        event_specs = [
            ("Ignite Leadership Conference 2025", Event.Kind.CONFERENCE, forge, -300),
            ("Hadassah Women's Summit 2025", Event.Kind.CONFERENCE, hadassah, -240),
            ("Forge Mentorship Cohort — Spring", Event.Kind.MENTORSHIP, forge, -180),
            ("Community Outreach: Nima", Event.Kind.OUTREACH, human, -120),
            ("Hadassah Mentorship Cohort — Summer", Event.Kind.MENTORSHIP, hadassah, -90),
            ("Leaders' Roundtable Workshop", Event.Kind.WORKSHOP, forge, -45),
            ("Ignite Leadership Conference 2026", Event.Kind.CONFERENCE, forge, 35),
            ("Humanitarian Outreach: Cape Coast", Event.Kind.OUTREACH, human, 60),
            ("Forge Mentorship Cohort — Fall", Event.Kind.MENTORSHIP, forge, 80),
        ]
        for title, kind, prog, day_offset in event_specs:
            starts = now + timedelta(days=day_offset)
            ev = Event.objects.create(
                title=title, kind=kind, program=prog, starts_at=starts,
                theme="Purpose · Leadership · Impact",
                description=("A flagship OIF gathering convening emerging leaders "
                             "for teaching, mentorship and community."),
                location="Accra International Conference Centre" if kind ==
                Event.Kind.CONFERENCE else "Virtual / Community",
                is_virtual=(kind != Event.Kind.CONFERENCE),
                capacity=random.choice([0, 100, 150, 200]),
                registration_open=(day_offset > -60))
            events.append(ev)

        upcoming = [e for e in events if e.starts_at >= now]
        past = [e for e in events if e.starts_at < now]

        # ---------------------------------------------------------------- Registrations
        self.stdout.write("Creating event registrations…")
        for ev in events:
            registrants = random.sample(members, k=random.randint(4, len(members)))
            for u in registrants:
                status = (EventRegistration.Status.ATTENDED if ev in past
                          else EventRegistration.Status.REGISTERED)
                if random.random() < 0.08:
                    status = EventRegistration.Status.CANCELLED
                reg = EventRegistration.objects.create(
                    event=ev, user=u, status=status)
                rdate = ev.starts_at - timedelta(days=random.randint(3, 25))
                backdate(EventRegistration, reg.pk, rdate)

        # ---------------------------------------------------------------- Donations
        self.stdout.write("Creating backdated donations (12 months)…")
        channels = [Donation.Channel.MOMO, Donation.Channel.MOMO,
                    Donation.Channel.CARD, Donation.Channel.BANK]
        campaigns = ["General Fund", "Mentorship Fund", "Outreach: Nima",
                     "Conference Sponsorship", "Hadassah Scholarship"]
        for month_back in range(12, -1, -1):
            n_gifts = random.randint(4, 11)
            for _ in range(n_gifts):
                donor = random.choice(all_donors)
                amount = Decimal(str(random.choice(
                    [50, 100, 150, 200, 250, 500, 750, 1000, 1500])))
                status = Donation.Status.SUCCESS
                roll = random.random()
                if roll > 0.93:
                    status = Donation.Status.FAILED
                elif roll > 0.86:
                    status = Donation.Status.PENDING
                d = Donation.objects.create(
                    donor=donor,
                    donor_name=donor.get_full_name() or donor.username,
                    donor_email=donor.email, amount=amount, currency="GHS",
                    channel=random.choice(channels), status=status,
                    reference=f"OIF-{random.randint(100000, 999999)}",
                    campaign=random.choice(campaigns),
                    is_recurring=random.random() < 0.25)
                created = (now - timedelta(days=month_back * 30
                                           + random.randint(0, 27)))
                backdate(Donation, d.pk, created)

        # ---------------------------------------------------------------- Applications
        self.stdout.write("Creating applications…")
        app_specs = [
            (members[0], Application.Kind.MENTOR, Application.Status.PENDING),
            (members[1], Application.Kind.VOLUNTEER, Application.Status.PENDING),
            (members[2], Application.Kind.MENTOR, Application.Status.APPROVED),
            (members[3], Application.Kind.VOLUNTEER, Application.Status.APPROVED),
            (members[4], Application.Kind.VOLUNTEER, Application.Status.REJECTED),
            (members[5], Application.Kind.MENTOR, Application.Status.PENDING),
        ]
        for user, kind, status in app_specs:
            app = Application.objects.create(
                user=user, kind=kind, status=status,
                area_of_interest=random.choice(
                    ["Leadership", "Community outreach", "Events & logistics",
                     "Youth discipleship", "Women's development"]),
                motivation=("I am passionate about serving young people and want "
                            "to contribute my time and skills to OIF's mission."))
            if status != Application.Status.PENDING:
                app.reviewed_by = director
                app.reviewed_at = now - timedelta(days=random.randint(5, 40))
                app.save()
                if status == Application.Status.APPROVED:
                    user.role = ("MENTOR" if kind == Application.Kind.MENTOR
                                 else "VOLUNTEER")
                    user.save(update_fields=["role"])
            backdate(Application, app.pk,
                     now - timedelta(days=random.randint(10, 60)))

        # ---------------------------------------------------------------- Mentorship
        self.stdout.write("Creating mentorship enrollments…")
        enroll_specs = [
            (members[6], mentor1, forge, MentorshipEnrollment.Phase.PHASE1, 3, "Forge — Spring 2026"),
            (members[7], mentor2, hadassah, MentorshipEnrollment.Phase.PHASE2, 9, "Hadassah — Summer 2025"),
            (members[8], mentor1, forge, MentorshipEnrollment.Phase.PHASE2, 7, "Forge — Spring 2026"),
            (members[9], mentor2, hadassah, MentorshipEnrollment.Phase.COMPLETE, 12, "Hadassah — Summer 2025"),
            (members[0], mentor1, forge, MentorshipEnrollment.Phase.PHASE1, 2, "Forge — Fall 2026"),
            (members[2], mentor2, hadassah, MentorshipEnrollment.Phase.PHASE1, 5, "Hadassah — Fall 2026"),
        ]
        for mentee, mentor, prog, phase, done, cohort in enroll_specs:
            en = MentorshipEnrollment.objects.create(
                mentee=mentee, mentor=mentor, program=prog, phase=phase,
                cohort=cohort, sessions_completed=done, sessions_total=12)
            backdate(MentorshipEnrollment, en.pk,
                     now - timedelta(days=random.randint(20, 120)))

        # ---------------------------------------------------------------- Testimonials
        self.stdout.write("Creating testimonials…")
        testimonials = [
            ("Akosua Frimpong", "Forge Cohort '25", Testimonial.Source.CONFERENCE,
             "The Ignite Conference gave me language for a calling I could only "
             "feel before. I left with clarity and courage."),
            ("Kwabena Osei", "Mentee, Forge", Testimonial.Source.MENTORSHIP,
             "My mentor walked with me through decisions I would have rushed. "
             "The two-phase structure kept me accountable."),
            ("Adwoa Nyarko", "Hadassah Summit attendee", Testimonial.Source.CONFERENCE,
             "I met women leading with grace and grit. It reshaped how I see my "
             "own leadership."),
            ("Efua Asante", "Mentee, Hadassah", Testimonial.Source.MENTORSHIP,
             "The live sessions were the turning point — practical, personal, and "
             "deeply encouraging."),
            ("Kojo Antwi", "Nima Outreach volunteer", Testimonial.Source.OUTREACH,
             "Serving with OIF in Nima reminded me that dignity is restored one "
             "relationship at a time."),
        ]
        for i, (a, r, src, q) in enumerate(testimonials):
            Testimonial.objects.create(author=a, author_role=r, source=src,
                                       quote=q, is_published=True, order=i)

        # ---------------------------------------------------------------- Gallery
        self.stdout.write("Creating gallery placeholders…")
        gallery_specs = [
            ("Ignite Conference 2025 — main session", forge),
            ("Hadassah Summit — panel", hadassah),
            ("Nima community outreach", human),
            ("Forge mentorship live session", forge),
            ("Volunteers packing relief items", human),
            ("Cape Coast outreach team", human),
            ("Leaders' roundtable", forge),
            ("Hadassah cohort graduation", hadassah),
        ]
        for i, (cap, prog) in enumerate(gallery_specs):
            GalleryImage.objects.create(caption=cap, program=prog,
                                        is_published=True, order=i)

        # ---------------------------------------------------------------- Policies
        self.stdout.write("Creating placeholder policies…")
        policy_specs = [
            (Policy.Kind.PRIVACY, "Privacy Policy",
             "Onesimus Impact Foundation collects only the personal data needed "
             "to deliver our programmes — such as your name, contact details and "
             "application information.\n\nWe act as the data controller for this "
             "information and process it in line with the Data Protection Act, "
             "2012 (Act 843) of Ghana.\n\nThis is placeholder text to be replaced "
             "with the Foundation's final, legally reviewed privacy notice."),
            (Policy.Kind.TERMS, "Terms of Use",
             "By using this website you agree to use it lawfully and to respect "
             "the intellectual property of the Onesimus Impact Foundation.\n\n"
             "This is placeholder text to be replaced with the Foundation's final "
             "terms of use."),
            (Policy.Kind.DONATION, "Donation Policy",
             "Donations to the Onesimus Impact Foundation support conferences, "
             "mentorship and humanitarian work. Gifts are processed securely "
             "through Paystack (mobile money and card) or by bank transfer.\n\n"
             "Donations are generally non-refundable except where a transaction "
             "was made in error.\n\nThis is placeholder text to be replaced with "
             "the Foundation's final donation policy."),
        ]
        for kind, title, body in policy_specs:
            Policy.objects.create(kind=kind, title=title, body=body,
                                  is_placeholder=True)

        # ---------------------------------------------------------------- Enquiries
        self.stdout.write("Creating contact & partner enquiries…")
        contact_specs = [
            ("Yaw Mensah", "yaw@example.com", "Volunteering",
             "How can my church youth group volunteer at the next outreach?",
             ContactMessage.Status.NEW),
            ("Ama Owusu", "ama@example.com", "Mentorship",
             "Is the mentorship programme open to graduates outside Accra?",
             ContactMessage.Status.READ),
            ("Kofi Boateng", "kofi@example.com", "Media",
             "We'd love to feature OIF on our podcast. Who should we contact?",
             ContactMessage.Status.RESOLVED),
        ]
        for name, email, subject, message, status in contact_specs:
            m = ContactMessage.objects.create(
                name=name, email=email, subject=subject, message=message,
                status=status)
            if status != ContactMessage.Status.NEW:
                m.handled_by = director
                m.save(update_fields=["handled_by"])
            backdate(ContactMessage, m.pk,
                     now - timedelta(days=random.randint(2, 40)))

        partner_specs = [
            ("Kasapreko Foundation", "Nana Yaw", "partners@kasapreko.example",
             PartnerEnquiry.Kind.SPONSOR, "We'd like to sponsor the next Ignite "
             "Conference.", PartnerEnquiry.Status.NEW),
            ("Ecobank Ghana CSR", "Efua Danso", "csr@ecobank.example",
             PartnerEnquiry.Kind.PARTNER, "Exploring a mentorship partnership for "
             "young professionals.", PartnerEnquiry.Status.IN_REVIEW),
            ("Diaspora Giving Circle", "Kwame Boadi", "hello@diaspora.example",
             PartnerEnquiry.Kind.DONOR, "Our circle would like to fund a Hadassah "
             "scholarship cohort.", PartnerEnquiry.Status.ENGAGED),
        ]
        for org, contact, email, kind, msg, status in partner_specs:
            e = PartnerEnquiry.objects.create(
                organisation=org, contact_name=contact, email=email, kind=kind,
                message=msg, status=status)
            if status != PartnerEnquiry.Status.NEW:
                e.handled_by = dir_partners
                e.save(update_fields=["handled_by"])
            backdate(PartnerEnquiry, e.pk,
                     now - timedelta(days=random.randint(3, 50)))

        # ---------------------------------------------------------------- Newsletter
        for i in range(12):
            NewsletterSubscriber.objects.create(
                email=f"subscriber{i+1}@example.com",
                name=random.choice(["", "Kwame", "Ama", "Yaa", "Kojo"]))

        # ---------------------------------------------------------------- Audit trail
        self.stdout.write("Creating sample audit records…")
        log_action(admin, "seed.run", "demo dataset", "Initial seed")
        log_action(dir_partners, "partner.status", "Ecobank Ghana CSR", "IN_REVIEW")
        log_action(director, "application.review", "Volunteer — member4", "APPROVED")
        log_action(finance, "donation.status", "OIF-DEMO0001", "SUCCESS")
        log_action(editor, "content.update.testimonials", "Akosua Frimpong")

        # ---------------------------------------------------------- Accounting
        from dashboard.accounting import ensure_accounting_defaults, post_donation
        ensure_accounting_defaults()
        for donation in Donation.objects.filter(status=Donation.Status.SUCCESS):
            post_donation(donation, finance)

        # ---------------------------------------------------------------- Summary
        self.stdout.write(self.style.SUCCESS(
            "\nDemo data created successfully!\n"
            f"  Users:         {User.objects.count()}\n"
            f"  Programs:      {Program.objects.count()}\n"
            f"  Events:        {Event.objects.count()}\n"
            f"  Registrations: {EventRegistration.objects.count()}\n"
            f"  Donations:     {Donation.objects.count()}\n"
            f"  Applications:  {Application.objects.count()}\n"
            f"  Mentorships:   {MentorshipEnrollment.objects.count()}\n"
            f"  Testimonials:  {Testimonial.objects.count()}\n"
            f"  Gallery:       {GalleryImage.objects.count()}\n"
            f"  Policies:      {Policy.objects.count()}\n"
            f"  Contact msgs:  {ContactMessage.objects.count()}\n"
            f"  Partner enqs:  {PartnerEnquiry.objects.count()}\n"
            f"  Subscribers:   {NewsletterSubscriber.objects.count()}\n"
            f"  Audit records: {AuditLog.objects.count()}\n"))
        self.stdout.write(
            "Login accounts (password for all: %s):\n"
            "  admin (superuser)\n"
            "  globallead / execdir / director\n"
            "  dirprograms / dirops / dircomms / dirpartners\n"
            "  finance / editor / eventmgr\n"
            "  mentor / mentor2 / volunteer / volunteer2\n"
            "  applicant / donor / member1 … member10\n" % PASSWORD)
