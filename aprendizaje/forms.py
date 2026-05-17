from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Estudiante, PerfilProfesional

class RegistroRedOwlForm(UserCreationForm):
    TIPO_CHOICES = (
        ('estudiante', 'Operador (Estudiante)'),
        ('reclutador', 'Contratista (Reclutador)'),
    )
    
    tipo_usuario = forms.ChoiceField(
        choices=TIPO_CHOICES, 
        widget=forms.RadioSelect, 
        initial='estudiante',
        label="Tipo de Cuenta"
    )
    
    escuela = forms.CharField(
        max_length=200, 
        required=False, 
        label="Institución / Escuela (Opcional)"
    )

    empresa = forms.CharField(
        max_length=200, 
        required=False, 
        label="Nombre de tu Empresa"
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields

class EditarEstudianteForm(forms.ModelForm):
    class Meta:
        model = Estudiante
        fields = ['escuela', 'avatar']
        widgets = {
            'escuela': forms.TextInput(attrs={'class': 'form-input'}),
            'avatar': forms.ClearableFileInput(attrs={'class': 'form-file-input'}),
        }

class EditarPerfilProfesionalForm(forms.ModelForm):
    class Meta:
        model = PerfilProfesional
        fields = ['biografia', 'url_github', 'url_linkedin', 'disponible']
        widgets = {
            'biografia': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 4}),
            'url_github': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://github.com/...'}),
            'url_linkedin': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://linkedin.com/in/...'}),
            'disponible': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }