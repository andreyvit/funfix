Funfix: Fixtures for Python
===========================

Funfix complements the story of your tests with clear & concise fixtures that are fun to write. Currently works with Google App Engine's Datastore, looking for contributors to support other ORMs.


Really Basic Usage
------------------

Say you have the following models:

    # mymodels.py
    class Post(db.Model):
      title = db.TextProperty()
      body  = db.TextProperty()
    
    class Comment(db.Model):
      post   = db.ReferenceProperty(Post)
      author = db.StringProperty()
      body   = db.TextProperty()

Defining a simple fixture is as simple as:

    # myfixtures.py
    from funfix import AppEngineFixture as Fixture
    from mymodels import Post, Comment
  
    class Posts(Fixture, Post):
  
      class initial:
        title = "Starting a blog"
        body  = "Hey, I'm blogging now!"
      
      class sorry:
        title = "Long time no see..."
        body  = "Sorry, I've been away for a while: too much work. But now I'll definitely blog more!"
      
Usage #1: You can simply reference the values of the fixtures anywhere:

    def can_reference_values_anywhere():
      print Posts.initial.body
      assert not isinstance(Posts.initial, Post)  # Posts.initial is a regular Python class
    
Usage #2: To actually load the fixtures into the datastore, use the fixture class as a decorator:

    @Posts
    def runs_with_fixtures_in_the_db():
      assert isinstance(Posts.initial, Post)  # look, ma, Posts.initial is now a model instance!
      print Posts.initial.body
      print Posts.initial.key()  # since it's in the DB, can get id/key now
    
After the decorated method returns, the fixtures are removed from the database, and `Posts.initial` becomes a boring regular Python class again.


Referencing Other Objects
-------------------------

Time to add some comments!
  
    class Comments(Fixture, Comment):
  
      class hey:
        post   = Posts.initial
        author = "Andrey"
        body   = "Great news! Just wanted to say hey."
      
      class spam:
        post   = Posts.initial
        author = "Jack"
        body   = "Buy our new pills! http://www.example.com/pills"
      
Again, loading them is easy:

    @Comments
    def test_some_comments():
      print Comments.hey.post.author
      print Posts.initial
      
Note that all referenced fixtures are loaded too, so loading Comments automatically loads `Posts.initial` (but not `Posts.sorry`, since `Posts.sorry` is not referenced).

Need a fancier dependency? Use a lambda expression (or a function):

    class MoreComments(Fixture, Comment):
      class fancy:
        key_name = lambda: 'Comment-for-%s' % Posts.initial.key().id_or_name()
        post     = Posts.initial
        author   = "Kate"
        body     = "Where's Aeron?"
        
Need to get even fancier? Accept a 'self' argument:

    class EvenMoreComments(Fixture, Comment):
      class fancy:
        post     = Posts.initial
        author   = "Kate"
        body     = lambda self: "Where's Aeron? -- %s." % self.author
        
        def key_name(self):
          # e.g. "fancy-comment-from-Kate-for-1"
          return '%s-comment-from-%s-for-%s' % (self.__name__, self.author, Posts.initial.key().id_or_name())

Note: simply referencing `Posts.initial.key()` will NOT work outside of a decorated method, because the fixture is not loaded yet and thus `Posts.initial` is not a model object yet:

    # BAD BAD BAD
    class MoreComments(Fixture, Comment):
      class fancy:
        # AttributeError: Posts.initial does not have a `key` attribute yet
        key_name = 'Comment-for-%s' % Posts.initial.key().name()
        post     = Posts.initial
        author   = "Kate"
        body     = "Where's Aeron?"
        

Derivation
----------

You can derive fixture classes from each other, and you can derive individual fixtures from each other. This works just as you can expect:

    class GeneralAccounts(Fixture, Account):
      class acme:
        name = 'Acme LLC'
    
    class MoreAccounts(GeneralAccounts):
      class borey:
        name = 'Borey Inc.'
        
    class Invitations(Fixture, Invitation):
      
      class acme_uninvited:
        email = 'ceo@acme.com'
        name = 'Jack Betauser'
        invitation_code = None
        
      class acme_invited(acme_uninvited):
        invitation_code = '12345'
        
    class AccountPack(Posts, Comments, MoreComments, MoreAccounts, Invitations): pass
    
    ...
    
    @AccountPack
    def process_something():
      print GeneralAccounts.acme.key()
      print MoreAccounts.borey.key()
      print Comments.spam.key()
      
      
