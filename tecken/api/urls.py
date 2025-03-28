# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.urls import path

from . import views


app_name = "api"

"""
Note!
The endpoints that start with a '_' are basically only relevant
for the sake of the frontend. Meaning, it doesn't make sense to use
them in your curl script, for example.
"""

urlpatterns = [
    path("_auth/", views.auth, name="auth"),
    path("stats/", views.stats, name="stats"),
    path("stats/uploads", views.stats_uploads, name="stats_uploads"),
    path("tokens/", views.tokens, name="tokens"),
    path("tokens/token/<int:id>/extend", views.extend_token, name="extend_token"),
    path("tokens/token/<int:id>", views.delete_token, name="delete_token"),
    path(
        "uploads/_possible_upload_urls/",
        views.possible_upload_urls,
        name="possible_upload_urls",
    ),
    path("uploads/", views.uploads, name="uploads"),
    path("uploads/content/", views.uploads_content, name="uploads_content"),
    path("uploads/aggregates/", views.uploads_aggregates, name="uploads_aggregates"),
    path("uploads/created/", views.uploads_created, name="uploads_created"),
    path(
        "uploads/created/backfilled/",
        views.uploads_created_backfilled,
        name="uploads_created_backfilled",
    ),
    path("uploads/files/", views.upload_files, name="upload_files"),
    path(
        "uploads/files/content/",
        views.upload_files_content,
        name="upload_files_content",
    ),
    path(
        "uploads/files/aggregates/",
        views.upload_files_aggregates,
        name="upload_files_aggregates",
    ),
    path("uploads/files/file/<int:id>", views.upload_file, name="upload_file"),
    path("uploads/upload/<int:id>", views.upload, name="upload"),
    path("downloads/missing/", views.downloads_missing, name="downloads_missing"),
]
