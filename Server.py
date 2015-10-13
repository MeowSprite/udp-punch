import socket
from PoolHandler import PoolHandle,PoolReadyQueue
import threading
import Queue
import time


class UhpServer():
    '''
    docstring the uhp server class
    '''

    def __init__(self, port):
        self.udp_sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.pools = {}
        self.address_status = {}
        self.send_queue = Queue.Queue()
        self.udp_sock.bind(('', port))
        self.pool_handle_thread = threading.Thread(target=self.pool_handler, name='pool_handle')
        self.receive_handle_thread = threading.Thread(target=self.receive_handle, name='recv')
        self.send_handle_thread = threading.Thread(target=self.send_handle, name='send')
        self.alive = True

    def handle_ack(self, addr):
        print('acknowledging connections')
        try:
            self.address_status[addr] = 1
            self.send_queue.put(tuple(('\x02', addr)))
            self.address_status[addr] = 2
        except:
            raise
        return True
    
    def pool_connect(self, pool, addr):
        try:
            if addr in self.address_status:
                if self.address_status[addr] == 2:
                    print(pool in self.pools)
                    if pool in self.pools:
                        if not self.pools[pool].is_member(addr):
                            print('pool adding')
                            self.pools[pool].add_member(addr)
                            self.send_queue.put(tuple(('\x04' + str(pool), addr)))
                    elif pool not in self.pools:
                        print('pool adding')
                        self.pools[pool] = PoolHandle('p2p', pool, self.udp_sock)
                        self.pools[pool].add_member(addr)
                        self.send_queue.put(tuple(('\x04' + str(pool), addr)))
        except:
            raise
        return True
    
    def pool_handler(self):
        while self.alive:
            try:
                pool = PoolReadyQueue.get()
                pool_t = pool.pool_type
                if pool_t == 'p2p':
                    result = pool.send_addr_p2p()
                    if len(result) == 2:
                        pool.pool_members = []
                        self.send_queue.put(result[0]);
                        self.send_queue.put(result[1]);
            except socket.error:
                raise
            except KeyboardInterrupt:
                raise

    def receive_handle(self):
        while self.alive:
            try:
                data, addr = self.udp_sock.recvfrom(256)
                print("**", data, addr)
                if data == '\x01':
                    if not self.handle_ack(addr):
                        raise socket.error("Send acknowledge error: " + str(addr))
                elif str(data).startswith('\x03'):
                    if not self.pool_connect(data[1:], addr):
                        raise socket.error("Send acknowledge on pool: " + str(addr))
            except socket.error:
                raise
            except KeyboardInterrupt:
                raise

    def send_handle(self):
        while self.alive:
            try:
                    to_send = self.send_queue.get()
                    print "*", to_send
                    self.udp_sock.sendto(to_send[0], to_send[1])
            except socket.error:
                raise
            except KeyboardInterrupt:
                raise

    def main(self):
        self.pool_handle_thread.start()
        self.receive_handle_thread.start()
        self.send_handle_thread.start()
        self.pool_handle_thread.join()
        self.receive_handle_thread.join()
        self.send_handle_thread.join()
        print 'Closing threads'
        print 'Closing sockets'
        self.udp_sock.close()
        print 'Good Bye'