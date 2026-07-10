from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from accounts.models import Role, User
from donations.models import Donation
from donations.views import _mark_success
from .accounting import (ensure_accounting_defaults, financial_statements,
                         post_journal, reverse_journal)
from .models import (BankReconciliation, Budget, BudgetLine, CashAccount,
                     FiscalPeriod, Fund, JournalEntry, JournalLine,
                     LedgerAccount)

PWD = "accounting-test-pass"


class AccountingCoreTest(TestCase):
    def setUp(self):
        self.finance = User.objects.create_user(
            username="accountant", password=PWD, role=Role.FINANCE
        )
        self.member = User.objects.create_user(
            username="accounting_member", password=PWD, role=Role.MEMBER
        )
        self.accounts, self.fund = ensure_accounting_defaults()
        self.period = FiscalPeriod.objects.create(
            name="FY 2030", starts_on=date(2030, 1, 1), ends_on=date(2030, 12, 31)
        )

    def journal(self, amount="100.00"):
        journal = JournalEntry.objects.create(
            entry_date=date(2030, 3, 1), description="Balanced test",
            fiscal_period=self.period, fund=self.fund, created_by=self.finance,
        )
        JournalLine.objects.create(
            journal=journal, account=self.accounts["1000"], debit=amount
        )
        JournalLine.objects.create(
            journal=journal, account=self.accounts["4000"], credit=amount
        )
        return journal

    def test_balanced_journal_posts_and_reverses(self):
        journal = post_journal(self.journal(), self.finance)
        self.assertEqual(journal.status, JournalEntry.Status.POSTED)
        self.assertTrue(journal.is_balanced)
        reversal = reverse_journal(journal, self.finance, date(2030, 3, 2))
        journal.refresh_from_db()
        self.assertEqual(journal.status, JournalEntry.Status.REVERSED)
        self.assertEqual(reversal.total_debits, Decimal("100.00"))
        self.assertEqual(reversal.total_credits, Decimal("100.00"))

    def test_unbalanced_or_closed_period_journal_cannot_post(self):
        journal = self.journal()
        journal.lines.filter(credit__gt=0).update(credit="90.00")
        with self.assertRaises(ValidationError):
            post_journal(journal, self.finance)
        journal.lines.filter(credit__gt=0).update(credit="100.00")
        self.period.status = FiscalPeriod.Status.CLOSED
        self.period.save(update_fields=["status"])
        with self.assertRaises(ValidationError):
            post_journal(journal, self.finance)

    def test_statements_and_budget_variance_come_from_posted_ledger(self):
        post_journal(self.journal("250.00"), self.finance)
        budget = Budget.objects.create(
            name="Annual plan", fiscal_period=self.period, fund=self.fund,
            status=Budget.Status.APPROVED, created_by=self.finance,
        )
        BudgetLine.objects.create(
            budget=budget, account=self.accounts["4000"], amount="300.00"
        )
        statements = financial_statements(
            date(2030, 1, 1), date(2030, 12, 31), self.fund, budget
        )
        self.assertEqual(statements["income"], Decimal("250.00"))
        self.assertEqual(statements["surplus"], Decimal("250.00"))
        self.assertEqual(statements["trial_debits"], statements["trial_credits"])
        self.assertEqual(statements["budget_rows"][0]["variance"], Decimal("-50.00"))
        self.client.login(username="accountant", password=PWD)
        report = self.client.get(reverse("dashboard:reports"), {
            "start": "2030-01-01", "end": "2030-12-31",
        })
        self.assertContains(report, "Operating margin")
        self.assertContains(report, "Trial balance")
        export = self.client.get(reverse("dashboard:reports_export"), {
            "type": "finance", "start": "2030-01-01", "end": "2030-12-31",
        })
        self.assertIn("accounting,trial_balance", export.content.decode())

    def test_successful_donation_creates_one_idempotent_journal(self):
        donation = Donation.objects.create(
            donor_name="Ama", amount="80.00", reference="AUTO-JOURNAL",
            status=Donation.Status.PENDING,
        )
        _mark_success(donation)
        _mark_success(donation)
        journal = JournalEntry.objects.get(source_type="donation", source_id=donation.pk)
        self.assertEqual(journal.status, JournalEntry.Status.POSTED)
        self.assertEqual(journal.total_debits, Decimal("80.00"))

    def test_reconciliation_requires_zero_difference(self):
        account = CashAccount.objects.create(name="Main bank", currency="GHS")
        reconciliation = BankReconciliation.objects.create(
            account=account, statement_date=date(2030, 3, 31),
            statement_balance="100.00", book_balance="110.00",
            prepared_by=self.finance,
        )
        self.client.login(username="accountant", password=PWD)
        response = self.client.post(
            reverse("dashboard:reconciliation_action", args=[reconciliation.pk])
        )
        reconciliation.refresh_from_db()
        self.assertEqual(reconciliation.status, BankReconciliation.Status.DRAFT)
        reconciliation.book_balance = Decimal("100.00")
        reconciliation.save(update_fields=["book_balance"])
        self.client.post(
            reverse("dashboard:reconciliation_action", args=[reconciliation.pk])
        )
        reconciliation.refresh_from_db()
        self.assertEqual(reconciliation.status, BankReconciliation.Status.RECONCILED)

    def test_accounting_workspace_is_role_compliant(self):
        self.client.login(username="accounting_member", password=PWD)
        self.assertEqual(self.client.get(reverse("dashboard:accounting_core")).status_code, 403)
        self.client.logout()
        self.client.login(username="accountant", password=PWD)
        response = self.client.get(reverse("dashboard:accounting_core"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Statements &amp; Ledger", html=True)
        self.assertContains(response, "Trial balance")
        self.assertContains(response, "Financial Position")
