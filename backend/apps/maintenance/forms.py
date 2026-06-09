from django import forms
from django.forms import inlineformset_factory
from apps.maintenance.models import MaintenanceReport, MaintenanceItem
from apps.agents.models import Machine

class MaintenanceReportForm(forms.ModelForm):
    class Meta:
        model = MaintenanceReport
        fields = [
            'machine', 'ticket', 'type', 'status', 'title', 
            'description', 'work_done', 'scheduled_at', 
            'started_at', 'completed_at', 'cost', 'warranty_days'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'work_done': forms.Textarea(attrs={'rows': 4}),
            'scheduled_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'started_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'completed_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # Filtra as máquinas pela empresa atual se o usuário não for superadmin
        if self.request and self.request.user.role != 'superadmin':
            self.fields['machine'].queryset = Machine.objects.filter(company=self.request.user.company)
            
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control bg-dark border-secondary text-light'})
            
        # Select fields
        self.fields['type'].widget.attrs.update({'class': 'form-select bg-dark border-secondary text-light'})
        self.fields['status'].widget.attrs.update({'class': 'form-select bg-dark border-secondary text-light'})
        self.fields['machine'].widget.attrs.update({'class': 'form-select bg-dark border-secondary text-light'})
        if 'ticket' in self.fields:
             self.fields['ticket'].widget.attrs.update({'class': 'form-select bg-dark border-secondary text-light'})

class MaintenanceItemForm(forms.ModelForm):
    class Meta:
        model = MaintenanceItem
        fields = ['description', 'quantity', 'unit_cost']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control bg-dark border-secondary text-light form-control-sm'})

MaintenanceItemFormSet = inlineformset_factory(
    MaintenanceReport, MaintenanceItem, form=MaintenanceItemForm,
    extra=1, can_delete=True
)
