import socket
import struct
import pickle

class Messenger:
	def __init__(self, destination_ip, destination_port, sock=None, verbose=False):
		if not sock:
			self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.s.connect((destination_ip, int(destination_port)))
		else:
			self.s = sock
		self.sd = self.s.makefile("brw", 0)
		self.verbose = verbose

	def transmit(self, intent, payload):
		try:
			# packing the msg
			intent = intent.encode()
			payload = dict_to_bin(payload)
			msglen = len(payload)
			msg = struct.pack("!4sL%ds" % msglen, intent, msglen, payload)
			# send the msg
			self.sd.write(msg)
			self.sd.flush()
		except KeyboardInterrupt:
			self.close()
			return False
		except Exception as e:
			print(e)
			return False
		#except:
		#	return False
		return True

	def receive(self):
		try:
			intent = self.sd.read(4)
			if not intent :
				return (None, None)
			lenstr = self.sd.read(4)
			msglen = int(struct.unpack("!L", lenstr)[0])
			msg = b''
			while len(msg) != msglen :
				data = self.sd.read(min(2048, msglen - len(msg)))
				if not len(data) :
					break
				msg += data
			if len(msg) != msglen :
				return (None, None)
		except KeyboardInterrupt :
			self.close()
			return (None, None)
		except Exception as e:
			print(e)
			return (None, None)
		#except:
		#	return (None, None)
		intent = intent.decode().upper()
		payload = bin_to_dict(msg)
		return (intent, payload)

	def close(self):
		self.s.close()
		self.s = None
		self.sd = None

def dict_to_bin(dictionary):
	""" dictionary to binary """
	return pickle.dumps(dictionary)

def bin_to_dict(binary):
	""" binary to dictionary """
	return pickle.loads(binary)