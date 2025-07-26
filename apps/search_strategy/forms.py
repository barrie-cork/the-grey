from django import forms
from django.core.exceptions import ValidationError
from typing import List, Dict, Any
from .models import SearchStrategy


class SearchStrategyForm(forms.ModelForm):
    """
    Form for creating and editing search strategies using the PIC framework.
    Provides dynamic fields for population, interest, and context terms.
    """
    
    # PIC Framework fields as text areas for dynamic input
    population_terms_text = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter population terms one at a time. These describe who the research focuses on (e.g., elderly, diabetic patients)',
            'data-field': 'population'
        }),
        required=False,
        help_text="Enter terms describing the target population (one per line)"
    )
    
    interest_terms_text = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter intervention/interest terms. These describe what you\'re studying (e.g., insulin therapy, diet management)',
            'data-field': 'interest'
        }),
        required=False,
        help_text="Enter terms describing the intervention or interest (one per line)"
    )
    
    context_terms_text = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter context terms. These describe where or under what conditions (e.g., primary care, UK)',
            'data-field': 'context'
        }),
        required=False,
        help_text="Enter terms describing the context or setting (one per line)"
    )
    
    # Organization domains
    organization_domains = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter organization domains (e.g., nice.org.uk, who.int)',
            'data-field': 'domains'
        }),
        required=False,
        help_text="Enter organization domains to search (one per line)"
    )
    
    # Search configuration checkboxes
    include_general_search = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Include general web search without domain restrictions"
    )
    
    # File types
    search_pdf = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="PDF documents"
    )
    
    search_doc = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Word documents (.doc and .docx)"
    )
    
    # Search engines
    use_google_search = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Google Web Search"
    )
    
    use_google_scholar = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Google Scholar"
    )
    
    # Maximum results per query
    max_results_per_query = forms.IntegerField(
        initial=50,
        min_value=10,
        max_value=200,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'style': 'width: 100px;'
        }),
        help_text="Maximum number of results to retrieve per query (10-200)"
    )
    
    class Meta:
        model = SearchStrategy
        fields = ['population_terms', 'interest_terms', 'context_terms', 'search_config']
        widgets = {
            'population_terms': forms.HiddenInput(),
            'interest_terms': forms.HiddenInput(),
            'context_terms': forms.HiddenInput(),
            'search_config': forms.HiddenInput(),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # If we have an instance, populate the text fields from the model
        if self.instance and self.instance.pk:
            self.fields['population_terms_text'].initial = '\n'.join(self.instance.population_terms)
            self.fields['interest_terms_text'].initial = '\n'.join(self.instance.interest_terms)
            self.fields['context_terms_text'].initial = '\n'.join(self.instance.context_terms)
            
            # Populate search configuration fields
            config = self.instance.search_config or {}
            self.fields['organization_domains'].initial = '\n'.join(config.get('domains', []))
            self.fields['include_general_search'].initial = config.get('include_general_search', True)
            
            # File types
            file_types = config.get('file_types', [])
            self.fields['search_pdf'].initial = 'pdf' in file_types
            self.fields['search_doc'].initial = 'doc' in file_types
            
            # Search engines (for future use)
            self.fields['use_google_search'].initial = config.get('search_type', 'google') == 'google'
            self.fields['use_google_scholar'].initial = config.get('search_type') == 'scholar'
            
            # Max results
            self.fields['max_results_per_query'].initial = config.get('max_results', 50)
    
    def clean(self):
        """Custom validation for the search strategy form."""
        cleaned_data = super().clean()
        
        # Convert text fields to lists
        population_text = cleaned_data.get('population_terms_text', '')
        interest_text = cleaned_data.get('interest_terms_text', '')
        context_text = cleaned_data.get('context_terms_text', '')
        domains_text = cleaned_data.get('organization_domains', '')
        
        # Parse terms from text areas
        population_terms = self._parse_terms(population_text)
        interest_terms = self._parse_terms(interest_text)
        context_terms = self._parse_terms(context_text)
        domains = self._parse_terms(domains_text)
        
        # Set the model fields
        cleaned_data['population_terms'] = population_terms
        cleaned_data['interest_terms'] = interest_terms
        cleaned_data['context_terms'] = context_terms
        
        # Build search configuration
        file_types = []
        if cleaned_data.get('search_pdf'):
            file_types.append('pdf')
        if cleaned_data.get('search_doc'):
            file_types.append('doc')
        
        # Determine search type
        search_type = 'google'  # Default
        if cleaned_data.get('use_google_scholar'):
            search_type = 'scholar'
        
        search_config = {
            'domains': domains,
            'include_general_search': cleaned_data.get('include_general_search', False),
            'file_types': file_types,
            'search_type': search_type,
            'max_results': cleaned_data.get('max_results_per_query', 50)
        }
        
        cleaned_data['search_config'] = search_config
        
        # Validation: At least one PIC category must have terms
        if not any([population_terms, interest_terms, context_terms]):
            raise ValidationError("At least one PIC category (Population, Interest, or Context) must have terms.")
        
        # Validation: Must have at least one domain or general search
        if not domains and not cleaned_data.get('include_general_search'):
            raise ValidationError("You must specify at least one organization domain or enable general search.")
        
        # Validation: Must have at least one file type
        if not file_types:
            raise ValidationError("You must select at least one file type to search for.")
        
        return cleaned_data
    
    def _parse_terms(self, text: str) -> List[str]:
        """Parse terms from textarea input, removing empty lines and duplicates."""
        if not text:
            return []
        
        lines = text.strip().split('\n')
        terms = []
        for line in lines:
            term = line.strip()
            if term and term not in terms:  # Remove duplicates
                terms.append(term)
        
        return terms
    
    def save(self, commit=True):
        """Save the strategy with the processed data."""
        strategy = super().save(commit=False)
        
        # The cleaned data has already been processed in clean()
        # Just ensure the fields are set
        if hasattr(self, 'cleaned_data'):
            strategy.population_terms = self.cleaned_data.get('population_terms', [])
            strategy.interest_terms = self.cleaned_data.get('interest_terms', [])
            strategy.context_terms = self.cleaned_data.get('context_terms', [])
            strategy.search_config = self.cleaned_data.get('search_config', {})
        
        if commit:
            strategy.save()
        
        return strategy