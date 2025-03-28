# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import datetime
import re

import dateutil

from django import forms
from django.contrib.auth.models import Permission, Group, User
from django.utils import timezone


class TokenForm(forms.Form):
    permissions = forms.CharField()
    notes = forms.CharField(required=False)
    expires = forms.CharField()

    def clean_expires(self):
        value = self.cleaned_data["expires"]
        try:
            return int(value)
        except ValueError:
            raise forms.ValidationError(f"Invalid number of days ({value!r})")

    def clean_permissions(self):
        value = self.cleaned_data["permissions"]
        permissions = []
        for pk in value.split(","):
            permissions.append(Permission.objects.get(id=pk))

        # Due to how we use permissions to route uploads, as a rule
        # you can not have an Token containing BOTH of these permissions.
        p1 = Permission.objects.get(codename="upload_symbols")
        p2 = Permission.objects.get(codename="upload_try_symbols")
        if p1 in permissions and p2 in permissions:
            raise forms.ValidationError("Invalid combination of permissions")

        return permissions


class ExtendTokenForm(forms.Form):
    days = forms.CharField(required=False)

    def clean_days(self):
        value = self.cleaned_data["days"]
        if value:
            try:
                return int(value)
            except ValueError:
                raise forms.ValidationError(f"Invalid number of days ({value!r})")


class TokensForm(forms.Form):
    state = forms.CharField(required=False)

    def clean_state(self):
        value = self.cleaned_data["state"]
        if value and value not in ("expired", "all"):
            raise forms.ValidationError(f"Unrecognized state value {value!r}")
        return value


class UserEditForm(forms.ModelForm):
    groups = forms.CharField(required=False)

    class Meta:
        model = User
        fields = ("is_active", "is_superuser")

    def clean_groups(self):
        value = self.cleaned_data["groups"]
        groups = []
        for pk in [x for x in value.split(",") if x.strip()]:
            try:
                groups.append(Group.objects.get(id=pk))
            except ValueError:
                raise forms.ValidationError("Invalid group ID")
        return groups


class BaseFilteringForm(forms.Form):
    sort = forms.CharField(required=False)
    reverse = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        self.valid_sorts = kwargs.pop("valid_sorts", None)
        super().__init__(*args, **kwargs)

    def _clean_dates(self, values, date=False):
        """return a list of either a datetime, date or None.
        Each one can have an operator.

        If @date is True, the values haves to be datetime.date instances only.
        """
        if not values:
            return []
        dates = []
        operators = re.compile("<=|>=|<|>|=")
        for block in [x.strip() for x in values.split(",") if x.strip()]:
            if operators.findall(block):
                (operator,) = operators.findall(block)
            else:
                operator = "="
            rest = operators.sub("", block).strip()
            if rest.lower() in ("null", "incomplete"):
                date_obj = None
            elif rest.lower() == "today":
                date_obj = timezone.now().replace(hour=0, minute=0, second=0)
            elif rest.lower() == "yesterday":
                date_obj = timezone.now().replace(hour=0, minute=0, second=0)
                date_obj -= datetime.timedelta(days=1)
            else:
                try:
                    date_obj = dateutil.parser.parse(rest)
                except ValueError:
                    raise forms.ValidationError(f"Unable to parse {rest!r}")
                if timezone.is_naive(date_obj):
                    date_obj = timezone.make_aware(date_obj)
            if date:
                date_obj = date_obj.date()
            dates.append((operator, date_obj))

        return dates

    def clean_sort(self):
        value = self.cleaned_data["sort"]
        if value and self.valid_sorts and value not in self.valid_sorts:
            raise forms.ValidationError(f"Invalid sort '{value}'")
        return value

    def clean_reverse(self):
        value = self.cleaned_data["reverse"]
        if value:
            return True if value == "true" else False

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("sort"):
            cleaned["order_by"] = {
                "sort": cleaned.pop("sort"),
                "reverse": cleaned.pop("reverse"),
            }
        return cleaned


SIZE_RE = re.compile(
    r"^(?P<operator><=|>=|<|>|=)?"
    r"\s*"
    r"(?P<num>[0-9\.]+)"
    r"\s*"
    r"(?P<multiplier>gb|g|mb|m|kb|k|b)?"
    r"$",
    re.I,
)


