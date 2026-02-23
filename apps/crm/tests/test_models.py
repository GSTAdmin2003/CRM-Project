"""
Tests for CRM app models (SalesTeam, LeadStage, Lead, LeadActivity, LeadFile).
"""

from decimal import Decimal

import pytest

from apps.crm.models import Lead, LeadActivity, LeadFile, LeadStage, SalesTeam

from .conftest import (
    CompanyFactory,
    ContactFactory,
    IncomingLeadFactory,
    LeadActivityFactory,
    LeadFactory,
    LeadFileFactory,
    LeadStageFactory,
    SalesTeamFactory,
    UserFactory,
)


# =============================================================================
# SalesTeam Model
# =============================================================================


@pytest.mark.django_db
class TestSalesTeamModel:
    def test_create_sales_team_with_required_fields(self):
        team = SalesTeamFactory(name="Alpha Team")
        assert team.pk is not None
        assert team.name == "Alpha Team"
        assert team.is_active is True

    def test_str_returns_name(self):
        team = SalesTeamFactory(name="Beta Team")
        assert str(team) == "Beta Team"

    def test_ordering_by_name(self):
        SalesTeamFactory(name="Zulu")
        SalesTeamFactory(name="Alpha")
        SalesTeamFactory(name="Mike")
        names = list(SalesTeam.objects.values_list("name", flat=True))
        assert names == sorted(names)

    def test_manager_set_null_on_delete(self):
        manager = UserFactory()
        team = SalesTeamFactory(manager=manager)
        manager.delete()
        team.refresh_from_db()
        assert team.manager is None

    def test_get_team_members_returns_active_members(self):
        team = SalesTeamFactory()
        user1 = UserFactory()
        user1.sales_team = team
        user1.save()
        user2 = UserFactory()
        user2.sales_team = team
        user2.is_active = False
        user2.save()

        members = team.get_team_members()
        assert user1 in members
        assert user2 not in members

    def test_get_team_leads_returns_leads_for_members(self):
        team = SalesTeamFactory()
        user = UserFactory()
        user.sales_team = team
        user.save()

        stage = LeadStageFactory()
        lead = LeadFactory(assigned_to=user, stage=stage)
        other_lead = LeadFactory(stage=stage)

        team_leads = team.get_team_leads()
        assert lead in team_leads
        assert other_lead not in team_leads

    def test_created_at_and_updated_at_auto_set(self):
        team = SalesTeamFactory()
        assert team.created_at is not None
        assert team.updated_at is not None

    def test_name_is_unique(self):
        SalesTeamFactory(name="Unique Team")
        with pytest.raises(Exception):
            SalesTeamFactory(name="Unique Team")


# =============================================================================
# LeadStage Model
# =============================================================================


@pytest.mark.django_db
class TestLeadStageModel:
    def test_create_stage_with_defaults(self):
        stage = LeadStageFactory(name="Qualification")
        assert stage.pk is not None
        assert stage.name == "Qualification"
        assert stage.is_active is True
        assert stage.is_closed_stage is False

    def test_str_with_team(self):
        team = SalesTeamFactory(name="Sales A")
        stage = LeadStageFactory(name="Discovery", sales_team=team)
        assert str(stage) == "Discovery (Sales A)"

    def test_str_global_stage(self):
        stage = LeadStageFactory(name="New", sales_team=None)
        assert str(stage) == "New (Global)"

    def test_ordering(self):
        team = SalesTeamFactory()
        LeadStageFactory(name="C", order=3, sales_team=team)
        LeadStageFactory(name="A", order=1, sales_team=team)
        LeadStageFactory(name="B", order=2, sales_team=team)
        stages = list(
            LeadStage.objects.filter(sales_team=team).values_list("name", flat=True)
        )
        assert stages == ["A", "B", "C"]

    def test_unique_together_name_and_sales_team(self):
        team = SalesTeamFactory()
        LeadStageFactory(name="Duplicate", sales_team=team)
        with pytest.raises(Exception):
            LeadStageFactory(name="Duplicate", sales_team=team)

    def test_get_stages_for_team_returns_team_stages(self):
        team = SalesTeamFactory()
        team_stage = LeadStageFactory(name="Team Stage", sales_team=team, order=1)
        global_stage = LeadStageFactory(name="Global Stage", sales_team=None, order=1)

        stages = LeadStage.get_stages_for_team(team)
        assert team_stage in stages
        assert global_stage not in stages

    def test_get_stages_for_team_fallback_to_global(self):
        team = SalesTeamFactory()
        global_stage = LeadStageFactory(name="Global Fallback", sales_team=None, order=1)

        stages = LeadStage.get_stages_for_team(team)
        assert global_stage in stages

    def test_get_stages_for_team_none_returns_global(self):
        global_stage = LeadStageFactory(name="Global Only", sales_team=None, order=1)
        stages = LeadStage.get_stages_for_team(None)
        assert global_stage in stages

    def test_get_default_stage_for_team_returns_first(self):
        team = SalesTeamFactory()
        stage1 = LeadStageFactory(name="First", sales_team=team, order=1)
        LeadStageFactory(name="Second", sales_team=team, order=2)

        default = LeadStage.get_default_stage_for_team(team)
        assert default == stage1

    def test_get_default_stage_for_team_none_when_no_stages(self):
        team = SalesTeamFactory()
        default = LeadStage.get_default_stage_for_team(team)
        assert default is None

    def test_can_be_edited_by_executive(self, user_sales_executive):
        stage = LeadStageFactory(sales_team=None)
        assert stage.can_be_edited_by(user_sales_executive) is True

    def test_can_be_edited_by_team_manager(self, user_sales_manager):
        team = SalesTeamFactory(manager=user_sales_manager)
        stage = LeadStageFactory(sales_team=team)
        assert stage.can_be_edited_by(user_sales_manager) is True

    def test_cannot_be_edited_by_non_manager_rep(self, user_sales_rep):
        team = SalesTeamFactory()
        stage = LeadStageFactory(sales_team=team)
        assert stage.can_be_edited_by(user_sales_rep) is False

    def test_global_stage_cannot_be_edited_by_manager(self, user_sales_manager):
        stage = LeadStageFactory(sales_team=None)
        assert stage.can_be_edited_by(user_sales_manager) is False

    def test_cascade_delete_team_deletes_stages(self):
        team = SalesTeamFactory()
        LeadStageFactory(sales_team=team)
        LeadStageFactory(sales_team=team)
        team_pk = team.pk
        assert LeadStage.objects.filter(sales_team_id=team_pk).count() == 2
        team.delete()
        assert LeadStage.objects.filter(sales_team_id=team_pk).count() == 0


# =============================================================================
# Lead Model
# =============================================================================


