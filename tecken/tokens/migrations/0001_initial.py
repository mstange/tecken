# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Generated by Django 1.11.1 on 2017-06-01 18:59

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import tecken.tokens.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("auth", "0008_alter_user_username_max_length"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Token",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "key",
                    models.CharField(
                        default=tecken.tokens.models.make_key, max_length=32
                    ),
                ),
                (
                    "expires_at",
                    models.DateTimeField(default=tecken.tokens.models.get_future),
                ),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("permissions", models.ManyToManyField(to="auth.Permission")),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
