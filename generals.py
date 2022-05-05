import os
import socket

from messenger import Messenger

class General:
	def __init__(self, ip, port, name, state, status='seccondary', verbose=False):
		self.ip = ip
		self.port = int(port)
		self.name = name
		self.state = state
		self.status = status
		self.reciever = self.init_reciever()
		self.verbose = verbose
		self.order = None

	def __str__(self):
		return f"G{self.name}, {self.status}, majority=?, state={self.state}"

	def get_state(self):
		return f"G{self.name}, {self.status}, state={self.state}"

	def set_state(self, state):
		if state.upper() == "FAULTY":
			self.state = "F"
		else:
			self.state = "NF"

	def init_reciever(self, backlog=5):
		""" To construct and prepare a server socket listening on the given port."""
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		s.bind(('', self.port))
		s.listen(backlog)
		s.settimeout(2)
		return s
	
	def listen(self):
		""" Lisetning the received msg and handling """
		try:
			client_sock = self.reciever.accept()[0]
			client_sock.settimeout(None)

			host, port = client_sock.getpeername()
			listener_connection = Messenger(host, port, client_sock, self.verbose)
			try:
				msgtype, msgdata = listener_connection.receive()
			except KeyboardInterrupt:
				self.close()
				return (False, False, False)
			listener_connection.close()
			opposite_id = "%s:%d" % (host, port)
			if self.verbose:
				print(f"Recieved message. MSGTYPE: {msgtype}, DATA: {msgdata}")
			return (opposite_id, msgtype, msgdata)
		except:
			return False
	def send(self, dest_id, msgtype, msgdata):
		# destination peer id = ip:port
		ip = dest_id.split(":")[0]
		port = dest_id.split(":")[1]
		# try to send
		try :
			messenger = Messenger(ip, port, None, self.verbose)
			messenger.transmit(msgtype, msgdata)
		except KeyboardInterrupt:
			self.close()
			return False
		return True

	def broadcast(self, dest_id_list, msgtype, msgdata):
		myid = "%s:%d" % (self.ip, self.port)
		if self.verbose:
			print(f"{myid} => Broadcasting message: {msgtype} {msgdata}")
		for dest_id in dest_id_list:
			if dest_id != myid:
				self.send(dest_id, msgtype, msgdata)
		return True

	def get_receiver_address(self):
		return ip, port

	def close(self):
		self.reciever.close()
		return True