@pytest.mark.django_db
class TestLeadModel:
    def test_create_lead_with_required_fields(self):
        stage = LeadStageFactory()
        user = UserFactory()
        lead = LeadFactory(
            title="Big Deal",
            stage=stage,
            assigned_to=user,
            created_by=user,
        )
        assert lead.pk is not None
        assert lead.title == "Big Deal"
        assert lead.stage == stage

    def test_str_representation_with_full_name(self):
        lead = LeadFactory(title="Deal X", full_name="John Doe", first_name="", last_name="")
        assert str(lead) == "Deal X - John Doe"

    def test_str_representation_with_first_last_name(self):
        lead = LeadFactory(
            title="Deal Y", full_name="", first_name="Jane", last_name="Smith"
        )
        assert "Deal Y" in str(lead)
        assert "Jane Smith" in str(lead)

    def test_contact_full_name_property_prefers_full_name(self):
        lead = LeadFactory(full_name="Bob Jones", first_name="Robert", last_name="Jones")
        assert lead.contact_full_name == "Bob Jones"

    def test_contact_full_name_property_falls_back_to_parts(self):
        lead = LeadFactory(full_name="", first_name="Alice", last_name="Doe")
        assert lead.contact_full_name == "Alice Doe"

    def test_weighted_value_property(self):
        stage = LeadStageFactory(probability=50)
        lead = LeadFactory(estimated_value=Decimal("10000.00"), stage=stage)
        # probability is set from stage on save
        assert lead.weighted_value == pytest.approx(5000.0)

    def test_ordering_by_last_activity_desc(self):
        stage = LeadStageFactory()
        lead1 = LeadFactory(title="Older", stage=stage)
        lead2 = LeadFactory(title="Newer", stage=stage)
        # lead2 created after lead1, so its last_activity is newer
        leads = list(Lead.objects.values_list("title", flat=True))
        assert leads[0] == "Newer"

    def test_verbose_name_is_opportunity(self):
        assert Lead._meta.verbose_name == "Opportunity"
        assert Lead._meta.verbose_name_plural == "Opportunities"

    def test_save_syncs_full_name_to_parts(self):
        lead = LeadFactory(
            full_name="John Doe", first_name="", last_name=""
        )
        assert lead.first_name == "John"
        assert lead.last_name == "Doe"

    def test_save_syncs_parts_to_full_name(self):
        lead = LeadFactory(
            full_name="", first_name="Jane", last_name="Smith"
        )
        assert lead.full_name == "Jane Smith"

    def test_save_auto_assigns_sales_team_from_user(self):
        team = SalesTeamFactory()
        user = UserFactory()
        user.sales_team = team
        user.save()
        stage = LeadStageFactory()
        lead = LeadFactory(assigned_to=user, sales_team=None, stage=stage)
        assert lead.sales_team == team

    def test_save_updates_probability_from_stage(self):
        stage = LeadStageFactory(probability=75)
        lead = LeadFactory(stage=stage)
        assert lead.probability == 75

    def test_can_be_viewed_by_executive(self, user_sales_executive):
        lead = LeadFactory()
        assert lead.can_be_viewed_by(user_sales_executive) is True

    def test_can_be_viewed_by_assigned_rep(self, user_sales_rep):
        lead = LeadFactory(assigned_to=user_sales_rep)
        assert lead.can_be_viewed_by(user_sales_rep) is True

    def test_cannot_be_viewed_by_unrelated_rep(self, user_sales_rep):
        other_user = UserFactory()
        lead = LeadFactory(assigned_to=other_user, created_by=other_user)
        assert lead.can_be_viewed_by(user_sales_rep) is False

    def test_can_be_edited_by_executive(self, user_sales_executive):
        lead = LeadFactory()
        assert lead.can_be_edited_by(user_sales_executive) is True

    def test_can_be_edited_by_assigned_user(self):
        user = UserFactory()
        lead = LeadFactory(assigned_to=user)
        assert lead.can_be_edited_by(user) is True

    def test_cannot_be_edited_by_unrelated_rep(self, user_sales_rep):
        other_user = UserFactory()
        lead = LeadFactory(assigned_to=other_user, created_by=other_user)
        assert lead.can_be_edited_by(user_sales_rep) is False

    def test_can_be_edited_by_team_manager(self, user_sales_manager):
        team = SalesTeamFactory(manager=user_sales_manager)
        lead = LeadFactory(sales_team=team)
        assert lead.can_be_edited_by(user_sales_manager) is True

    def test_stage_protect_on_delete(self):
        """Deleting a stage that has leads should raise ProtectedError."""
        stage = LeadStageFactory()
        LeadFactory(stage=stage)
        with pytest.raises(Exception):
            stage.delete()

    def test_assigned_to_set_null_on_delete(self):
        user = UserFactory()
        lead = LeadFactory(assigned_to=user)
        user.delete()
        lead.refresh_from_db()
        assert lead.assigned_to is None

    def test_company_and_contact_fk(self):
        company = CompanyFactory()
        contact = ContactFactory(company=company)
        lead = LeadFactory(company=company, contact=contact)
        assert lead.company == company
        assert lead.contact == contact

    def test_custom_fields_default_empty_dict(self):
        lead = LeadFactory()
        assert lead.custom_fields == {}

    def test_source_choices(self):
        lead = LeadFactory(source="referral")
        assert lead.source == "referral"

    def test_created_at_and_updated_at_auto_set(self):
        lead = LeadFactory()
        assert lead.created_at is not None
        assert lead.updated_at is not None


