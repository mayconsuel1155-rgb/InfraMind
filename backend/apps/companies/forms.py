from django import forms

from apps.accounts.models import User
from apps.companies.models import Company


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = [
            'name', 'logo', 'cnpj', 'trade_name', 'phone', 'email',
            'address_zip_code', 'address_street', 'address_number',
            'address_complement', 'address_neighborhood', 'address_city',
            'address_state', 'parent_company', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control glass-input',
                'placeholder': 'Razão Social',
            }),
            'logo': forms.FileInput(attrs={
                'class': 'form-control glass-input',
                'accept': 'image/*',
            }),
            'cnpj': forms.TextInput(attrs={
                'class': 'form-control glass-input',
                'placeholder': '00.000.000/0000-00',
                'id': 'company_cnpj',
            }),
            'trade_name': forms.TextInput(attrs={
                'class': 'form-control glass-input',
                'placeholder': 'Nome Fantasia',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control glass-input',
                'placeholder': 'Telefone de contato',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control glass-input',
                'placeholder': 'contato@empresa.com',
            }),
            'address_zip_code': forms.TextInput(attrs={
                'class': 'form-control glass-input',
                'placeholder': '00000-000',
            }),
            'address_street': forms.TextInput(attrs={
                'class': 'form-control glass-input',
                'placeholder': 'Logradouro',
            }),
            'address_number': forms.TextInput(attrs={
                'class': 'form-control glass-input',
                'placeholder': 'Número',
            }),
            'address_complement': forms.TextInput(attrs={
                'class': 'form-control glass-input',
                'placeholder': 'Complemento',
            }),
            'address_neighborhood': forms.TextInput(attrs={
                'class': 'form-control glass-input',
                'placeholder': 'Bairro',
            }),
            'address_city': forms.TextInput(attrs={
                'class': 'form-control glass-input',
                'placeholder': 'Cidade',
            }),
            'address_state': forms.TextInput(attrs={
                'class': 'form-control glass-input',
                'placeholder': 'UF',
                'maxlength': '2',
            }),
            'parent_company': forms.Select(attrs={
                'class': 'form-select glass-input',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'role': 'switch',
            }),
        }

    def __init__(self, *args, current_user=None, **kwargs):
        self.current_user = current_user
        super().__init__(*args, **kwargs)
        
        # Determine allowed parent companies
        queryset = Company.objects_all.all()
        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
            
        if current_user and current_user.role != 'superadmin':
            # An admin of a company can only link a new branch to their own company
            self.fields['parent_company'].queryset = Company.objects_all.filter(pk=current_user.company_id)
            self.fields['parent_company'].initial = current_user.company_id
            self.fields['parent_company'].widget = forms.HiddenInput()
            self.fields['parent_company'].required = False
        else:
            # Superadmin can link to any company or none (making it a matrix)
            self.fields['parent_company'].queryset = queryset.order_by('name')
            self.fields['parent_company'].required = False
            self.fields['parent_company'].label = "Matriz (Caso esta seja uma filial)"

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.current_user and self.current_user.role != 'superadmin':
            # Force the parent company to be the admin's company
            instance.parent_company_id = self.current_user.company_id
        if commit:
            instance.save()
            self.save_m2m()
        return instance



class UserForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-control glass-input',
        'placeholder': 'usuario@empresa.com',
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control glass-input',
        'placeholder': 'Senha temporaria ou definitiva',
    }))
    role = forms.ChoiceField(widget=forms.Select(attrs={
        'class': 'form-select glass-input',
    }))
    company = forms.ModelChoiceField(
        queryset=Company.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select glass-input'}),
    )
    is_active = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'role': 'switch',
        }),
    )

    def __init__(self, *args, current_user=None, **kwargs):
        self.current_user = current_user
        super().__init__(*args, **kwargs)

        if current_user and current_user.role == 'superadmin':
            self.fields['role'].choices = User.ROLE_CHOICES
            self.fields['company'].queryset = Company.objects.filter(is_active=True).order_by('name')
            self.fields['company'].required = False
            self.fields['company'].help_text = 'Opcional para superadmin.'
        else:
            self.fields['role'].choices = [
                choice for choice in User.ROLE_CHOICES
                if choice[0] in ('admin', 'technician', 'viewer')
            ]
            self.fields['company'].queryset = Company.objects.filter(pk=getattr(current_user, 'company_id', None))
            self.fields['company'].required = False
            self.fields['company'].widget = forms.HiddenInput()
            self.fields['company'].initial = getattr(current_user, 'company_id', None)

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        company = cleaned_data.get('company')

        if self.current_user and self.current_user.role != 'superadmin':
            if not getattr(self.current_user, 'company_id', None):
                raise forms.ValidationError('Sua conta precisa estar vinculada a uma empresa para criar usuarios.')
            cleaned_data['company'] = self.current_user.company
        elif role != 'superadmin' and not company:
            raise forms.ValidationError('Selecione uma empresa para este usuario.')

        return cleaned_data

    def save(self):
        cleaned_data = self.cleaned_data
        user = User(
            email=cleaned_data['email'],
            company=cleaned_data.get('company') if cleaned_data.get('role') != 'superadmin' else None,
            role=cleaned_data['role'],
            is_active=cleaned_data.get('is_active', True),
            is_staff=cleaned_data['role'] == 'superadmin',
        )
        user.set_password(cleaned_data['password'])
        user.save()
        return user
