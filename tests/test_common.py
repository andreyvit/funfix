    
from sampledb import Account
from support import with_empty_db, SampleDbFixture as Fixture


class BasicAccounts(Fixture):
  Entity = Account
  
  class first:
    x = 42
    y = x / 2
  
  class second:
    x = 11
    y = 99

class AdvancedAccounts(BasicAccounts):
  
  class third:
    x = 2
    y = 4

# can also pass Entity as a subclass
class DependentAccounts(Fixture, Account):
  
  class fourth:
    x = BasicAccounts.first
    y = lambda: BasicAccounts.second.key

class DerivedAccounts(Fixture):
  Entity = Account
  
  class base:
    x = 70
    y = 77
  
  class fifth(base):
    y = 81
    
    
@with_empty_db
def test_undecorated_method_can_access_data():
  assert 42 == BasicAccounts.first.x
  assert 21 == BasicAccounts.first.y
  assert 11 == BasicAccounts.second.x
  assert 99 == BasicAccounts.second.y
  
@with_empty_db
def test_undecorated_method_cannot_access_model():
  try:
    dummy = BasicAccounts.first.model_only_prop
    assert False
  except AttributeError: pass

@with_empty_db
def test_fixture_is_decorator():
  @BasicAccounts
  def some_method():
    pass
  some_method()

@with_empty_db
@BasicAccounts
def test_fixture_decorated_method_can_access_data():
  assert 42 == BasicAccounts.first.x
  assert 21 == BasicAccounts.first.y
  assert 11 == BasicAccounts.second.x
  assert 99 == BasicAccounts.second.y

@with_empty_db
@BasicAccounts
def test_fixture_decorated_method_can_access_model():
  assert 555 == BasicAccounts.first.model_only_prop
  assert 555 == BasicAccounts.second.model_only_prop

@with_empty_db
def test_fixture_decorated_method_loads_models():
  assert [] == Account.find_by_x(BasicAccounts.first.x)
  @BasicAccounts
  def some_method():
    assert [BasicAccounts.first] == Account.find_by_x(BasicAccounts.first.x), "Wrong number of account loaded with x=%d: len=%d" % (BasicAccounts.first.x, len(Account.find_by_x(BasicAccounts.first.x)))
  some_method()
  assert [] == Account.find_by_x(BasicAccounts.first.x)

@with_empty_db
def test_fixture_decorated_method_unloads_models():
  @BasicAccounts
  def some_method(): pass
  some_method()
  assert [] == Account.find_by_x(BasicAccounts.first.x)

@with_empty_db
def test_fixture_derivation_combines_items():
  assert 2 == AdvancedAccounts.third.x
  assert 4 == AdvancedAccounts.third.y
  assert 42 == AdvancedAccounts.first.x
  assert 21 == AdvancedAccounts.first.y
  assert 11 == AdvancedAccounts.second.x
  assert 99 == AdvancedAccounts.second.y

@with_empty_db
@AdvancedAccounts
def test_fixture_derivation_combines_item_loading():
  assert isinstance(AdvancedAccounts.third, Account)
  assert isinstance(AdvancedAccounts.first, Account)
  assert isinstance(AdvancedAccounts.second, Account)

@with_empty_db
@AdvancedAccounts
def test_fixture_derivation_loads_parent_fixture_items():
  assert isinstance(BasicAccounts.first, Account)
  assert isinstance(BasicAccounts.second, Account)

@with_empty_db
@DependentAccounts
def test_dependent_fixture_reference():
  assert BasicAccounts.first.id == DependentAccounts.fourth.x, "%s != %s" % (BasicAccounts.first.id, DependentAccounts.fourth.x)

@with_empty_db
@DependentAccounts
def test_dependent_fixture_attribute_reference():
  assert 'Account1' == DependentAccounts.fourth.y

@with_empty_db
def test_recursive_loading_due_to_dependent_props():
  @DependentAccounts
  @BasicAccounts
  def some_method():
    assert isinstance(BasicAccounts.first, Account)
    assert isinstance(BasicAccounts.second, Account)
    assert isinstance(DependentAccounts.fourth, Account)
  assert not isinstance(BasicAccounts.first, Account)
  assert not isinstance(BasicAccounts.second, Account)
  assert not isinstance(DependentAccounts.fourth, Account)

@with_empty_db
def test_recursive_loading_due_to_repeatation():
  @BasicAccounts
  @BasicAccounts
  def some_method():
    assert isinstance(BasicAccounts.first, Account)
    assert isinstance(BasicAccounts.second, Account)
  assert not isinstance(BasicAccounts.first, Account)
  assert not isinstance(BasicAccounts.second, Account)


@with_empty_db
def test_derived_direct_access():
  assert 70 == DerivedAccounts.fifth.x
  assert 81 == DerivedAccounts.fifth.y

@with_empty_db
@DerivedAccounts
def test_derived_loaded_access():
  assert 70 == DerivedAccounts.fifth.x
  assert 81 == DerivedAccounts.fifth.y