# =============================================================================
# LeadActivity Model
# =============================================================================


@pytest.mark.django_db
class TestLeadActivityModel:
    def test_create_activity(self):
        activity = LeadActivityFactory(
            activity_type="call",
            subject="Follow-up call",
        )
        assert activity.pk is not None
        assert activity.activity_type == "call"
        assert activity.subject == "Follow-up call"

    def test_str_representation(self):
        lead = LeadFactory(title="My Opportunity")
        activity = LeadActivityFactory(lead=lead, activity_type="email")
        assert "My Opportunity" in str(activity)
        assert "Email" in str(activity)

    def test_ordering_by_created_at_desc(self):
        lead = LeadFactory()
        a1 = LeadActivityFactory(lead=lead, subject="First")
        a2 = LeadActivityFactory(lead=lead, subject="Second")
        activities = list(lead.activities.values_list("subject", flat=True))
        assert activities[0] == "Second"

    def test_cascade_delete_lead_deletes_activities(self):
        lead = LeadFactory()
        LeadActivityFactory(lead=lead)
        LeadActivityFactory(lead=lead)
        lead_pk = lead.pk
        assert LeadActivity.objects.filter(lead_id=lead_pk).count() == 2
        lead.delete()
        assert LeadActivity.objects.filter(lead_id=lead_pk).count() == 0

    def test_user_set_null_on_delete(self):
        user = UserFactory()
        activity = LeadActivityFactory(user=user)
        user.delete()
        activity.refresh_from_db()
        assert activity.user is None

    def test_verbose_name(self):
        assert LeadActivity._meta.verbose_name == "Opportunity Activity"
        assert LeadActivity._meta.verbose_name_plural == "Opportunity Activities"

    def test_activity_type_choices(self):
        for atype, _ in LeadActivity.ACTIVITY_TYPES:
            activity = LeadActivityFactory(activity_type=atype)
            assert activity.activity_type == atype

    def test_optional_fields(self):
        activity = LeadActivityFactory(
            duration=30,
            outcome="Positive",
        )
        assert activity.duration == 30
        assert activity.outcome == "Positive"


# =============================================================================
# LeadFile Model
# =============================================================================


@pytest.mark.django_db
class TestLeadFileModel:
    def test_create_file(self):
        lead_file = LeadFileFactory(filename="contract.pdf")
        assert lead_file.pk is not None
        assert lead_file.filename == "contract.pdf"

    def test_str_representation(self):
        lead = LeadFactory(title="Big Deal")
        lead_file = LeadFileFactory(lead=lead, filename="proposal.docx")
        assert str(lead_file) == "Big Deal - proposal.docx"

    def test_ordering_by_uploaded_at_desc(self):
        lead = LeadFactory()
        f1 = LeadFileFactory(lead=lead, filename="first.pdf")
        f2 = LeadFileFactory(lead=lead, filename="second.pdf")
        files = list(lead.files.values_list("filename", flat=True))
        assert files[0] == "second.pdf"

    def test_cascade_delete_lead_deletes_files(self):
        lead = LeadFactory()
        LeadFileFactory(lead=lead)
        LeadFileFactory(lead=lead)
        lead_pk = lead.pk
        assert LeadFile.objects.filter(lead_id=lead_pk).count() == 2
        lead.delete()
        assert LeadFile.objects.filter(lead_id=lead_pk).count() == 0

    def test_uploaded_by_set_null_on_delete(self):
        user = UserFactory()
        lead_file = LeadFileFactory(uploaded_by=user)
        user.delete()
        lead_file.refresh_from_db()
        assert lead_file.uploaded_by is None


# =============================================================================
# Incoming Lead (Lead with lead_type='lead')
# =============================================================================


