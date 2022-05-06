import os
import random
import _thread
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
		self.start()

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
				intent, payload = listener_connection.receive()
			except KeyboardInterrupt:
				self.close()
				return (False, False, False)
			listener_connection.close()
			opposite_id = "%s:%d" % (host, port)
			return (opposite_id, intent, payload)
		except:
			return False

	def send(self, dest_id, intent, payload):
		# destination peer id = ip:port
		ip = dest_id.split(":")[0]
		port = dest_id.split(":")[1]
		# try to send
		try :
			messenger = Messenger(ip, port, None, self.verbose)
			messenger.transmit(intent, payload)
		except KeyboardInterrupt:
			self.close()
			return False
		return True

	def broadcast(self, dest_id_list, intent, payload):
		myid = self.get_address()
		if self.verbose:
			print(f"{myid} => Broadcasting message: {intent} {payload}")
		for dest_id in dest_id_list:
			if dest_id != myid:
				self.send(dest_id, intent, payload)
		return True

	def get_address(self):
		return f"{self.ip}:{self.port}"

	def get_vote(self):
		if self.state == "F":
			return random.choice(["attack", "retreat"])
		else:
			return self.order

	def cast_vote(self, quorum):
		myid = self.get_address()
		for dest_id in quorum:
			if dest_id != myid:
				payload = {"sender": self.get_address(), "vote": self.get_vote()}
				self.send(dest_id, "VOTE", payload)

	def pending_majority(self):
		#TODO : YET TO BE IMPLEMENTED 
		return False

	def close(self):
		self.reciever.close()
		return True

	def start(self):
		_thread.start_new_thread(self.run, ())


	def run(self):
		"""
			Run background Task to await for messenger and act accordingly
			
			1. Listen to incoming socket.
			2. Check the message intent and accordingly take suitable action.
				a. Intent: order (passed as ORDR) 
					Accept order from primary and vote in the quorum
				b. Intent: Vote (passed as VOTE)
					Register the vote in data structure and await quorum decision stage.
					After recieving all votes, decide majority and inform the final decision to the primary genral.
		"""
		while True:
			response = self.listen()
			if not isinstance(response, bool):
				_, task, payload = response
				if task == "ORDR":
					if self.verbose:
						print(f"payload => order: {payload['order']} quorum: {payload['quorum']}")
					self.order = payload['order']
					self.primary = payload['primary']
					# Propogate vote
					self.cast_vote(payload['quorum'])
				elif task == "VOTE":
					if self.verbose:
						print(f"payload => order: {payload['vote']} sender: {payload['sender']}")
					if self.pending_majority():
						self.save_vote(payload)

				else:
					print(self.name, task, payload)
