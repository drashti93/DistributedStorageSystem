from concurrent import futures
import grpc
import logging
import sys
import threading
import os
sys.path.append("../" + os.path.dirname(os.path.realpath(__file__)))
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + '/utils/')
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + '/generated/')

import globals
import connection

from node_position import NodePosition
import greet_pb2_grpc
import network_manager_pb2_grpc
import traversal_pb2
import traversal_pb2_grpc
import time
import storage_pb2_grpc
import rumour_pb2_grpc
import rumour_pb2

from client import Client
from server import Greeter
from network_manager import NetworkManager
from node_traversal import Traversal
from pulse import Pulse
from hb_server import RumourServicer
from hb_server import RecoveryServicer

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=50))
    greet_pb2_grpc.add_GreeterServicer_to_server(Greeter(), server)
    network_manager_pb2_grpc.add_NetworkManagerServicer_to_server(NetworkManager(), server)
    traversal_pb2_grpc.add_TraversalServicer_to_server(Traversal(), server)
    server.add_insecure_port("[::]:" + str(globals.port))
    logger.info("Server starting at port " + str(globals.port))
    storage_pb2_grpc.add_FileServerServicer_to_server(globals.storage_object, server)
    server.add_insecure_port("[::]:" + str(globals.port))
    logger.info("Server starting at port " + str(globals.port))
    server.start()
    server.wait_for_termination()


def fault_tol():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    rumour_pb2_grpc.add_RumourServicer_to_server(RumourServicer(), server)

    # recovery server
    recovery_pb2_grpc.add_RecoveryServicer_to_server(RecoveryServicer(), server)

    server.add_insecure_port('[::]:8888')
    server.start()
    print("Server starting...")

# XXX
def send_request():
    time.sleep(10)
    server_node_ip = "10.0.0.3"
    logger.info("Connecting to {} at port {}...".format(server_node_ip, globals.port))
    traversal_stub = traversal_pb2_grpc.TraversalStub(globals.node_connections.connection_dict[NodePosition.RIGHT].channel)
    logger.debug(traversal_stub)
    response = traversal_stub.ReceiveData(
        traversal_pb2.ReceiveDataRequest(
                                        hash_id="hashid",
                                        request_id="1",
                                        stack=str([]),
                                        visited=str([])))
    logger.info("forward_receive_data_request: response: {}".format(response))


if __name__ == "__main__":
    globals.init()
    logging.basicConfig(filename='node.log', filemode='w',
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    if len(sys.argv) == 3:
        logger.info("Starting first node of the network at position: ({},{})"
                    .format(sys.argv[1], sys.argv[2]))
        my_node_coordinates = (int(sys.argv[1]), int(sys.argv[2]))
        my_pos = my_node_coordinates
        conn = connection.Connection(channel=None, node_position=NodePosition.CENTER,
                                     node_coordinates=my_node_coordinates, node_ip=globals.my_ip)
        globals.node_connections.add_connection(conn)
        logger.debug("NodeConnections.connection_dict: {}".format(globals.node_connections.connection_dict))

        logger.debug("Starting server thread...")
        server_thread = threading.Thread(target=serve)
        server_thread.start()
        # traversal_thread = threading.Thread(target=send_request)
        # traversal_thread.start()
        pulse_thread = threading.Thread(target=Pulse.check_neighbor_node_pulse)
        pulse_thread.start()


        server_thread.join()
    else:
        if len(sys.argv) != 2:
            print("usage: python3 node/node.py [ipv4 address]")
            exit(1)

        client_thread = threading.Thread(target=Client.greet, args=(sys.argv[1],))
        server_thread = threading.Thread(target=serve)
        fault_tol_thread = threading.Thread(target=fault_tol)
        # for testing storage client only
        #storage_thread = threading.Thread(target=Client.test_upload_data, args=(sys.argv[1],))
        # XXX
        #traversal_thread = threading.Thread(target=ReceiveRequest, args=(request))

        logger.debug("Starting client thread with target greet...")
        client_thread.start()
        logger.debug("Starting server thread with target serve...")

        # logger.debug("Starting storage thread with target greet...")
        # storage_thread.start()

        server_thread.start()
        fault_tol_thread.start()

        pulse_thread = threading.Thread(target=Pulse.check_neighbor_node_pulse)
        pulse_thread.start()

        server_thread.join()
