import grpc
import logging
import sys
import os
from yaml import load, Loader
sys.path.append("../" + os.path.dirname(os.path.realpath(__file__)))
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + '/generated/')

import machine_info
import greet_pb2
import greet_pb2_grpc
import network_manager_pb2
import network_manager_pb2_grpc

connection_list = []


def greet(ip, channel):
    global node_ip, node_port
    greeter_stub = greet_pb2_grpc.GreeterStub(channel)
    response = greeter_stub.SayHello(greet_pb2.HelloRequest(name=machine_info.get_ip(),
                                                            cpu_usage=machine_info.get_my_cpu_usage(),
                                                            memory_usage=machine_info.get_my_memory_usage(),
                                                            disk_usage=machine_info.get_my_memory_usage()))
    logger.info("Response from " + ip + ": " + str(response))
    if response.my_pos == "" and response.your_pos == "":
        logger.error("Cannot join " + ip)
        return
    node_meta_dict = {eval(response.my_pos): node_ip, eval(response.your_pos): machine_info.get_ip()}
    file = open("node_meta.txt", "w+")
    file.write(str(node_meta_dict))
    file.close()

    connections_len = len(eval(response.additional_connections))
    if connections_len > 0:
        i = 0
        my_pos = response.your_pos
        my_ip = machine_info.get_ip()
        while i < connections_len:
            node_port = str(config["port"])
            node_ip = eval(response.additional_connections)[i]
            channel = grpc.insecure_channel(node_ip + ":" + str(node_port))
            network_manager_stub = network_manager_pb2_grpc.NetworkManagerStub(channel)
            logger.info("greet: making add. conn. to " + node_ip)
            response = network_manager_stub.UpdateNeighborMetaData(
                network_manager_pb2.UpdateNeighborMetaDataRequest(node_meta_dict=str({eval(my_pos): my_ip})))
            logger.info("greet: response: " + str(response))
            node_meta_dict.update({eval(response.status): node_ip})
            file = open("node_meta.txt", "w+")
            file.write(str(node_meta_dict))
            file.close()
            i += 1


if __name__ == '__main__':
    config = load(open('config.yaml'), Loader=Loader)
    logging.basicConfig(filename='client.log', filemode='w',
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(machine_info.get_ip())
    logger.setLevel(logging.DEBUG)
    if len(sys.argv) != 2:
        print("usage: python3 node/client.py [ipv4 address]")
        exit(1)
    node_ip = sys.argv[1]
    node_port = str(config["port"])
    chn = grpc.insecure_channel(node_ip + ":" + str(node_port))
    greet(node_ip, chn)

