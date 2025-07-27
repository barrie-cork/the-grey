from django import forms

from .models import SearchSession


class SessionCreateForm(forms.ModelForm):
    """Minimal form for session creation - just title and description."""

    class Meta:
        model = SearchSession
        fields = ["title", "description"]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g., Diabetes Management Guidelines Review",
                    "autofocus": True,
                    "required": True,
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Brief description of your systematic review objectives (optional)",
                    "rows": 3,
                }
            ),
        }
        labels = {"title": "Review Title", "description": "Description (Optional)"}
        help_texts = {
            "title": "Give your review a clear, descriptive title",
            "description": "Add any additional context or objectives",
        }


class SessionEditForm(forms.ModelForm):
    """Form for editing session title and description only."""

    class Meta:
        model = SearchSession
        fields = ["title", "description"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }
