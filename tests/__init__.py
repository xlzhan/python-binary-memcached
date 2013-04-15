import mock
import unittest
import bmemcached
from bmemcached.exceptions import InvalidCredentials, AuthenticationNotSupported, MemcachedException


class MemcachedTests(unittest.TestCase):
    def setUp(self):
        self.server = '127.0.0.1:11211'
        self.client = bmemcached.Client(self.server, 'user', 'password')

    def tearDown(self):
        self.client.delete('test_key')
        self.client.delete('test_key2')
        self.client.disconnect_all()

    def testSet(self):
        self.assertTrue(self.client.set('test_key', 'test'))

    def testSetMulti(self):
        self.assertTrue(self.client.set_multi({
            'test_key': 'value',
            'test_key2': 'value2'}))

    def testGet(self):
        self.client.set('test_key', 'test')
        self.assertEqual('test', self.client.get('test_key'))

    def testGetEmptyString(self):
        self.client.set('test_key', '')
        self.assertEqual('', self.client.get('test_key'))

    def testGetMulti(self):
        self.assertTrue(self.client.set_multi({
            'test_key': 'value',
            'test_key2': 'value2'
        }))
        self.assertEqual({'test_key': 'value', 'test_key2': 'value2'},
                         self.client.get_multi(['test_key', 'test_key2']))
        self.assertEqual({'test_key': 'value', 'test_key2': 'value2'},
                         self.client.get_multi(['test_key', 'test_key2', 'nothere']))

    def testGetLong(self):
        self.client.set('test_key', 1L)
        value = self.client.get('test_key')
        self.assertEqual(1L, value)
        self.assertTrue(isinstance(value, long))

    def testGetInteger(self):
        self.client.set('test_key', 1)
        value = self.client.get('test_key')
        self.assertEqual(1, value)
        self.assertTrue(isinstance(value, int))

    def testGetObject(self):
        self.client.set('test_key', {'a': 1})
        value = self.client.get('test_key')
        self.assertTrue(isinstance(value, dict))
        self.assertTrue('a' in value)
        self.assertEqual(1, value['a'])

    def testDelete(self):
        self.client.set('test_key', 'test')
        self.assertTrue(self.client.delete('test_key'))
        self.assertEqual(None, self.client.get('test_key'))

    def testDeleteUnknownKey(self):
        self.assertTrue(self.client.delete('test_key'))

    def testAddPass(self):
        self.assertTrue(self.client.add('test_key', 'test'))

    def testAddFail(self):
        self.client.add('test_key', 'value')
        self.assertFalse(self.client.add('test_key', 'test'))

    def testReplacePass(self):
        self.client.add('test_key', 'value')
        self.assertTrue(self.client.replace('test_key', 'value2'))
        self.assertEqual('value2', self.client.get('test_key'))

    def testReplaceFail(self):
        self.assertFalse(self.client.replace('test_key', 'value'))

    def testIncrement(self):
        self.assertEqual(0, self.client.incr('test_key', 1))
        self.assertEqual(1, self.client.incr('test_key', 1))

    def testDecrement(self):
        self.assertEqual(0, self.client.decr('test_key', 1))
        self.assertEqual(0, self.client.decr('test_key', 1))

    def testFlush(self):
        self.client.set('test_key', 'test')
        self.assertTrue(self.client.flush_all())
        self.assertEqual(None, self.client.get('test_key'))

    def testStats(self):
        stats = self.client.stats()[self.server]
        self.assertTrue('pid' in stats)

        stats = self.client.stats('settings')[self.server]
        self.assertTrue('verbosity' in stats)

        stats = self.client.stats('slabs')[self.server]
        self.assertTrue('1:get_hits' in stats)


class SocketMemcachedTests(MemcachedTests):
    """
    Same tests as above, just make sure it works with sockets.
    """
    def setUp(self):
        self.server = '/tmp/memcached.sock'
        self.client = bmemcached.Client(self.server, 'user', 'password')


class TestMemcachedErrors(unittest.TestCase):
    def testGet(self):
        """
        Raise MemcachedException if request wasn't successful and
        wasn't a 'key not found' error.
        """
        client = bmemcached.Client('127.0.0.1:11211', 'user', 'password')
        with mock.patch.object(bmemcached.client.Server, '_get_response') as mocked_response:
            mocked_response.return_value = (0, 0, 0, 0, 0, 0x81, 0, 0, 0, 0)
            self.assertRaises(MemcachedException, client.get, 'foo')

    def testSet(self):
        """
        Raise MemcachedException if request wasn't successful and
        wasn't a 'key not found' or 'key exists' error.
        """
        client = bmemcached.Client('127.0.0.1:11211', 'user', 'password')
        with mock.patch.object(bmemcached.client.Server, '_get_response') as mocked_response:
            mocked_response.return_value = (0, 0, 0, 0, 0, 0x81, 0, 0, 0, 0)
            self.assertRaises(MemcachedException, client.set, 'foo', 'bar', 300)

    def testIncrDecr(self):
        """
        Incr/Decr raise MemcachedException unless the request wasn't
        successful.
        """
        client = bmemcached.Client('127.0.0.1:11211', 'user', 'password')
        client.set('foo', 1)
        with mock.patch.object(bmemcached.client.Server, '_get_response') as mocked_response:
            mocked_response.return_value = (0, 0, 0, 0, 0, 0x81, 0, 0, 0, 2)
            self.assertRaises(MemcachedException, client.incr, 'foo', 1)
            self.assertRaises(MemcachedException, client.decr, 'foo', 1)

    def testDelete(self):
        """
        Raise MemcachedException if the delete request isn't successful.
        """
        client = bmemcached.Client('127.0.0.1:11211', 'user', 'password')
        client.flush_all()
        with mock.patch.object(bmemcached.client.Server, '_get_response') as mocked_response:
            mocked_response.return_value = (0, 0, 0, 0, 0, 0x81, 0, 0, 0, 0)
            self.assertRaises(MemcachedException, client.delete, 'foo')

    def testFlushAll(self):
        """
        Raise MemcachedException if the flush wasn't successful.
        """
        client = bmemcached.Client('127.0.0.1:11211', 'user', 'password')
        with mock.patch.object(bmemcached.client.Server, '_get_response') as mocked_response:
            mocked_response.return_value = (0, 0, 0, 0, 0, 0x81, 0, 0, 0, 0)
            self.assertRaises(MemcachedException, client.flush_all)


