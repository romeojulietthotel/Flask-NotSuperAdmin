
import wtforms

from flask import Flask
from flask_superadmin import Admin
from django.conf import settings
from flask_superadmin.model.backends.django.view import ModelAdmin
from django.db import models, DatabaseError
from examples.django.utils import install_models

settings.configure(
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': 'mydatabase.sqlite',
        }
    }
)

app = Flask(__name__)
app.config['SECRET_KEY'] = '123456790'
app.config['WTF_CSRF_ENABLED'] = False

admin = Admin(app)

class CustomModelView(ModelAdmin):
    def __init__(self, model, name=None, category=None, endpoint=None,
                 url=None, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

        super(CustomModelView, self).__init__(model, name, category, endpoint,
                                              url)

def test_list():
    class Person(models.Model):
        name = models.CharField(max_length=255)
        age = models.IntegerField()

        def __unicode__(self):
            return self.name

    # Create tables in the database if they don't exists
    try:
        install_models(Person)
    except DatabaseError as e:
        if 'already exists' not in e.message:
            raise

    Person.objects.all().delete()

    view = CustomModelView(Person)
    admin.add_view(view)

    assert view.model == Person
    assert view.name == 'Person'
    assert view.endpoint == 'person'
    assert view.url == '/admin/person'

    # Verify form
    with app.test_request_context():
        Form = view.get_form()
        assert isinstance(Form()._fields['name'], wtforms.StringField)
        assert isinstance(Form()._fields['age'], wtforms.IntegerField)

    # Make some test clients
    client = app.test_client()

    resp = client.get('/admin/person/')
    assert resp.status_code == 200

    resp = client.get('/admin/person/add/')
    assert resp.status_code == 200

    resp = client.post('/admin/person/add/',
                     data=dict(name='name', age='18'))
    assert resp.status_code == 302

    person = Person.objects.all()[0]
    assert person.name == 'name'
    assert person.age == 18

    resp = client.get('/admin/person/')
    assert resp.status_code == 200
    assert person.name in resp.data

    resp = client.get('/admin/person/%s/' % person.pk)
    assert resp.status_code == 200

    resp = client.post('/admin/person/%s/' % person.pk, data=dict(name='changed'))
    assert resp.status_code == 302

    person = Person.objects.all()[0]
    assert person.name == 'changed'
    assert person.age == 18

    resp = client.post('/admin/person/%s/delete/' % person.pk)
    assert resp.status_code == 200
    assert Person.objects.count() == 1

    resp = client.post('/admin/person/%s/delete/' % person.pk, data={'confirm_delete': True})
    assert resp.status_code == 302
    assert Person.objects.count() == 0

