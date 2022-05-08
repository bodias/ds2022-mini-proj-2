import sys
import time
import rpyc
import threading
from rpyc.utils.server import ThreadedServer
from generals import General
from collections import Counter

generals, port_prefix = [], 4000

if len(sys.argv) > 1 and sys.argv[-1] == "--verbose":
	verbose = True
else:
	verbose = False

class Coordinator(rpyc.Service):
	"""Coordinator Service to facilitate interaction between driver code and the generals (Process nodes)"""
	def on_connect(self, conn):
		self.next_id = 0
		if verbose:
			print("SERVER: connected to Driver. Awaiting Generals to be initialized")

	def on_disconnect(self, conn):
		exit_program()

	def add_generals(self, generals_count):
		for general_id in range(generals_count):
			# General(IP, PORT_ID, NAME, STATE, STATUS(Primary/Secondary))
			self.next_id += 1
			if not generals:
				general = General("localhost", int(port_prefix + self.next_id), self.next_id, "NF", "primary", verbose)
			else:
				general = General("localhost", int(port_prefix + self.next_id), self.next_id, "NF", "secondary", verbose)
			if verbose:
				print(f"SERVER: General G{self.next_id} initialized: {general}")
			generals.append(general)
		return None

	def exposed_initialize_generals(self, generals_count):
		return self.add_generals(generals_count)

	def list_general_states(self):
		"""
			Iterate through all connections and fetch general states
		"""
		# 'generals' is a global variable
		for general in generals:
			print(general.get_state())

	def execute_order(self, quorum, decisions):
		"""
		Execute order based on collective decision		
		"""
		# K members can fail assuming arbitrary failures.
		# we need at least 3K + 1 members to reach consensus
		total_nodes = len(generals)
		faulty_nodes = [general for general in generals if general.state == "F"]
		score = Counter([order[1] for order in decisions])		
		# TODO: when K=0, what should I do? is there a minimum number of members still? Or just 3 is enough (to have majority)
		min_score = (total_nodes // 2) + 1
		required_nodes = 3 * (len(faulty_nodes)) + 1
		collective_decision = score.most_common(1)[0][0]
		print(f"scores: {score}, collective_decision: {collective_decision}")
		
		if required_nodes > total_nodes or collective_decision == "undefined":
			print(f"Execute order: cannot be determined - not enough generals in the system! {len(faulty_nodes)} faulty node(s) in the system - {min_score} out of {total_nodes} quorum not consistent\n")
			return
		
		if faulty_nodes:
			print(f"Execute order: {collective_decision}! {len(faulty_nodes)} faulty nodes in the system - {min_score} out of {total_nodes} quorum suggest {collective_decision}\n")
		else:
			print(f"Execute order: {collective_decision}! Non-faulty nodes in the system - {min_score} out of {total_nodes} quorum suggest {collective_decision}\n")
		return



	def exposed_remote_command(self, command_args):
		remote_command = command_args[0]
		print("\nReceived command: \t ", remote_command)
		if len(command_args) > 3:
			print("Too many arguments", command_args)

		# handle exit
		elif remote_command == "exit":
			print("Exiting program")
			exit_program()
			sys.exit(0)

		# handle actual-order
		elif remote_command == "actual-order":
			if len(command_args) < 2:
				print("Define attack strategy.. e.g. 'actual-order attack' or 'actual-order retreat'")
				return

			order, quorum = command_args[1].lower(), []
			if order == "attack" or order == "retreat":
				# Build list of generals for consensus.
				primary_general = None
				for general in generals:
					if general.status == "primary":
						primary_general = general
					quorum.append(general.get_address())
				if verbose:
					print("quorum participants: ", quorum)
					print("primary: ", primary_general)
				# Broadcast the Order to generals (from Primary).
				primary_general.send_order(quorum, order)
				# Generals receive Orders and prepare for quorum.
				# Exchange messages and Reach Consensus
				# Report quorum to leader.

				## Print majority from each general and then report final quorum decision. 
				time.sleep(1)
				if verbose:
					print("Majorities observed:", primary_general.decisions)

				for general in generals:
					print(general)
					general.round = None
				self.execute_order(quorum, primary_general.decisions)
				primary_general.decisions = []
				# sleep call just so all communication is carried out and outcome is reported back before allowing next command to be given
			else:
				print("Unrecognized order ", order)

		# handle g-state
		elif remote_command == "g-state":
			if len(command_args) > 1:
				try:
					if command_args[1].isdigit() and (command_args[2].upper() == "NON-FAULTY" or command_args[2].upper() == "FAULTY"):
						input_general, state = int(command_args[1]), command_args[2].upper()
						for general in generals:
							if general.name == input_general:
								general.set_state(state)
					else:
						print("USAGE: g-state <general_id> [FAULTY|NON-FAULTY]")
				except Exception as e:
					print(f"Exception raised: {e}")
			self.list_general_states()
			return None

		# handle g-add
		elif remote_command == "g-add":
			if len(command_args) > 1:
				if command_args[1].isdigit():
					self.add_generals(int(command_args[1]))
				else:
					print("USAGE: g-add <number of new generals>")
			self.list_general_states()
			return None

		# handle g-kill
		elif remote_command == "g-kill":
			if len(command_args) > 1:
				try:
					is_primary = False
					if command_args[1].isdigit():
						input_general, general_to_remove = int(command_args[1]), None
						for general in generals:
							if general.name == input_general:
								general.close()
								general_to_remove = general
						if general_to_remove:
							generals.remove(general_to_remove)
							if general_to_remove.status == "primary":
								generals[0].status = "primary"
								primary_general = generals[0]
						self.list_general_states()
					else:
						print("USAGE: g-state <general_id> [FAULTY|NON-FAULTY]")
				except Exception as e:
					print(f"Exception raised: {e}")
			else:
				print("USAGE: g-kill <general_id>")
			return None
		# handle unsupported command
		else:
			print("Unsupported command:", remote_command)
		return None


def run_process_service(server):
	server.start()

def exit_program():
	for general in generals:
		general.close()
	coordinator.close()


if __name__ == '__main__':
	# To run Server and driver processes separately, comment the following code block and run server in separate terminal
	coordinator = ThreadedServer(Coordinator, port = 18811)
	try:
		# Launching the RPC server in a separate daemon thread (killed on exit)
		coordinator_thread = threading.Thread(target=run_process_service, args=(coordinator,), daemon=True)
		coordinator_thread.start()

		# run_process_service(coordinator)
#		while True:
			# Temporary workaround to give each connection time to communicate and keep connection alive
#			for general in generals:
#				print(general.listen())

		if len(sys.argv) > 1:
			if int(sys.argv[1]) > 0:
				try:
					conn = rpyc.connect("localhost", 18811)
					if conn.root:
						conn.root.initialize_generals(int(sys.argv[1]))
						while True:
							try:
								remote_command = input("Input the Command:\t").lower().split(" ")
								conn.root.remote_command(remote_command)
								if remote_command[0] == "exit":
									sys.exit(0)
							except KeyboardInterrupt:
								print("\nKeyboardInterrupt detected. Disconnecting from server.")
								conn.close()
								break
				except EOFError:
					print("Connection was closed by server.")
				except ConnectionRefusedError:
					print("Connection Refused by server. Is server running?")
				finally:
					print("Program Terminated.")
			else:
				print("No of connections cannot be less than 1.")
				sys.exit(0)
		else:
			print("Usage: 'byzantine_generals_driver.py <number_of_connections>'")
			sys.exit(0)

	except KeyboardInterrupt:
		print("Exiting")
		exit_program()