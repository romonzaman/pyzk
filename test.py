import sys
import os
import unittest
import codecs
from mock import patch, Mock, MagicMock
mock_socket = MagicMock(name='zk.socket')
sys.modules['zk.socket'] = mock_socket
from zk import ZK, const
from zk.base import ZK_helper
from zk.user import User
from zk.finger import Finger
from zk.attendance import Attendance
from zk.exception import ZKErrorResponse, ZKNetworkError

try:
    unittest.TestCase.assertRaisesRegex
except AttributeError:
    unittest.TestCase.assertRaisesRegex = unittest.TestCase.assertRaisesRegexp

def dump(obj, nested_level=0, output=sys.stdout):
    spacing = '   '
    if type(obj) == dict:
        print >> output, '%s{' % ((nested_level) * spacing)
        for k, v in obj.items():
            if hasattr(v, '__iter__'):
                print >> output, '%s%s:' % ((nested_level + 1) * spacing, k)
                dump(v, nested_level + 1, output)
            else:
                print >> output, '%s%s: %s' % ((nested_level + 1) * spacing, k, v)
        print >> output, '%s}' % (nested_level * spacing)
    elif type(obj) == list:
        print >> output, '%s[' % ((nested_level) * spacing)
        for v in obj:
            if hasattr(v, '__iter__'):
                dump(v, nested_level + 1, output)
            else:
                print >> output, '%s%s' % ((nested_level + 1) * spacing, v)
        print >> output, '%s]' % ((nested_level) * spacing)
    else:
        print >> output, '%s%s' % (nested_level * spacing, obj)