class TestServerParsing(unittest.TestCase):
    def testAcceptStringServer(self):
        client = bmemcached.Client('127.0.0.1:11211')
        self.assertEqual(len(client.servers), 1)

    def testAcceptIterableServer(self):
        client = bmemcached.Client(['127.0.0.1:11211', '127.0.0.1:11211'])
        self.assertEqual(len(client.servers), 2)

    def testNoPortGiven(self):
        server = bmemcached.client.Server('127.0.0.1')
        self.assertEqual(server.host, '127.0.0.1')
        self.assertEqual(server.port, 11211)

    def testInvalidPort(self):
        server = bmemcached.client.Server('127.0.0.1:blah')
        self.assertEqual(server.host, '127.0.0.1')
        self.assertEqual(server.port, 11211)

    def testNonStandardPort(self):
        server = bmemcached.client.Server('127.0.0.1:5000')
        self.assertEqual(server.host, '127.0.0.1')
        self.assertEqual(server.port, 5000)

    def testAcceptUnixSocket(self):
        client = bmemcached.Client('/tmp/memcached.sock')
        self.assertEqual(len(client.servers), 1)

    @mock.patch.object(bmemcached.client.Server, '_get_response')
    def testPassCredentials(self, mocked_response):
        """
        If username/password passed to Client, auto-authenticate.
        """
        mocked_response.return_value = (0, 0, 0, 0, 0, 0, 0, 0, 0, ['PLAIN'])
        client = bmemcached.Client('127.0.0.1:11211', username='user',
                                   password='password')
        server = client.servers[0]
        self.assertTrue(server.authenticated)

    @mock.patch.object(bmemcached.client.Server, '_get_response')
    def testNoCredentialsNoAuth(self, mocked_response):
        mocked_response.return_value = (0, 0, 0, 0, 0, 0x01, 0, 0, 0, ['PLAIN'])
        client = bmemcached.Client('127.0.0.1:11211')
        server = client.servers[0]
        self.assertFalse(server.authenticated)

    def testNoServersSupplied(self):
        """
        Raise assertion if the server list is empty.
        """
        self.assertRaises(AssertionError, bmemcached.Client, [])


class TestServerAuth(unittest.TestCase):
    @mock.patch.object(bmemcached.client.Server, '_get_response')
    def testServerDoesntNeedAuth(self, mocked_response):
        """
        If 0x81 ('unkown_command') comes back in the status field when
        authenticating, it isn't needed.
        """
        mocked_response.return_value = (0, 0, 0, 0, 0, 0x81, 0, 0, 0, 0)
        server = bmemcached.client.Server('127.0.0.1')
        # can pass anything and it'll work
        self.assertTrue(server.authenticate('user', 'badpassword'))

    @mock.patch.object(bmemcached.client.Server, '_get_response')
    def testNotUsingPlainAuth(self, mocked_response):
        """
        Raise AuthenticationNotSupported unless we're using PLAIN auth.
        """
        mocked_response.return_value = (0, 0, 0, 0, 0, 0, 0, 0, 0, [])
        server = bmemcached.client.Server('127.0.0.1')
        self.assertRaises(AuthenticationNotSupported,
                          server.authenticate, 'user', 'password')

    @mock.patch.object(bmemcached.client.Server, '_get_response')
    def testAuthNotSuccessful(self, mocked_response):
        """
        Raise MemcachedException for anything unsuccessful.
        """
        mocked_response.return_value = (0, 0, 0, 0, 0, 0x01, 0, 0, 0, ['PLAIN'])
        server = bmemcached.client.Server('127.0.0.1')
        self.assertRaises(MemcachedException,
                          server.authenticate, 'user', 'password')

    @mock.patch.object(bmemcached.client.Server, '_get_response')
    def testAuthSuccessful(self, mocked_response):
        """
        Valid logins return True.
        """
        mocked_response.return_value = (0, 0, 0, 0, 0, 0, 0, 0, 0, ['PLAIN'])
        server = bmemcached.client.Server('127.0.0.1')
        self.assertTrue(server.authenticate('user', 'password'))

    @mock.patch.object(bmemcached.client.Server, '_get_response')
    def testAuthUnsuccessful(self, mocked_response):
        """
        Invalid logins raise InvalidCredentials
        """
        mocked_response.return_value = (0, 0, 0, 0, 0, 0x08, 0, 0, 0, ['PLAIN'])
        server = bmemcached.client.Server('127.0.0.1')
        self.assertRaises(InvalidCredentials, server.authenticate,
                          'user', 'password2')
