import sys
import os
import grpc

sys.path.append("../" + os.path.dirname(os.path.realpath(__file__)))
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + '/utils/')
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + '/generated/')

import replication_pb2
import replication_pb2_grpc

class ReplicationService(replication_pb2_grpc.FileserviceServicer):

    def ReplicateFile(self, request, context):
        hash_id = ""
        chunk_size = 0
        number_of_chunks = 0
        is_replica = False

        for key, value in context.invocation_metadata():
            if key == "key-hash-id":
                hash_id = value
            elif key == "key-chunk-size":
                chunk_size = int(value)
            elif key == "key-number-of-chunks":
                number_of_chunks = int(value)
            elif key == "key-is-replica":
                is_replica = str(value)
        metadata = (
            ('key-hash-id', hash_id),
            ('key-chunk-size', str(chunk_size)),
            ('key-number-of-chunks', str(number_of_chunks)),
            ('key-is-replica', str(is_replica))
        )

        print("request =", request.shortest_path[request.currentpos])
        if request.currentpos == len(request.shortest_path) - 1:
            #cache.saveVClock(str(request), str(request))
            #write_to_memory
            return replication_pb2.ack(success=True, message="Data Replicated.")
        else:
            forward_coordinates = request.shortest_path[request.currentpos]
            print("forward coord =", forward_coordinates)
            forward_server_addr = self.getneighbordata(forward_coordinates)
            print("forward IP =", forward_server_addr)
            forward_port = 50051
            forward_channel = grpc.insecure_channel(forward_server_addr + ":" + str(forward_port))
            forward_stub = replication_pb2_grpc.FileserviceStub(forward_channel)
            request.currentpos += 1
            updated_request = replication_pb2.FileData(initialReplicaServer=request.initialReplicaServer,
                                               bytearray=request.bytearray,
                                               vClock=request.vClock, shortest_path=request.shortest_path, currentpos=request.currentpos + 1,
                                               fileMetaData=request.fileMetaData)

            forward_resp = forward_stub.ReplicateFile(updated_request, metadata = metadata)
            print("forward_resp", forward_resp)
            return replication_pb2.ack(success=True, message="Data Forwarded.")