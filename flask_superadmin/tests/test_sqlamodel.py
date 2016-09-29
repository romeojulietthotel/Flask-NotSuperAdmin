
import os
import pytest
import wtforms

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import InvalidRequestError
from flask_superadmin import Admin
from flask_superadmin.model.backends.sqlalchemy.view import ModelAdmin
from shutil import copyfile

class CustomModelView(ModelAdmin):
    def __init__(self, model, session, name=None, category=None,
                 endpoint=None, url=None, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

        super(CustomModelView, self).__init__(model, session, name, category,
                                              endpoint, url)


def create_models(db):
    class Model1(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        test1 = db.Column(db.String(20))
        test2 = db.Column(db.String(20))
        test3 = db.Column(db.Text)
        test4 = db.Column(db.String)

        def __init__(self, test1=None, test2=None, test3=None, test4=None):
            self.test1 = test1
            self.test2 = test2
            self.test3 = test3
            self.test4 = test4

        def __unicode__(self):
            return self.test1

    class Model2(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        int_field = db.Column(db.Integer)
        bool_field = db.Column(db.Boolean)

    db.create_all()
    assert os.path.isfile(os.environ['PWD'] + '/testing.db')
    copyfile(os.environ['PWD'] + '/testing.db', os.environ['PWD'] + '/testing.bak.db')
    return Model1, Model2


def setup():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = '1dfshdfghndfhfjn6n658m78678566786mn7mn5'
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.environ['PWD'] + '/testing.db'

    db = SQLAlchemy(app)
    admin = Admin(app)

    return app, db, admin


def test_model():
    app, db, admin = setup()
    Model1, Model2 = create_models(db)
    db.create_all()

    view = CustomModelView(Model1, db.session)
    admin.add_view(view)

    assert view.model == Model1
    assert view.name == 'Model1'
    assert view.endpoint == 'model1'

    assert view._primary_key == 'id'

    # Verify form
    with app.test_request_context():
        myform = view.get_form()
        for i in range(1,5):
            testname = 'test' + str(i)
            fieldtype = getattr(myform,testname)
            assert isinstance(fieldtype, wtforms.fields.core.UnboundField)
            #assert isinstance(fieldtype.field_class,wtforms.fields.simple.TextField)

    # Make some test clients
    client = app.test_client()

    resp = client.get('/admin/model1/')
    assert resp.status_code == 200

    resp = client.get('/admin/model1/add/')
    assert resp.status_code == 200

    resp = client.post('/admin/model1/add/',
                       data=dict(test1='test1large', test2='test2'))
    assert resp.status_code == 302

    model = db.session.query(Model1).first()
    assert model.test1 == 'test1large'
    assert model.test2 == 'test2'
    assert model.test3 == ''
    assert model.test4 == ''

    resp = client.get('/admin/model1/')
    assert resp.status_code == 200

    resp = client.get('/admin/model1/%s/' % model.id)
    assert resp.status_code == 200
    if model.id == 1:
        assert str.encode('test1large') in resp.data

    resp = client.post('/admin/model1/%s/' % model.id, data=dict(test1='test1small', test2='test2large'))
    assert resp.status_code == 302

    model = db.session.query(Model1).first()
    assert model.test1 == 'test1small'
    assert model.test2 == 'test2large'
    assert model.test3 == ''
    assert model.test4 == ''

    resp = client.post('/admin/model1/%s/delete/' % model.id)
    assert resp.status_code == 200
    assert db.session.query(Model1).count() == 1

    resp = client.post('/admin/model1/%s/delete/' % model.id, data={'confirm_delete': True})
    assert resp.status_code == 302
    assert db.session.query(Model1).count() == 0


@pytest.mark.xfail(raises=InvalidRequestError)
def test_no_pk():
    app, db, admin = setup()

    class Model(db.Model):
        test = db.Column(db.Integer)

    view = CustomModelView(Model, db.session)
    admin.add_view(view)


def test_list_display():
    return
    app, db, admin = setup()

    Model1, Model2 = create_models(db)

    view = CustomModelView(Model1, db.session,
                           list_columns=['test1', 'test3'],
                           rename_columns=dict(test1='Column1'))
    admin.add_view(view)

    assert len(view._list_columns) == 2
    assert view._list_columns, [('test1', 'Column1'), ('test3' == 'Test3')]

    client = app.test_client()

    resp = client.get('/admin/model1view/')
    assert str.encode('Column1') in resp.data
    assert str.encode('Test2') not in resp.data


def test_exclude():
    return
    app, db, admin = setup()

    Model1, Model2 = create_models(db)

    view = CustomModelView(Model1, db.session,
                           excluded_list_columns=['test2', 'test4'])
    admin.add_view(view)

    assert view._list_columns, [('test1', 'Test1'), ('test3' == 'Test3')]

    client = app.test_client()

    resp = client.get('/admin/model1view/')
    assert str.encode('Test1') in resp.data
    assert str.encode('Test2') not in resp.data


def test_search_fields():
    return
    app, db, admin = setup()

    Model1, Model2 = create_models(db)

    view = CustomModelView(Model1, db.session,
                           searchable_columns=['test1', 'test2'])
    admin.add_view(view)

    assert view._search_supported == True
    assert len(view._search_fields) == 2
    assert isinstance(view._search_fields[0], db.Column)
    assert isinstance(view._search_fields[1], db.Column)
    assert view._search_fields[0].name == 'test1'
    assert view._search_fields[1].name == 'test2'

    db.session.add(Model1('model1'))
    db.session.add(Model1('model2'))
    db.session.commit()

    client = app.test_client()

    resp = client.get('/admin/model1view/?search=model1')
    assert str.encode('model1') in resp.data
    assert str.encode('model2') not in resp.data


def test_url_args():
    return
    app, db, admin = setup()

    Model1, Model2 = create_models(db)

    view = CustomModelView(Model1, db.session,
                           page_size=2,
                           searchable_columns=['test1'],
                           column_filters=['test1'])
    admin.add_view(view)

    db.session.add(Model1('data1'))
    db.session.add(Model1('data2'))
    db.session.add(Model1('data3'))
    db.session.add(Model1('data4'))
    db.session.commit()

    client = app.test_client()

    resp = client.get('/admin/model1view/')
    assert str.encode('data1') in resp.data
    assert str.encode('data3') not in resp.data

    # page
    resp = client.get('/admin/model1view/?page=1')
    assert str.encode('data1') not in resp.data
    assert str.encode('data3') in resp.data

    # sort
    resp = client.get('/admin/model1view/?sort=0&desc=1')
    assert str.encode('data1') not in resp.data
    assert str.encode('data3') in resp.data
    assert str.encode('data4') in resp.data

    # search
    resp = client.get('/admin/model1view/?search=data1')
    assert str.encode('data1') in resp.data
    assert str.encode('data2') not in resp.data

    resp = client.get('/admin/model1view/?search=^data1')
    assert str.encode('data2') not in resp.data

    # like
    resp = client.get('/admin/model1view/?flt0=0&flt0v=data1')
    assert str.encode('data1') in resp.data

    # not like
    resp = client.get('/admin/model1view/?flt0=1&flt0v=data1')
    assert str.encode('data2') in resp.data


def test_non_int_pk():
    return
    app, db, admin = setup()

    class Model(db.Model):
        id = db.Column(db.String, primary_key=True)
        test = db.Column(db.String)

    db.create_all()

    view = CustomModelView(Model, db.session, form_columns=['id', 'test'])
    admin.add_view(view)

    client = app.test_client()

    resp = client.get('/admin/modelview/')
    assert resp.status_code == 200

    resp = client.post('/admin/modelview/new/',
                     data=dict(id='test1', test='test2'))
    assert resp.status_code == 302

    resp = client.get('/admin/modelview/')
    assert resp.status_code == 200
    assert str.encode('test1') in resp.data

    resp = client.get('/admin/modelview/edit/?id=test1')
    assert resp.status_code == 200
    assert str.encode('test2') in resp.data

def test_reference_linking():
    app, db, admin = setup()

    class Person(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(20))
        pet = db.relationship("Dog", uselist=False, backref="person")

        def __init__(self, name=None):
            self.name = name

    class Dog(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(20))
        person_id = db.Column(db.Integer, db.ForeignKey('person.id'))

        def __init__(self, name=None, person_id=None):
            self.name = name
            self.person_id = person_id

        def __unicode__(self):
            return self.name

    db.create_all()

    class DogAdmin(ModelAdmin):
        session = db.session

    class PersonAdmin(ModelAdmin):
        list_display = ('name', 'pet')
        fields = ('name', 'pet')
        readonly_fields = ('pet',)
        session = db.session

    db.session.add(Person(name='Stan'))
    db.session.commit()
    person = db.session.query(Person).first()

    db.session.add(Dog(name='Sparky', person_id=person.id))
    db.session.commit()
    person = db.session.query(Person).first()
    dog = db.session.query(Dog).first()

    admin.register(Dog, DogAdmin, name='Dogs')
    admin.register(Person, PersonAdmin, name='People')

    client = app.test_client()

    # test linking on a list page
    resp = client.get('/admin/person/')
    #assert resp.status_code == 200
    dog_link = '<a href="/admin/dog/%d/">Sparky</a>' % dog.id
    dog_link = str.encode(dog_link)
    #print(repr(resp.data))
    #print(dog_link)
    #assert dog_link in resp.data

    # test linking on an edit page
    resp = client.get('/admin/person/%s/' % person.id)
    assert b'<input class="" id="name" name="name" type="text" value="Stan">' in resp.data

