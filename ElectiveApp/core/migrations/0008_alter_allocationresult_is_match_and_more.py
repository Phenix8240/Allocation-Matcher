# Generated by Django 5.2 on 2025-05-17 15:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_allocationresult"),
    ]

    operations = [
        migrations.AlterField(
            model_name="allocationresult",
            name="is_match",
            field=models.BooleanField(
                help_text="Indicates if the chosen and allocated subjects match."
            ),
        ),
        migrations.AlterField(
            model_name="student",
            name="elective_finalized",
            field=models.BooleanField(
                default=False,
                help_text="If True, the student's electives are finalized.",
            ),
        ),
    ]
