from django import forms
from apps.tickets.models import Ticket
from apps.agents.models import Machine
from apps.companies.models import Company
from django.contrib.auth import get_user_model

User = get_user_model()

class MachineModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.hostname} ({obj.company.name})"

class UserModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        if obj.company:
            return f"{obj.email} ({obj.company.name})"
        return f"{obj.email} (Sem Empresa)"

class TicketManualForm(forms.ModelForm):
    company = forms.ModelChoiceField(
        queryset=Company.objects.filter(is_active=True).order_by('name'),
        required=False,
        label="Cliente / Empresa",
        widget=forms.Select(attrs={
            'class': 'form-select bg-dark text-white border-secondary border-opacity-50',
            'id': 'id_manual_ticket_company',
        })
    )
    
    machine = MachineModelChoiceField(
        queryset=Machine.objects.none(),
        required=False,
        label="Máquina",
        widget=forms.Select(attrs={
            'class': 'form-select bg-dark text-white border-secondary border-opacity-50',
        })
    )
    
    assigned_to = UserModelChoiceField(
        queryset=User.objects.none(),
        required=False,
        label="Colaborador / Técnico",
        widget=forms.Select(attrs={
            'class': 'form-select bg-dark text-white border-secondary border-opacity-50',
        })
    )

    class Meta:
        model = Ticket
        fields = ['title', 'description', 'priority', 'company', 'machine', 'assigned_to']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control bg-dark text-white border-secondary border-opacity-50',
                'placeholder': 'Ex: Lentidão na estação ou Erro ao iniciar serviço',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control bg-dark text-white border-secondary border-opacity-50',
                'placeholder': 'Descreva detalhadamente o incidente...',
                'rows': 4,
            }),
            'priority': forms.Select(attrs={
                'class': 'form-select bg-dark text-white border-secondary border-opacity-50',
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['machine'].required = False
        self.fields['machine'].empty_label = "Nenhuma máquina específica"
        self.fields['assigned_to'].empty_label = "Não designado"
        self.fields['company'].empty_label = "Selecione a empresa"

        if user:
            if user.role == 'superadmin':
                self.fields['company'].required = True
                self.fields['machine'].queryset = Machine.objects.all().select_related('company').order_by('hostname')
                self.fields['assigned_to'].queryset = User.objects.filter(is_active=True).select_related('company').exclude(role='viewer').order_by('email')
            else:
                self.fields['company'].widget = forms.HiddenInput()
                self.fields['company'].required = False
                self.fields['company'].initial = user.company
                self.fields['machine'].queryset = Machine.objects.filter(company=user.company).select_related('company').order_by('hostname')
                self.fields['assigned_to'].queryset = User.objects.filter(company=user.company, is_active=True).select_related('company').exclude(role='viewer').order_by('email')
        else:
            self.fields['machine'].queryset = Machine.objects.none()
            self.fields['assigned_to'].queryset = User.objects.none()
            self.fields['company'].widget = forms.HiddenInput()


