from django import forms
from django.utils import timezone
from .models import Assignment, AssignmentSubmission


class AssignmentForm(forms.ModelForm):
    """Form for creating and editing assignments"""
    
    class Meta:
        model = Assignment
        fields = ['title', 'description', 'essay_type', 'due_date', 'max_score', 'instructions']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter assignment title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 4,
                'placeholder': 'Provide detailed instructions for the assignment'
            }),
            'essay_type': forms.Select(attrs={'class': 'form-select'}),
            'due_date': forms.DateTimeInput(attrs={
                'class': 'form-control', 
                'type': 'datetime-local'
            }),
            'max_score': forms.NumberInput(attrs={
                'class': 'form-control', 
                'min': 0, 
                'max': 100,
                'value': 100
            }),
            'instructions': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 6,
                'placeholder': 'Detailed instructions, rubric details, formatting requirements, etc.'
            }),
        }
    
    def clean_due_date(self):
        due_date = self.cleaned_data['due_date']
        if due_date <= timezone.now():
            raise forms.ValidationError("Due date must be in the future.")
        return due_date


class AssignmentSubmissionForm(forms.Form):
    """Form for submitting assignments"""
    
    submission_method = forms.ChoiceField(
        choices=[
            ('upload', 'Upload File'),
            ('paste', 'Paste Text'),
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='paste'
    )
    
    essay_file = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.docx,.txt'
        }),
        help_text='Upload a Word document (.docx) or text file (.txt)'
    )
    
    essay_text = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 15,
            'placeholder': 'Paste your essay text here...'
        }),
        help_text='Paste your essay text directly into this field'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        submission_method = cleaned_data.get('submission_method')
        essay_file = cleaned_data.get('essay_file')
        essay_text = cleaned_data.get('essay_text')
        
        if submission_method == 'upload' and not essay_file:
            raise forms.ValidationError("Please upload a file.")
        
        if submission_method == 'paste' and not essay_text:
            raise forms.ValidationError("Please paste your essay text.")
        
        return cleaned_data


class GradingForm(forms.ModelForm):
    """Form for teacher grading"""
    
    class Meta:
        model = AssignmentSubmission
        fields = ['teacher_score', 'teacher_feedback']
        widgets = {
            'teacher_score': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 100,
                'step': 0.1
            }),
            'teacher_feedback': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 8,
                'placeholder': 'Provide detailed feedback...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        assignment = kwargs.pop('assignment', None)
        super().__init__(*args, **kwargs)
        
        if assignment:
            self.fields['teacher_score'].widget.attrs['max'] = assignment.max_score
