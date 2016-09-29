
import wtforms

from flask import Flask
from mongoengine import *
from flask_superadmin import Admin
from flask_superadmin.model.backends.mongoengine.view import ModelAdmin


class CustomModelView(ModelAdmin):
    def __init__(self, model, name=None, category=None, endpoint=None,
                 url=None, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

        super(CustomModelView, self).__init__(model, name, category, endpoint,
                                              url)


def setup():
    connect('superadmin_test')
    app = Flask(__name__)
    app.config['SECRET_KEY'] = '1'
    app.config['WTF_CSRF_ENABLED'] = False

    admin = Admin(app)

    return app, admin


def test_model():
    app, admin = setup()

    class Person(Document):
        name = StringField()
        age = IntField()

    Person.drop_collection()

    view = CustomModelView(Person)
    admin.add_view(view)

    assert view.model == Person
    assert view.name == 'Person'
    assert view.endpoint == 'person'
    assert view.url == '/admin/person'

    # Verify form
    with app.test_request_context():
        Form = view.get_form()
        assert isinstance(Form()._fields['name'], wtforms.TextAreaField)
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

    person = Person.objects.first()
    assert person.name == 'name'
    assert person.age == 18

    resp = client.get('/admin/person/')
    assert resp.status_code == 200
    assert str(person.pk) in resp.data

    resp = client.get('/admin/person/%s/' % person.pk)
    assert resp.status_code == 200

    resp = client.post('/admin/person/%s/' % person.pk, data=dict(name='changed'))
    assert resp.status_code == 302

    person = Person.objects.first()
    assert person.name == 'changed'
    assert person.age == 18

    resp = client.post('/admin/person/%s/delete/' % person.pk)
    assert resp.status_code == 200
    assert Person.objects.count() == 1

    resp = client.post('/admin/person/%s/delete/' % person.pk, data={'confirm_delete': True})
    assert resp.status_code == 302
    assert Person.objects.count() == 0


def test_list_display():
    app, admin = setup()

    class Person(Document):
        name = StringField()
        age = IntField()

    Person.drop_collection()

    view = CustomModelView(Person, list_display=('name', 'age'))
    admin.add_view(view)

    assert len(view.list_display) == 2

    client = app.test_client()

    resp = client.get('/admin/person/')
    assert 'Name' in resp.data
    assert 'Age' in resp.data

    resp = client.post('/admin/person/add/',
                     data=dict(name='Steve', age='18'))
    assert resp.status_code == 302

    resp = client.get('/admin/person/')
    assert 'Steve' in resp.data
    assert '18' in resp.data


def test_exclude():
    app, admin = setup()

    class Person(Document):
        name = StringField()
        age = IntField()

    Person.drop_collection()

    view = CustomModelView(Person, exclude=['name'])
    admin.add_view(view)

    # Verify form
    with app.test_request_context():
        Form = view.get_form()
        assert list(Form()._fields.keys()), ['csrf_token' == 'age']

def test_fields():
    app, admin = setup()

    class Person(Document):
        name = StringField()
        age = IntField()

    Person.drop_collection()

    view = CustomModelView(Person, fields=['name'])
    admin.add_view(view)

    # Verify form
    with app.test_request_context():
        Form = view.get_form()
        assert list(Form()._fields.keys()), ['csrf_token' == 'name']

def test_fields_and_exclude():
    app, admin = setup()

    class Person(Document):
        name = StringField()
        age = IntField()

    Person.drop_collection()

    view = CustomModelView(Person, fields=['name', 'age'], exclude=['name'])
    admin.add_view(view)

    # Verify form
    with app.test_request_context():
        Form = view.get_form()
        assert list(Form()._fields.keys()), ['csrf_token' == 'age']

def test_search_fields():
    app, admin = setup()

    class Person(Document):
        name = StringField()
        age = IntField()

    Person.drop_collection()
    Person.objects.create(name='John', age=18)
    Person.objects.create(name='Michael', age=21)

    view = CustomModelView(Person, list_display=['name'],
                           search_fields=['name'])
    admin.add_view(view)

    assert len(view.search_fields) == 1
    client = app.test_client()

    resp = client.get('/admin/person/')
    assert 'name="q" class="search-input"' in resp.data
    assert 'John' in resp.data
    assert 'Michael' in resp.data

    resp = client.get('/admin/person/?q=john')
    assert 'John' in resp.data
    assert 'Michael' not in resp.data


def test_pagination():
    app, admin = setup()

    class Person(Document):
        name = StringField()
        age = IntField()

    Person.drop_collection()
    Person.objects.create(name='John', age=18)
    Person.objects.create(name='Michael', age=21)
    Person.objects.create(name='Steve', age=15)
    Person.objects.create(name='Ron', age=59)

    view = CustomModelView(Person, list_per_page=2,
                           list_display=['name', 'age'])
    admin.add_view(view)

    client = app.test_client()

    resp = client.get('/admin/person/')
    assert '<div class="total-count">Total count: 4</div>' in resp.data
    # make sure the first page is active (i.e. has no url
    assert str.encode('<a href="#">1</a>') in resp.data
    assert 'John' in resp.data
    assert 'Michael' in resp.data
    assert 'Steve' not in resp.data
    assert 'Ron' not in resp.data

    # default page == page 0
    assert resp.data == client.get('/admin/person/?page=0').data

    resp = client.get('/admin/person/?page=1')
    assert 'John' not in resp.data
    assert 'Michael' not in resp.data
    assert 'Steve' in resp.data
    assert 'Ron' in resp.data

def test_sort():
    app, admin = setup()

    class Person(Document):
        name = StringField()
        age = IntField()

    Person.drop_collection()
    Person.objects.create(name='John', age=18)
    Person.objects.create(name='Michael', age=21)
    Person.objects.create(name='Steve', age=15)
    Person.objects.create(name='Ron', age=59)

    view = CustomModelView(Person, list_per_page=2,
                           list_display=['name', 'age'])
    admin.add_view(view)

    client = app.test_client()

    resp = client.get('/admin/person/?sort=name')
    assert 'John' in resp.data
    assert 'Michael' in resp.data
    assert 'Ron' not in resp.data
    assert 'Steve' not in resp.data

    resp = client.get('/admin/person/?sort=-name')
    assert 'John' not in resp.data
    assert 'Michael' not in resp.data
    assert 'Ron' in resp.data
    assert 'Steve' in resp.data

    resp = client.get('/admin/person/?sort=age')
    assert 'John' in resp.data
    assert 'Michael' not in resp.data
    assert 'Ron' not in resp.data
    assert 'Steve' in resp.data

    resp = client.get('/admin/person/?sort=-age')
    assert 'John' not in resp.data
    assert 'Michael' in resp.data
    assert 'Ron' in resp.data
    assert 'Steve' not in resp.data

def test_reference_linking():
    app, admin = setup()

    class Dog(Document):
        name = StringField()

        def __unicode__(self):
            return self.name

    class Person(Document):
        name = StringField()
        age = IntField()
        pet = ReferenceField(Dog)

    class DogAdmin(ModelAdmin):
        pass

    class PersonAdmin(ModelAdmin):
        list_display = ('name', 'age', 'pet')
        fields = ('name', 'age', 'pet')
        readonly_fields = ('pet',)

    Dog.drop_collection()
    Person.drop_collection()
    dog = Dog.objects.create(name='Sparky')
    person = Person.objects.create(name='Stan', age=10, pet=dog)

    admin.register(Dog, DogAdmin, name='Dogs')
    admin.register(Person, PersonAdmin, name='People')

    client = app.test_client()

    # test linking on a list page
    resp = client.get('/admin/person/')
    dog_link = '<a href="/admin/dog/%s/">Sparky</a>' % dog.pk
    assert dog_link in resp.data

    # test linking on an edit page
    resp = client.get('/admin/person/%s/' % person.pk)
    assert '<textarea class="" id="name" name="name">Stan</textarea>' in resp.data
    assert '<input class="" id="age" name="age" type="text" value="10">' in resp.data
    assert dog_link in resp.data

def test_no_csrf_in_form():
    app, admin = setup()

    class Person(Document):
        name = StringField()
        age = IntField()

    Person.drop_collection()
    person = Person.objects.create(name='Eric', age=10)

    client = app.test_client()

    view = CustomModelView(Person)
    admin.add_view(view)

    resp = client.get('/admin/person/%s/' % person.pk)
    assert '<textarea class="" id="name" name="name">Eric</textarea>' in resp.data
    assert '<input class="" id="age" name="age" type="text" value="10">' in resp.data
    assert '<label for="csrf_token">Csrf Token</label>' not in resp.data

def test_requred_int_field():
    app, admin = setup()

    class Person(Document):
        name = StringField()
        age = IntField(required=True)

    Person.drop_collection()

    view = CustomModelView(Person)
    admin.add_view(view)

    client = app.test_client()

    resp = client.post('/admin/person/add/', data=dict(name='name', age='0'))
    assert resp.status_code == 302
    assert 'This field is required.' not in resp.data
    assert 'error.' not in resp.data

