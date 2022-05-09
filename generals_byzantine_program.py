import sys
import time
import rpyc
import threading
from rpyc.utils.server import ThreadedServer
from generals import General
from collections import Counter

generals, port_prefix = [], 5000

if len(sys.argv) > 1 and sys.argv[-1] == "--verbose":
	verbose = True
else:
	verbose = False

class Coordinator(rpyc.Service):
	"""
	Coordinator Service to facilitate interaction between driver code and the generals (Process nodes)
	Each command is sent through Remore calls using RPyC and the coordinator will act accordingly.
	"""
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

	def execute_order(self, decisions):
		"""
		Execute order based on collective decision		
		"""
		# K members can fail assuming arbitrary failures.
		# we need at least 3K + 1 members to reach consensus
		total_nodes = len(generals)
		faulty_nodes = [general for general in generals if general.state == "F"]
		score = Counter([decision["majority"] for decision in decisions])
		# when K=0, 3 nodes is enough to have majority (it assumes all nodes are Non-Faulty)
		# when k>1, use the 3k + 1 rule		
		required_nodes = max(3, 3 * (len(faulty_nodes)) + 1)
		# used top 2 because we can have 1 undefined 1 attack|retreat the most_common() will be inconsistent
		top_2_decisions = score.most_common(2)		
		collective_decision = top_2_decisions[0] 
		# if top 2 decisions have same number of votes, it's a tie		
		if len(top_2_decisions)>1:
			if top_2_decisions[0][1] == top_2_decisions[1][1]:
				collective_decision = ("undefined", top_2_decisions[0][1])
			
		print(f"scores: {score.most_common()}, majority decision: {collective_decision[0]}")
		
		if required_nodes > total_nodes or collective_decision[0] == "undefined":
			print(f"Execute order: cannot be determined - not enough generals in the system (required {required_nodes})! {len(faulty_nodes)} faulty node(s) in the system - {collective_decision[1]} out of {total_nodes} quorum not consistent\n")
			return
		
		if faulty_nodes:
			print(f"Execute order: {collective_decision[0]}! {len(faulty_nodes)} faulty nodes in the system - {collective_decision[1]} out of {total_nodes} quorum suggest {collective_decision[0]}\n")
		else:
			print(f"Execute order: {collective_decision[0]}! Non-faulty nodes in the system - {collective_decision[1]} out of {total_nodes} quorum suggest {collective_decision[0]}\n")
		return

	def exposed_remote_command(self, command_args):
		remote_command = command_args[0]
		print(f"\nReceived command: \t {' '.join(command_args)}"), 
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
				# Build list of secondary generals for consensus.
				primary_general = None
				for general in generals:
					if general.status == "primary":
						primary_general = general
					else:
						quorum.append(general.get_address())
				if verbose:
					print("quorum participants: ", quorum)
					print("primary: ", primary_general)
				# send_order Broadcasts the Order to generals (from Primary).
				# Generals receive Orders and prepare for quorum.
				# Exchange messages and Reach Consensus
				# Report quorum to leader.
				primary_general.send_order(quorum, order)

				## Print majority from each general and then report final quorum decision. 
				# print("Waiting for generals to communicate.", end ="")
				while len(primary_general.decisions) < len(quorum):
					# print(f".{len(primary_general.decisions)},{len(quorum)}", end="")
					time.sleep(0.5)
				# print("")
				if verbose:
					print("Majorities observed:", primary_general.decisions)

				for general in generals:
					print(general)
					general.round = None
				self.execute_order(primary_general.decisions)
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
						update_general = [general for general in generals if general.name == input_general]
						if update_general:
							update_general[0].set_state(state)
						else:
							print(f"General {input_general} does not exist. Please inform a valid general ID.\n")
							return None
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
								print(f"Primary general has been removed, new elected primary is {generals[0].name}.")
						else:
							print(f"General {input_general} not found. Invalid general ID.\n")
							return None
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
	coordinator = ThreadedServer(Coordinator, port = 18811)
	try:
		# Launching the RPC server in a separate daemon thread (killed on exit)
		coordinator_thread = threading.Thread(target=run_process_service, args=(coordinator,), daemon=True)
		coordinator_thread.start()

		if len(sys.argv) > 1:
			if int(sys.argv[1]) > 0:
				if len(sys.argv)>2:
					print(f"changing default port to {sys.argv[2]}")
					port_prefix = int(sys.argv[2])

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