Options
-------

If you think that deriving from a model class is ugly, you can also specify it using a class attribute:

    class Posts(Fixture):
      Entity = Post

      class initial:
        title = "Starting a blog"
        body  = "Hey, I'm blogging now!"
        
        
Google App Engine Key Name Generation
-------------------------------------

Goole App Engine backend in funfix simply passes all values into the constructor of the model class as named arguments.
This means that anything that db.Model constructor accepts can be specified in the fixture. For example, you can specify parent, key_name or an explicit key:

    class Posts(Fixture, Post):
      class initial:
        parent   = Users.bob  # the ancestor of the entity
        key_name = 'foo'      # explicit key name
        
However, since key names are so common in App Engine, there is a better way to provide them.
If your model defines a static method called key_name_for or key_for,
it will be automatically called to generate the key name for a new entity. Here's an example:

    import hashlib
    
    class Comment(db.Model):
      blog   = db.ReferenceProperty(Blog)
      post   = db.ReferenceProperty(Post)
      author = db.StringProperty()
      body   = db.TextProperty()
      
      @staticmethod
      def key_name_for(blog_key_name, post_key, author, body):
        hash = hashlib.sha1(author + body).hexdigest()
        return 'C-%s-%s-%s' % (blog_key_name, post_key.id_or_name(), hash)
  
    class Comments(Fixture, Comment):
      class hey:
        blog   = Blogs.jacks_whines
        post   = Posts.hey
        author = 'Sawer'
        body   = 'Hey yourself.'
        
A key name for Comments.hey will be automatically generated by calling Comment.key_name_for.
Arguments will be supplied based on a naming convention.
Basically, argument names must match the attributes of the fixture,
possibly with '_key' or '_key_name' appended.
(Appending '_key' makes sure model instances are turned into keys,
and appending '_key_name' makes sure model instances or keys are all turned into key names.)

Naturally, a function called 'key_name_for' is expected to return a string,
and a function called 'key_for' is expected to return db.Key.


Adopt to Your Database
----------------------

Fun Fixtures currently only supports Google App Engine, but this is easy to fix. Look how easy it was to support the App Engine:

    from funfix.common import AbstractFixture

    class AppEngineFixture(AbstractFixture):

      @classmethod
      def get_primary_key(fix_klass, item_klass, item_instance):
        return item_instance.key()
  
      @classmethod
      def create_item_instance(fix_klass, item_klass, values):
        result = fix_klass.Entity(**values)
        result.put()
        return result
    
      @classmethod
      def destroy_item_instance(fix_klass, item_klass, item_instance):
        item_instance.delete()

Certainly you can do it for your database engine too. Contributions are very welcome!


Running Tests
-------------

If you happen to be contributing to the core, you'd want to be able to run tests.
Please do:

    sudo easy_install -U setuptools
    sudo easy_install nose
    sudo easy_install coverage
    
(On my system, the last command still complained about outdated setuptools, so I had to run remove setuptools from /System/Library/Frameworks/Python.framework/Versions/2.5/Extras/lib/python/ and remove /usr/bin/easy_install, so that /usr/local/bin/easy_install installed by the first easy_install would be picked up.)

Then run the tests using:

    nodetests

To run tests continuously during development, download nosyd (http://github.com/lacostej/nosyd). Run it in a separate terminal window, and then use `nosyd -a` in the project directory to start monitoring it.

To get nosyd to show nice Growl notifications on a Mac, download Growl SDK from http://growl.info/downloads_developers.php; click the file to mount it. Then:

    $ cp -r '/Volumes/Growl 1.2 SDK/Bindings/python/' /tmp/py-Growl
    $ cd /tmp/py-Growl/
    $ sudo python setup.py install


Inspiration
-----------

The idea is inpired by the simplicity of Rails fixtures. The implementation is inspired by the Python fixture library (http://code.google.com/p/fixture/).

The author of 'fixture' refused to accept some patches making its APIs more fun to work with,
and I hated bloating my test code, and thus funfix was born.
This is not a fork since the original lib is unnecessarily complicated inside,
and I believe I can write a much smaller and straightforward one.
