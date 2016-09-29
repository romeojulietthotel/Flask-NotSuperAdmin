import pytest

from flask import Flask
from flask_superadmin import base


class MockView(base.BaseView):
    # Various properties
    allow_call = True
    allow_access = True

    @base.expose('/')
    def index(self):
        return 'Success!'

    @base.expose('/test/')
    def test(self):
        return self.render('mock.html')

    def _handle_view(self, name, **kwargs):
        if self.allow_call:
            return super(MockView, self)._handle_view(name, **kwargs)
        else:
            return b'Failure!'

    def is_accessible(self):
        if self.allow_access:
            return super(MockView, self).is_accessible()
        else:
            return False


def test_baseview_defaults():
    view = MockView()
    assert view.name == None
    assert view.category == None
    assert view.endpoint == None
    assert view.url == None
    assert view.static_folder == None
    assert view.admin == None
    assert view.blueprint == None


def test_base_defaults():
    admin = base.Admin()
    assert admin.name == 'Admin'
    assert admin.url == '/admin'
    assert admin.app == None
    assert admin.index_view is not None

    # Check if default view was added
    assert len(admin._views) == 1
    assert admin._views[0] == admin.index_view


def test_base_registration():
    app = Flask(__name__)
    admin = base.Admin(app)

    assert admin.app == app
    assert admin.index_view.blueprint is not None


def test_admin_customizations():
    app = Flask(__name__)
    admin = base.Admin(app, name='Test', url='/foobar')
    assert admin.name == 'Test'
    assert admin.url == '/foobar'

    client = app.test_client()
    rv = client.get('/foobar/')
    assert rv.status_code == 200


def test_baseview_registration():
    admin = base.Admin()

    view = MockView()
    bp = view.create_blueprint(admin)

    # Base properties
    assert view.admin == admin
    assert view.blueprint is not None

    # Calculated properties
    assert view.endpoint == 'mockview'
    assert view.url == '/admin/mockview'
    assert view.name == 'Mock View'

    # Verify generated blueprint properties
    assert bp.name == view.endpoint
    assert bp.url_prefix == view.url
    assert bp.template_folder == 'templates'
    assert bp.static_folder == view.static_folder

    # Verify customizations
    view = MockView(name='Test', endpoint='foobar')
    view.create_blueprint(base.Admin())

    assert view.name == 'Test'
    assert view.endpoint == 'foobar'
    assert view.url == '/admin/foobar'

    view = MockView(url='test')
    view.create_blueprint(base.Admin())
    assert view.url == '/admin/test'

    view = MockView(url='/test/test')
    view.create_blueprint(base.Admin())
    assert view.url == '/test/test'


def test_baseview_urls():
    app = Flask(__name__)
    admin = base.Admin(app)

    view = MockView()
    admin.add_view(view)

    assert len(view._urls) == 2


@pytest.mark.xfail(raises=Exception)
def test_no_default():
    app = Flask(__name__)
    admin = base.Admin(app)
    admin.add_view(base.BaseView())


def test_call():
    app = Flask(__name__)
    admin = base.Admin(app)
    view = MockView()
    admin.add_view(view)
    client = app.test_client()

    rv = client.get('/admin/')
    assert rv.status_code == 200

    rv = client.get('/admin/mockview/')
    assert rv.data == str.encode('Success!')

    rv = client.get('/admin/mockview/test/')
    assert rv.data == str.encode('Success!')

    # Check authentication failure
    view.allow_call = False
    rv = client.get('/admin/mockview/')
    assert rv.data == b'Failure!'


def test_permissions():
    app = Flask(__name__)
    admin = base.Admin(app)
    view = MockView()
    admin.add_view(view)
    client = app.test_client()

    view.allow_access = False

    rv = client.get('/admin/mockview/')
    assert rv.status_code == 403


def test_submenu():
    app = Flask(__name__)
    admin = base.Admin(app)
    admin.add_view(MockView(name='Test 1', category='Test', endpoint='test1'))

    # Second view is not normally accessible
    view = MockView(name='Test 2', category='Test', endpoint='test2')
    view.allow_access = False
    admin.add_view(view)

    assert 'Test' in admin._menu_categories
    assert len(admin._menu) == 2
    assert admin._menu[1].name == 'Test'
    assert len(admin._menu[1]._children) == 2

    # Categories don't have URLs and they're not accessible
    assert admin._menu[1].get_url() == None
    assert admin._menu[1].is_accessible() == False

    assert len(admin._menu[1].get_children()) == 1


def test_delayed_init():
    app = Flask(__name__)
    admin = base.Admin()
    admin.add_view(MockView())
    admin.init_app(app)

    client = app.test_client()

    rv = client.get('/admin/mockview/')
    assert rv.data == str.encode('Success!')


@pytest.mark.xfail(raises=Exception)
def test_double_init():
    app = Flask(__name__)
    admin = base.Admin(app)
    admin.init_app(app)