class CleanSizeMixin:
    def clean_size(self):
        values = self.cleaned_data["size"]
        if not values:
            return []
        sizes = []

        multiplier_aliases = {
            "gb": 1024 * 1024 * 1024,
            "g": 1024 * 1024 * 1024,
            "mb": 1024 * 1024,
            "m": 1024 * 1024,
            "kb": 1024,
            "k": 1024,
            "b": 1,
        }
        for block in [x.strip() for x in values.split(",") if x.strip()]:
            match = SIZE_RE.match(block)
            if match:
                operator = match.group("operator") or "="
                multiplier = match.group("multiplier") or "b"

                try:
                    num = match.group("num")
                    num = float(num)
                except ValueError:
                    raise forms.ValidationError(f"{block!r} is not a valid size")

                value = multiplier_aliases[multiplier.lower()] * num
                sizes.append((operator, value))
            else:
                raise forms.ValidationError(f"{block!r} is not a valid size")
        return sizes


class UploadsForm(BaseFilteringForm, CleanSizeMixin):
    user = forms.CharField(required=False)
    size = forms.CharField(required=False)
    created_at = forms.CharField(required=False)
    completed_at = forms.CharField(required=False)

    def clean_user(self):
        value = self.cleaned_data["user"]
        operator = "="  # default
        if value.startswith("!"):
            operator = "!"
            value = value[1:].strip()
        if value:
            # If it can be converted to an object, use that!
            try:
                return [operator, User.objects.get(email__icontains=value)]
            except (User.DoesNotExist, User.MultipleObjectsReturned):
                # Send the whole string which will result in a regex match
                # later.
                return [operator, value]

    def clean_created_at(self):
        return self._clean_dates(self.cleaned_data["created_at"])

    def clean_completed_at(self):
        return self._clean_dates(self.cleaned_data["completed_at"])


class UploadsCreatedForm(BaseFilteringForm, CleanSizeMixin):
    date = forms.CharField(required=False)
    size = forms.CharField(required=False)
    count = forms.CharField(required=False)

    def clean_date(self):
        return self._clean_dates(self.cleaned_data["date"], date=True)

    def clean_count(self):
        values = self.cleaned_data["count"]
        if not values:
            return []
        sizes = []
        operators = re.compile("<=|>=|<|>|=")
        for block in [x.strip() for x in values.split(",") if x.strip()]:
            if operators.findall(block):
                (operator,) = operators.findall(block)
            else:
                operator = "="
            rest = operators.sub("", block)
            try:
                rest = int(rest)
                if rest < 0:
                    raise forms.ValidationError(f"{rest!r} is negative")
            except ValueError:
                raise forms.ValidationError(f"{rest!r} is not an integer")
            sizes.append((operator, rest))
        return sizes


class FileUploadsForm(UploadsForm):
    size = forms.CharField(required=False)
    created_at = forms.CharField(required=False)
    completed_at = forms.CharField(required=False)
    key = forms.CharField(required=False)
    update = forms.BooleanField(required=False)
    compressed = forms.BooleanField(required=False)
    bucket_name = forms.CharField(required=False)

    def clean_key(self):
        values = self.cleaned_data["key"]
        if not values:
            return []
        return [x.strip() for x in values.split(",") if x.strip()]

    def clean_bucket_name(self):
        values = self.cleaned_data["bucket_name"]
        if not values:
            return []
        cleaned = []
        for value in values.split(","):
            if value.strip():
                if value.startswith("!"):
                    operator = "!"
                    value = value[1:].strip()
                else:
                    operator = "="
                cleaned.append((operator, value))
        return cleaned


COUNT_RE = re.compile(
    r"^(?P<operator><=|>=|<|>|=)?" r"\s*" r"(?P<num>\d+)" r"$",
)


class DownloadsMissingForm(BaseFilteringForm):
    symbol = forms.CharField(required=False)
    debugid = forms.CharField(required=False)
    filename = forms.CharField(required=False)
    code_file = forms.CharField(required=False)
    code_id = forms.CharField(required=False)
    modified_at = forms.CharField(required=False)
    count = forms.CharField(required=False)

    def clean_modified_at(self):
        return self._clean_dates(self.cleaned_data["modified_at"])

    def clean_count(self):
        values = self.cleaned_data["count"]
        if not values:
            return []

        counts = []
        for block in [x.strip() for x in values.split(",") if x.strip()]:
            match = COUNT_RE.match(block)
            if match:
                operator = match.group("operator") or "="
                try:
                    num = match.group("num")
                    num = int(num)
                except ValueError:
                    raise forms.ValidationError(f"{block!r} is not a valid count")
            else:
                raise forms.ValidationError(f"{block!r} is not a valid count")
            counts.append((operator, num))
        return counts
