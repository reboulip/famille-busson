"""Idempotent registration of django-q2 Schedule rows (9.6)."""

import pytest
from django.core.management import call_command
from django_q.models import Schedule


@pytest.mark.django_db
def test_creates_both_schedules():
    call_command("sync_scheduled_tasks")

    assert Schedule.objects.filter(name="send_daily_birthday_reminders").exists()
    assert Schedule.objects.filter(name="extract_pending_documents").exists()


@pytest.mark.django_db
def test_creates_event_reminder_schedule():
    call_command("sync_scheduled_tasks")

    reminder = Schedule.objects.get(name="send_event_reminders")
    assert reminder.func == "events.tasks.send_event_reminders"
    assert reminder.schedule_type == Schedule.DAILY


@pytest.mark.django_db
def test_schedules_point_at_the_right_callables():
    call_command("sync_scheduled_tasks")

    birthday = Schedule.objects.get(name="send_daily_birthday_reminders")
    assert birthday.func == "annuaire.tasks.send_daily_birthday_reminders"
    assert birthday.schedule_type == Schedule.DAILY

    extraction = Schedule.objects.get(name="extract_pending_documents")
    assert extraction.func == "documents.tasks.process_pending_document_files"
    assert extraction.schedule_type == Schedule.MINUTES
    assert extraction.minutes == 15


@pytest.mark.django_db
def test_running_it_twice_does_not_duplicate_schedules():
    call_command("sync_scheduled_tasks")
    call_command("sync_scheduled_tasks")

    assert Schedule.objects.filter(name="send_daily_birthday_reminders").count() == 1
    assert Schedule.objects.filter(name="extract_pending_documents").count() == 1


@pytest.mark.django_db
def test_running_it_again_does_not_push_next_run_back():
    call_command("sync_scheduled_tasks")
    first_next_run = Schedule.objects.get(name="send_daily_birthday_reminders").next_run

    call_command("sync_scheduled_tasks")
    second_next_run = Schedule.objects.get(name="send_daily_birthday_reminders").next_run

    assert first_next_run == second_next_run
