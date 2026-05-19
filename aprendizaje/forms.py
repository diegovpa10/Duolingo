from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
# Añadimos OfertaLaboral a la importación:
from .models import Estudiante, PerfilProfesional, OfertaLaboral

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
    # 1. Forzamos a que el campo en pantalla sea un input de texto normal
    habilidades = forms.CharField(
        required=False,
        label="Tus Habilidades (separadas por comas)",
        widget=forms.TextInput(attrs={
            'class': 'form-input', 
            'placeholder': 'Ej: Python, Django, SQL, Inglés B2'
        })
    )

    class Meta:
        model = PerfilProfesional
        # 2. Asegúrate de agregar 'habilidades' aquí a los fields
        fields = ['biografia', 'url_github', 'url_linkedin', 'disponible', 'habilidades']
        widgets = {
            'biografia': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 4}),
            'url_github': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://github.com/...'}),
            'url_linkedin': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://linkedin.com/in/...'}),
            'disponible': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }

    # 3. AL CARGAR: Si el estudiante ya tiene habilidades (lista), las convertimos a texto
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.habilidades:
            # Transforma ["Python", "SQL"] en "Python, SQL"
            self.initial['habilidades'] = ", ".join(self.instance.habilidades)

    # 4. AL GUARDAR: Toma el texto que escribió el estudiante y lo convierte a lista (JSON)
    def clean_habilidades(self):
        data = self.cleaned_data.get('habilidades', '')
        if data:
            # Corta por las comas, quita espacios extra y crea la lista
            return [hab.strip() for hab in data.split(',') if hab.strip()]
        return [] # Si lo deja en blanco, guarda una lista vacía

# --- NUEVO FORMULARIO PARA OFERTAS LABORALES ---
class OfertaLaboralForm(forms.ModelForm):
    class Meta:
        model = OfertaLaboral
        fields = ['titulo', 'descripcion', 'requisitos', 'rango_salarial']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ej: Desarrollador Backend Junior'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 4, 'placeholder': 'Describe las responsabilidades de la misión...'}),
            'requisitos': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'placeholder': 'Ej: Python, Django, SQL...'}),
            'rango_salarial': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ej: $500 - $1000 USD'}),
        }