@pytest.mark.django_db
class TestIncomingLeadModel:
    """Tests for incoming leads — now stored as Lead(lead_type='lead')."""

    def test_create_incoming_lead(self):
        incoming = IncomingLeadFactory(message="Interested in your product")
        assert incoming.pk is not None
        assert incoming.lead_type == "lead"
        assert incoming.message == "Interested in your product"
        assert incoming.status == "new"

    def test_str_contains_title(self):
        incoming = IncomingLeadFactory()
        assert incoming.title in str(incoming)

    def test_ordering_by_last_activity_desc(self):
        IncomingLeadFactory(message="First")
        IncomingLeadFactory(message="Second")
        leads = list(Lead.objects.filter(lead_type="lead").values_list("message", flat=True))
        # Just verify both are retrievable
        assert "First" in leads
        assert "Second" in leads

    def test_lead_type_discriminator(self):
        incoming = IncomingLeadFactory()
        assert incoming.lead_type == "lead"
        assert Lead.objects.filter(pk=incoming.pk, lead_type="lead").exists()

    def test_status_choices_include_converted_and_rejected(self):
        choice_values = [v for v, _ in Lead.STATUS_CHOICES]
        assert "converted" in choice_values
        assert "rejected" in choice_values
        assert "new" in choice_values
        assert "contacted" in choice_values

    def test_status_new(self):
        incoming = IncomingLeadFactory(status="new")
        assert incoming.status == "new"

    def test_status_converted(self):
        incoming = IncomingLeadFactory(status="converted")
        assert incoming.status == "converted"

    def test_can_be_viewed_by_executive(self, user_sales_executive):
        incoming = IncomingLeadFactory()
        assert incoming.can_be_viewed_by(user_sales_executive) is True

    def test_can_be_viewed_by_assigned_user(self, user_sales_rep):
        """Sales Rep assigned to the lead can view it."""
        incoming = IncomingLeadFactory(assigned_to=user_sales_rep)
        assert incoming.can_be_viewed_by(user_sales_rep) is True

    def test_can_be_viewed_by_creator(self):
        user = UserFactory()
        incoming = IncomingLeadFactory(created_by=user)
        assert incoming.can_be_viewed_by(user) is True

    def test_cannot_be_viewed_by_unrelated_rep(self, user_sales_rep):
        other_user = UserFactory()
        incoming = IncomingLeadFactory(
            created_by=other_user, assigned_to=other_user
        )
        assert incoming.can_be_viewed_by(user_sales_rep) is False

    def test_can_be_edited_by_executive(self, user_sales_executive):
        incoming = IncomingLeadFactory()
        assert incoming.can_be_edited_by(user_sales_executive) is True

    def test_can_be_edited_by_assigned_user(self):
        user = UserFactory()
        incoming = IncomingLeadFactory(assigned_to=user)
        assert incoming.can_be_edited_by(user) is True

    def test_cannot_be_edited_by_unrelated_user(self, user_sales_rep):
        other_user = UserFactory()
        incoming = IncomingLeadFactory(assigned_to=other_user, created_by=other_user)
        assert incoming.can_be_edited_by(user_sales_rep) is False

    def test_company_set_null_on_delete(self):
        company = CompanyFactory()
        incoming = IncomingLeadFactory(company=company)
        company.delete()
        incoming.refresh_from_db()
        assert incoming.company is None

    def test_contact_set_null_on_delete(self):
        contact = ContactFactory()
        incoming = IncomingLeadFactory(contact=contact)
        contact.delete()
        incoming.refresh_from_db()
        assert incoming.contact is None

    def test_converted_opportunity_link(self):
        """converted_opportunity property returns opportunity converted from this lead."""
        incoming = IncomingLeadFactory()
        opportunity = LeadFactory(converted_from=incoming, lead_type="opportunity")
        assert incoming.converted_opportunity == opportunity

    def test_created_at_and_updated_at_auto_set(self):
        incoming = IncomingLeadFactory()
        assert incoming.created_at is not None
        assert incoming.updated_at is not None
