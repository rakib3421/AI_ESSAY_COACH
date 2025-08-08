from django import forms
from .models import EssayAnalysis


class EssayUploadForm(forms.Form):
    """Form for uploading essay files"""
    
    essay_file = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.docx,.txt'
        }),
        help_text='Upload a Word document (.docx) or text file (.txt)'
    )
    essay_type = forms.ChoiceField(
        choices=EssayAnalysis.ESSAY_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Select the type of essay you are submitting'
    )
    title = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter a descriptive title for your essay'
        }),
        help_text='Provide a clear, descriptive title for your essay'
    )
    coaching_level = forms.ChoiceField(
        choices=[
            ('light', 'Light - Basic feedback'),
            ('medium', 'Medium - Balanced feedback'),
            ('intensive', 'Intensive - Detailed feedback'),
        ],
        initial='medium',
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Choose how detailed you want the feedback to be'
    )
    suggestion_level = forms.ChoiceField(
        choices=[
            ('low', 'Low - Conservative suggestions'),
            ('medium', 'Medium - Balanced suggestions'),
            ('high', 'High - Comprehensive suggestions'),
        ],
        initial='medium',
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Choose how many suggestions you want to receive'
    )


class EssayTextForm(forms.Form):
    """Form for pasting essay text directly"""
    
    essay_text = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 15,
            'placeholder': 'Paste your essay text here...'
        }),
        help_text='Paste your essay text directly into this field'
    )
    essay_type = forms.ChoiceField(
        choices=EssayAnalysis.ESSAY_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Select the type of essay you are submitting'
    )
    title = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter essay title'
        }),
        help_text='Provide a clear, descriptive title for your essay'
    )
    coaching_level = forms.ChoiceField(
        choices=[
            ('light', 'Light - Basic feedback'),
            ('medium', 'Medium - Balanced feedback'),
            ('intensive', 'Intensive - Detailed feedback'),
        ],
        initial='medium',
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Choose how detailed you want the feedback to be'
    )
    suggestion_level = forms.ChoiceField(
        choices=[
            ('low', 'Low - Conservative suggestions'),
            ('medium', 'Medium - Balanced suggestions'),
            ('high', 'High - Comprehensive suggestions'),
        ],
        initial='medium',
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Choose how many suggestions you want to receive'
    )


class FeedbackForm(forms.ModelForm):
    """Form for teacher feedback"""
    
    class Meta:
        model = EssayAnalysis
        fields = []
    
    feedback_text = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 8,
            'placeholder': 'Provide detailed feedback...'
        }),
        label='Teacher Feedback'
    )
    additional_score = forms.FloatField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 0,
            'max': 100,
            'step': 0.1
        }),
        label='Additional Score (Optional)',
        help_text='Provide an additional score if needed (0-100)'
    )