class PYZKTest(unittest.TestCase):
    def setup(self):

        pass

    def tearDown(self):
        pass

    @patch('zk.base.socket')
    @patch('zk.base.ZK_helper')
    def test_no_ping(self,helper, socket):
        """ what if ping doesn't response """
        helper.return_value.test_ping.return_value = False #no ping simulated
        #begin
        zk = ZK('192.168.1.201')
        helper.assert_called_with('192.168.1.201', 4370) # called correctly
        self.assertRaisesRegex(ZKNetworkError, "can't reach device", zk.connect)

    @patch('zk.base.socket')
    @patch('zk.base.ZK_helper')
    def test_correct_ping(self,helper, socket):
        """ what if ping is ok """
        helper.return_value.test_ping.return_value = True # ping simulated
        helper.return_value.test_tcp.return_value = 1 # helper tcp ok
        socket.return_value.recv.return_value = b''
        #begin
        zk = ZK('192.168.1.201')
        helper.assert_called_with('192.168.1.201', 4370) # called correctly
        self.assertRaisesRegex(ZKNetworkError, "unpack requires", zk.connect) # no data...?

    @patch('zk.base.socket')
    @patch('zk.base.ZK_helper')
    def test_tcp_invalid(self, helper, socket):
        """ Basic tcp invalid """
        helper.return_value.test_ping.return_value = True # ping simulated
        helper.return_value.test_tcp.return_value = 0 # helper tcp ok
        socket.return_value.recv.return_value = b'Invalid tcp data'
        #begin
        zk = ZK('192.168.1.201')
        helper.assert_called_with('192.168.1.201', 4370) # called correctly
        self.assertRaisesRegex(ZKNetworkError, "TCP packet invalid", zk.connect)

    @patch('zk.base.socket')
    @patch('zk.base.ZK_helper')
    def test_tcp_connect(self, helper, socket):
        """ Basic connection test """
        helper.return_value.test_ping.return_value = True # ping simulated
        helper.return_value.test_tcp.return_value = 0 # helper tcp ok
        socket.return_value.recv.return_value = codecs.decode('5050827d08000000d007fffc2ffb0000','hex') # tcp CMD_ACK_OK
        #begin
        zk = ZK('192.168.1.201') # already tested
        conn = zk.connect()
        socket.return_value.send.assert_called_with(codecs.decode('5050827d08000000e80317fc00000000', 'hex'))
        conn.disconnect()
        socket.return_value.send.assert_called_with(codecs.decode('5050827d08000000e903e6002ffb0100', 'hex'))

    @patch('zk.base.socket')
    @patch('zk.base.ZK_helper')
    def test_force_udp_connect(self, helper, socket):
        """ Force UDP connection test """
        helper.return_value.test_ping.return_value = True # ping simulated
        helper.return_value.test_tcp.return_value = 0 # helper tcp ok
        socket.return_value.recv.return_value = codecs.decode('d007fffc2ffb0000','hex') # tcp CMD_ACK_OK
        #begin
        zk = ZK('192.168.1.201', force_udp=True)
        conn = zk.connect()
        socket.return_value.sendto.assert_called_with(codecs.decode('e80317fc00000000', 'hex'), ('192.168.1.201', 4370))
        conn.disconnect()
        socket.return_value.sendto.assert_called_with(codecs.decode('e903e6002ffb0100', 'hex'), ('192.168.1.201', 4370))

    @patch('zk.base.socket')
    @patch('zk.base.ZK_helper')
    def test_udp_connect(self, helper, socket):
        """ Basic auto UDP connection test """
        helper.return_value.test_ping.return_value = True # ping simulated
        helper.return_value.test_tcp.return_value = 1 # helper tcp nope
        socket.return_value.recv.return_value = codecs.decode('d007fffc2ffb0000','hex') # tcp CMD_ACK_OK
        #begin
        zk = ZK('192.168.1.201')
        conn = zk.connect()
        socket.return_value.sendto.assert_called_with(codecs.decode('e80317fc00000000', 'hex'), ('192.168.1.201', 4370))
        conn.disconnect()
        socket.return_value.sendto.assert_called_with(codecs.decode('e903e6002ffb0100', 'hex'), ('192.168.1.201', 4370))

    @patch('zk.base.socket')
    @patch('zk.base.ZK_helper')
    def test_tcp_unauth(self, helper, socket):
        """ Basic unauth test """
        helper.return_value.test_ping.return_value = True # ping simulated
        helper.return_value.test_tcp.return_value = 0 # helper tcp ok
        socket.return_value.recv.side_effect = [
            codecs.decode('5050827d08000000d5075bb2cf450000', 'hex'), # tcp CMD_UNAUTH
            codecs.decode('5050827d08000000d5075ab2cf450100', 'hex') # tcp CMD_UNAUTH
        ]
        #begin
        zk = ZK('192.168.1.201', password=12)
        self.assertRaisesRegex(ZKErrorResponse, "Unauthenticated", zk.connect)
        socket.return_value.send.assert_called_with(codecs.decode('5050827d0c0000004e044e2ccf450100614d323c', 'hex')) # try with password 12

    @patch('zk.base.socket')
    @patch('zk.base.ZK_helper')
    def test_tcp_auth(self, helper, socket):
        """ Basic auth test """
        helper.return_value.test_ping.return_value = True # ping simulated
        helper.return_value.test_tcp.return_value = 0 # helper tcp ok
        socket.return_value.recv.side_effect = [
            codecs.decode('5050827d08000000d5075bb2cf450000', 'hex'), # tcp CMD_UNAUTH
            codecs.decode('5050827d08000000d0075fb2cf450100', 'hex'), # tcp CMD_ACK_OK
            codecs.decode('5050827d08000000d00745b2cf451b00', 'hex') # tcp random CMD_ACK_OK TODO: generate proper sequenced response

        ]
        #begin
        zk = ZK('192.168.1.201', password=45)
        conn = zk.connect()
        socket.return_value.send.assert_called_with(codecs.decode('5050827d0c0000004e044db0cf45010061c9323c', 'hex')) #auth with pass 45
        conn.disconnect()
        socket.return_value.send.assert_called_with(codecs.decode('5050827d08000000e90345b6cf450200', 'hex')) #exit

    @patch('zk.base.socket')
    @patch('zk.base.ZK_helper')
    def test_tcp_get_size(self, helper, socket):
        """ can read sizes? """
        helper.return_value.test_ping.return_value = True # ping simulated
        helper.return_value.test_tcp.return_value = 0 # helper tcp ok
        socket.return_value.recv.side_effect = [
            codecs.decode('5050827d08000000d0075fb2cf450100', 'hex'), # tcp CMD_ACK_OK
            codecs.decode('5050827d64000000d007a3159663130000000000000000000000000000000000070000000000000006000000000000005d020000000000000f0c0000000000000100000000000000b80b000010270000a0860100b20b00000927000043840100000000000000', 'hex'), #sizes
            codecs.decode('5050827d08000000d00745b2cf451b00', 'hex'), # tcp random CMD_ACK_OK TODO: generate proper sequenced response
        ]
        #begin
        zk = ZK('192.168.1.201') # already tested
        conn = zk.connect()
        socket.return_value.send.assert_called_with(codecs.decode('5050827d08000000e80317fc00000000', 'hex'))
        conn.read_sizes()
        socket.return_value.send.assert_called_with(codecs.decode('5050827d080000003200fcb9cf450200', 'hex'))
        conn.disconnect()
        self.assertEqual(conn.users, 7, "missed user data %s" % conn.users)
        self.assertEqual(conn.fingers, 6, "missed finger data %s" % conn.fingers)
        self.assertEqual(conn.records, 605, "missed record data %s" % conn.records)
        self.assertEqual(conn.users_cap, 10000, "missed user cap %s" % conn.users_cap)
        self.assertEqual(conn.fingers_cap, 3000, "missed finger cap %s" % conn.fingers_cap)
        self.assertEqual(conn.rec_cap, 100000, "missed record cap %s" % conn.rec_cap)

    @patch('zk.base.socket')
    @patch('zk.base.ZK_helper')
    def test_tcp_get_users_small_data(self, helper, socket):
        """ can get empty? """
        helper.return_value.test_ping.return_value = True # ping simulated
        helper.return_value.test_tcp.return_value = 0 # helper tcp ok
        socket.return_value.recv.side_effect = [
            codecs.decode('5050827d08000000d0075fb2cf450100', 'hex'), # tcp CMD_ACK_OK
            codecs.decode('5050827d64000000d007a3159663130000000000000000000000000000000000070000000000000006000000000000005d020000000000000f0c0000000000000100000000000000b80b000010270000a0860100b20b00000927000043840100000000000000', 'hex'), #sizes
            codecs.decode('5050827d04020000dd05942c96631500f801000001000e0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000003830380000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000003832310000000000000000000000000000000000000000000300000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000003833350000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000003833310000000000000000000000000000000000000000000500000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000003833320000000000000000000000000000000000000000000600000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000003836000000000000000000000000000000000000000000000c0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000383432000000000000000000000000000000000000000000','hex'), #DATA directly(not ok)
            codecs.decode('5050827d08000000d00745b2cf451b00', 'hex'), # tcp random CMD_ACK_OK TODO: generate proper sequenced response
            #codecs.decode('5050827d08000000d00745b2cf451b00', 'hex')  # tcp random CMD_ACK_OK TODO: generate proper sequenced response
        ]
        #begin
        zk = ZK('192.168.1.201' )
        conn = zk.connect()
        socket.return_value.send.assert_called_with(codecs.decode('5050827d08000000e80317fc00000000', 'hex'))
        users = conn.get_users()
        socket.return_value.send.assert_called_with(codecs.decode('5050827d13000000df053ca6cf4514000109000500000000000000', 'hex')) #get users
        self.assertEqual(len(users), 7, "incorrect size %s" % len(users))
        #assert one user
        usu = users[3]
        self.assertIsInstance(usu.uid, int, "uid should be int() %s" % type(usu.uid))
        if sys.version_info >= (3, 0):
            self.assertIsInstance(usu.user_id, (str, bytes), "user_id should be str() or bytes() %s" % type(usu.user_id))
        else:
            self.assertIsInstance(usu.user_id, (str, unicode), "user_id should be str() or unicode() %s" % type(usu.user_id))
        self.assertEqual(usu.uid, 4, "incorrect uid %s" % usu.uid)
        self.assertEqual(usu.user_id, "831", "incorrect user_id %s" % usu.user_id)
        self.assertEqual(usu.name, "NN-831", "incorrect uid %s" % usu.name) # generated
        conn.disconnect()

    @patch('zk.base.socket')
    @patch('zk.base.ZK_helper')
    def test_tcp_get_users_broken_data(self, helper, socket):
        """ test case for K20 """
        helper.return_value.test_ping.return_value = True # ping simulated
        helper.return_value.test_tcp.return_value = 0 # helper tcp ok
        socket.return_value.recv.side_effect = [
            codecs.decode('5050827d08000000d007d7d758200000','hex'), #ACK Ok
            codecs.decode('5050827d58000000d0074c49582013000000000000000000000000000000000002000000000000000000000000000000000000000000000007000000000000000000000000000000f4010000f401000050c30000f4010000f201000050c30000','hex'),#Sizes
            codecs.decode('5050827d9c000000dd053c87582015009000000001000000000000000000006366756c616e6f0000000000000000000000000000000000000000000000000000000000003130303030316c70000000000000000000000000000000000200000000000000000000726d656e67616e6f0000000000000000000000000000000000','hex'),#DATA112
            codecs.decode('000000000000000000000000323232323232636200000000000000000000000000000000','hex'), #extra data 36
            #codecs.decode('','hex'), #
            codecs.decode('5050827d08000000d00745b2cf451b00', 'hex'),  # CMD_ACK_OK for get_users TODO: generate proper sequenced response
            codecs.decode('5050827d08000000d00745b2cf451b00', 'hex'),  # CMD_ACK_OK for free_data TODO: generate proper sequenced response
            codecs.decode('5050827d08000000d00745b2cf451b00', 'hex'),  # CMD_ACK_OK for exit      TODO: generate proper sequenced response
        ]
        #begin
        zk = ZK('192.168.1.201') #, verbose=True)
        conn = zk.connect()
        socket.return_value.send.assert_called_with(codecs.decode('5050827d08000000e80317fc00000000', 'hex'))
        users = conn.get_users()
        #print (users) #debug
        socket.return_value.send.assert_called_with(codecs.decode('5050827d13000000df05b3cb582014000109000500000000000000', 'hex')) #get users
        self.assertEqual(len(users), 2, "incorrect size %s" % len(users))
        #assert one user
        usu = users[1]
        self.assertIsInstance(usu.uid, int, "uid should be int() %s" % type(usu.uid))
        if sys.version_info >= (3, 0):
            self.assertIsInstance(usu.user_id, (str, bytes), "user_id should be str() or bytes() %s" % type(usu.user_id))
        else:
            self.assertIsInstance(usu.user_id, (str, unicode), "user_id should be str() or unicode() %s" % type(usu.user_id))
        self.assertEqual(usu.uid, 2, "incorrect uid %s" % usu.uid)
        self.assertEqual(usu.user_id, "222222cb", "incorrect user_id %s" % usu.user_id)
        self.assertEqual(usu.name, "rmengano", "incorrect uid %s" % usu.name) # check test case
        conn.disconnect()


    @patch('zk.base.socket')
    @patch('zk.base.ZK_helper')
    def test_tcp_get_users_broken_tcp(self, helper, socket):
        """ tst case for https://github.com/fananimi/pyzk/pull/18#issuecomment-406250746 """
        helper.return_value.test_ping.return_value = True # ping simulated
        helper.return_value.test_tcp.return_value = 0 # helper tcp ok
        socket.return_value.recv.side_effect = [
            codecs.decode('5050827d09000000d007babb5c3c100009', 'hex'), # tcp CMD_ACK_OK
            codecs.decode('5050827d58000000d007292c5c3c13000000000000000000000000000000000046000000000000004600000000000000990c0000000000001a010000000000000600000006000000f4010000f401000050c30000ae010000ae010000b7b60000', 'hex'), #sizes
            codecs.decode('5050827d15000000d007a7625c3c150000b4130000b4130000cdef2300','hex'), #PREPARE_BUFFER -> OK 5044
            codecs.decode('5050827d10000000dc050da65c3c1600b4130000f0030000', 'hex'), # read_buffer -> Prepare_data 5044
            codecs.decode('5050827df8030000dd05d05800001600b013000001000e35313437393833004a6573757353616c646976617200000000000000000000000000000001000000000000000035313437393833000000000000000000000000000000000002000e33343934383636004e69657665734c6f70657a00000000000000000000000000000000000100000000000000003334393438363600000000000000000000000000000000000300000000000000000000000000000000000000000000000000000000000000000000000000000100000000000000003337333139333600000000000000000000000000', 'hex'), #  DATA 1016 -8 (util 216)
            codecs.decode('0000000100000000000000003734383433330000000000000000000000000000000000000800000000000000000000000000000000000000000000000000000000000000000000000000000100000000000000003433333939353800000000000000000000000000000000000900000000000000000000000000000000000000000000000000000000000000000000000000000100000000000000003333373335313100000000000000000000000000000000000a00000000000000000000000000000000000000000000000000000000000000000000000000000100000000000000003337373535363100000000000000000000000000000000000b000000', 'hex'), # raw data 256
            codecs.decode('0000000004000e00000000000000000000000000000000000000000000000000000000000000000000000001000000000000000032333338323035000000000000000000000000000000000005000e000000000000000000000000000000000000000000000000000000000000000000000000010000000000000000333632363439300000000000000000000000000000000000060000000000000000000000000000000000000000000000000000000000000000000000000000010000000000000000313838343633340000000000000000000000000000000000070000000000000000000000000000000000000000000000000000000000000000000000', 'hex'), #raw data 256
            codecs.decode('00000000000000000000000000000000000000000000000000000000000000000000000100000000000000003131313336333200000000000000000000000000000000000c00000000000000000000000000000000000000000000000000000000000000000000000000000100000000000000003130353233383900000000000000000000000000000000000d00000000000000000000000000000000000000000000000000000000000000000000000000000100000000000000003135333538333600000000000000000000000000000000000e00000000000000000000000000000000000000000000000000000000000000000000000000000100000000', 'hex'), #raw data 256
            codecs.decode('000000003933313637300000000000000000000000000000', 'hex'), #raw data 24

            codecs.decode('5050827df8030000dd0520b601001600000000000f00003334323931343800000000000000000000000000000000000000000000000000000000000100000000000000003334323931343800000000000000000000000000000000001000000000000000000000000000000000000000000000000000000000000000000000000000000100000000000000003139303636393700000000000000000000000000000000001100000000000000000000000000000000000000000000000000000000000000000000000000000100000000000000003139333831333500000000000000000000000000', 'hex'), # DATA 1016 -8 (util216
            codecs.decode('00000000120000000000000000000000000000000000000000000000000000000000000000000000000000010000000000000000393231303537000000000000000000000000000000000000130000000000000000000000000000000000000000000000000000000000000000000000000000010000000000000000333634383739340000000000000000000000000000000000140000323831353732000000000000000000000000000000000000000000000000000000000000010000000000000000323831353732000000000000000000000000000000000000150000000000000000000000000000000000000000000000000000000000000000000000', 'hex'), #raw data 256
            codecs.decode('00000001000000000000000031383133323236000000000000000000000000000000000016000000000000000000000000000000000000000000000000000000000000000000000000000001000000000000000035393037353800000000000000000000000000000000000017000000000000000000000000000000000000000000000000000000000000000000000000000001000000000000000031363933373232000000000000000000000000000000000018000000000000000000000000000000000000000000000000000000000000000000000000000001000000000000000033363430323131000000000000000000000000000000000019000000', 'hex'), #raw data 256
            codecs.decode('00000000000000000000000000000000000000000000000000000000000000000000000100000000000000003331303733390000000000000000000000000000000000001a00000000000000000000000000000000000000000000000000000000000000000000000000000100000000000000003433353430393400000000000000000000000000000000001b00000000000000000000000000000000000000000000000000000000000000000000000000000100000000000000003338303736333200000000000000000000000000000000001c00000000000000000000000000000000000000000000000000000000000000000000000000000100000000', 'hex'), #raw data 256
            codecs.decode('000000003231333938313700000000000000000000000000', 'hex'), #raw data 24

            codecs.decode('5050827df8030000dd059a2102001600000000001d00000000000000000000000000000000000000000000000000000000000000000000000000000100000000000000003333383738313900000000000000000000000000000000001e00000000000000000000000000000000000000000000000000000000000000000000000000000100000000000000003439353634363800000000000000000000000000000000001f00000000000000000000000000000000000000000000000000000000000000000000000000000100000000000000003832343030300000000000000000000000000000', 'hex'), #DATA 1016 -8 (util 216)
            codecs.decode('00000000200000000000000000000000000000000000000000000000000000000000000000000000000000010000000000000000333937373437370000000000000000000000000000000000210000000000000000000000000000000000000000000000000000000000000000000000000000010000000000000000343435383038340000000000000000000000000000000000220000000000000000000000000000000000000000000000000000000000000000000000000000010000000000000000343430353130390000000000000000000000000000000000230000000000000000000000000000000000000000000000000000000000000000000000', 'hex'), #raw data 256
            codecs.decode('00000001000000000000000033353732363931000000000000000000000000000000000024000000000000000000000000000000000000000000000000000000000000000000000000000001000000000000000033363336333832000000000000000000000000000000000025000000000000000000000000000000000000000000000000000000000000000000000000000001000000000000000033333232353432000000000000000000000000000000000026000000000000000000000000000000000000000000000000000000000000000000000000000001000000000000000039393437303800000000000000000000000000000000000027000000', 'hex'), #raw data 256
            codecs.decode('00000000000000000000000000000000000000000000000000000000000000000000000100000000000000003836333539380000000000000000000000000000000000002800000000000000000000000000000000000000000000000000000000000000000000000000000100000000000000003338383736383000000000000000000000000000000000002900000000000000000000000000000000000000000000000000000000000000000000000000000100000000000000003739393434350000000000000000000000000000000000002a00000000000000000000000000000000000000000000000000000000000000000000000000000100000000', 'hex'), # raw data 256
            codecs.decode('000000003532313136340000000000000000000000000000', 'hex'), # raw data 24

            codecs.decode('5050827df8030000dd053da903001600000000002b00000000000000000000000000000000000000000000000000000000000000000000000000000100000000000000003439373033323400000000000000000000000000000000002c0000000000000000000000000000000000000000000000000000000000000000000000', 'hex'), # DATA 1016 -8 (util 112)
            codecs.decode('0000000100000000000000003134363732353100000000000000000000000000000000002d000e32363635373336006d61726368756b0000000000000000000000000000000000000000000100000000000000003236363537333600000000000000000000000000', 'hex'), # raw data 104
            codecs.decode('000000002e00000000000000000000000000000000000000000000000000000000000000000000000000000100000000000000003136383133353200000000000000000000000000000000002f000000000000000000000000000000000000000000000000000000000000000000000000000001000000000000000034393633363732000000000000000000000000000000000030000000', 'hex'), # raw data 152
            codecs.decode('00000000000000000000000000000000000000000000000000000000000000000000000100000000000000003337363137373100000000000000000000000000000000003100000000000000000000000000000000000000000000000000000000000000000000000000000100000000000000003231353939353100000000000000000000000000000000003200000000000000000000000000000000000000000000000000000000000000000000000000000100000000000000003136393734323700000000000000000000000000000000003300000000000000000000000000000000000000000000000000000000000000000000000000000100000000', 'hex'), # raw data 256
            codecs.decode('0000000033373336323437000000000000000000000000000000000034000000000000000000000000000000000000000000000000000000000000000000000000000001000000000000000031323930313635000000000000000000000000000000000035000000000000000000000000000000000000000000000000000000', 'hex'), # raw data 128
            codecs.decode('0000000000000000000000010000000000000000333236333636330000000000000000000000000000000000360000000000000000000000000000000000000000000000000000000000000000000000000000010000000000000000393031353036000000000000000000000000000000000000370000000000000000000000', 'hex'), # raw data 128
            codecs.decode('0000000000000000000000000000000000000000000000000000000100000000000000003238313732393300000000000000000000000000000000003800000000000000000000000000000000000000000000000000000000000000000000000000000100000000000000003437303630333800000000000000000000000000', 'hex'), # raw data 128

            codecs.decode('5050827df8030000dd05037d04001600000000003900000000000000000000000000000000000000000000000000000000000000000000000000000100000000000000003136343731353600000000000000000000000000000000003a0000000000000000000000000000000000000000000000000000000000000000000000', 'hex'), # DATA 1016 -8 (util 112)
            codecs.decode('0000000100000000000000003530313435310000000000000000000000000000000000003b00000000000000000000000000000000000000000000000000000000000000000000000000000100000000000000003534363236373300000000000000000000000000000000003c00000000000000000000000000000000000000000000000000000000000000000000000000000100000000000000003533363730310000000000000000000000000000000000003d00000000000000000000000000000000000000000000000000000000000000000000000000000100000000000000003435383033303700000000000000000000000000000000003e000000', 'hex'), # raw data 256
            codecs.decode('00000000000000000000000000000000000000000000000000000000000000000000000100000000000000003136333835333200000000000000000000000000000000003f000e3336323634313900000000000000000000000000000000000000000000000000000000000100000000000000003336323634313900000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000000000000000000100000000000000003233323331383500000000000000000000000000000000004100000000000000000000000000000000000000000000000000000000000000000000000000000100000000', 'hex'), # raw data 256
            codecs.decode('0000000035323930373337000000000000000000000000000000000042000000000000000000000000000000000000000000000000000000000000000000000000000001000000000000000033393839303636000000000000000000000000000000000043000000000000000000000000000000000000000000000000000000', 'hex'), # raw data 128
            codecs.decode('0000000000000000000000010000000000000000343033323930390000000000000000000000000000000000440000000000000000000000000000000000000000000000000000000000000000000000000000010000000000000000323034363338380000000000000000000000000000000000450000000000000000000000', 'hex'), # raw data 128
            codecs.decode('0000000000000000000000000000000000000000000000000000000100000000000000003733383730330000000000000000000000000000000000004600000000000000000000000000000000000000000000000000000000000000000000000000000100000000000000003239313836333600000000000000000000000000', 'hex'), # raw data 128

            codecs.decode('5050827d0c000000dd0507fa0500160000000000', 'hex'), #  DATA 12-8 (util 4 ok) and ACK OK!!!

            codecs.decode('5050827d08000000d00745b2cf451b00', 'hex'),  # CMD_ACK_OK for get_users TODO: generate proper sequenced response
            codecs.decode('5050827d08000000d00745b2cf451b00', 'hex'),  # CMD_ACK_OK for free_data TODO: generate proper sequenced response
            codecs.decode('5050827d08000000d00745b2cf451b00', 'hex'),  # CMD_ACK_OK for exit      TODO: generate proper sequenced response
        ]
        #begin
        zk = ZK('192.168.1.201') # , verbose=True)
        conn = zk.connect()
        socket.return_value.send.assert_called_with(codecs.decode('5050827d08000000e80317fc00000000', 'hex'))
        users = conn.get_users()
        #print (users) #debug
        socket.return_value.send.assert_called_with(codecs.decode('5050827d08000000de05aebd5c3c1700', 'hex')) #get users
        self.assertEqual(len(users), 70, "incorrect size %s" % len(users))
        #assert one user
        usu = users[1]
        self.assertIsInstance(usu.uid, int, "uid should be int() %s" % type(usu.uid))
        if sys.version_info >= (3, 0):
            self.assertIsInstance(usu.user_id, (str, bytes), "user_id should be str() or bytes() %s" % type(usu.user_id))
        else:
            self.assertIsInstance(usu.user_id, (str, unicode), "user_id should be str() or unicode() %s" % type(usu.user_id))
        self.assertEqual(usu.uid, 2, "incorrect uid %s" % usu.uid)
        self.assertEqual(usu.user_id, "3494866", "incorrect user_id %s" % usu.user_id)
        self.assertEqual(usu.name, "NievesLopez", "incorrect uid %s" % usu.name) # check test case
        conn.disconnect()

    @patch('zk.base.socket')
    @patch('zk.base.ZK_helper')
    def _test_tcp_get_template(self, helper, socket):
        """ can get empty? """
        helper.return_value.test_ping.return_value = True # ping simulated
        helper.return_value.test_tcp.return_value = 0 # helper tcp ok
        socket.return_value.recv.side_effect = [
            codecs.decode('5050827d08000000d0075fb2cf450100', 'hex'), # tcp CMD_ACK_OK
            codecs.decode('5050827d15000000d007acf93064160000941d0000941d0000b400be00', 'hex'), # ack ok with size 7572
            codecs.decode('5050827d10000000dc05477830641700941d000000000100', 'hex'), #prepare data
            codecs.decode('5050827d08000000d00745b2cf451b00', 'hex'), # tcp random CMD_ACK_OK TODO: generate proper sequenced response
            #codecs.decode('5050827d08000000d00745b2cf451b00', 'hex')  # tcp random CMD_ACK_OK TODO: generate proper sequenced response
        ]
        #begin
        zk = ZK('192.168.1.201', verbose=True)
        conn = zk.connect()
        socket.return_value.send.assert_called_with(codecs.decode('5050827d08000000e80317fc00000000', 'hex'))
        templates = conn.get_templates()
        self.assertEqual(len(templates), 6, "incorrect size %s" % len(templates))
        #assert one user
        usu = users[3]
        self.assertIsInstance(usu.uid, int, "uid should be int() %s" % type(usu.uid))
        if sys.version_info >= (3, 0):
            self.assertIsInstance(usu.user_id, (str, bytes), "user_id should be str() or bytes() %s" % type(usu.user_id))
        else:
            self.assertIsInstance(usu.user_id, (str, unicode), "user_id should be str() or unicode() %s" % type(usu.user_id))
        self.assertEqual(usu.uid, 4, "incorrect uid %s" % usu.uid)
        self.assertEqual(usu.user_id, "831", "incorrect user_id %s" % usu.user_id)
        self.assertEqual(usu.name, "NN-831", "incorrect uid %s" % usu.name) # generated
        conn.disconnect()

if __name__ == '__main__':
    unittest.main()
