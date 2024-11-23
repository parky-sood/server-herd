import os
from dotenv import load_dotenv

import asyncio
import argparse
import aiohttp
import re 
import time


SERVERS = {'Bailey': 21208, 
           'Bona': 21209, 
           'Campbell': 21210, 
           'Clark': 21211, 
           'Jaquez': 21212}

CONNECTIONS = {'Clark': ['Jaquez', 'Bona'],
               'Campbell': ['Bailey', 'Bona', 'Jaquez'],
               'Bona': ['Bailey', 'Clark', 'Campbell'],
               'Jaquez': ['Clark', 'Campbell'],             # add 'Bona' maybe?
               'Bailey': ['Campbell', 'Bona']}

HOST_ADDR = '127.0.0.1'

class Server:
    def __init__(self, server_id):
        self.name = server_id
        self.port = SERVERS[server_id];
        self.connections = CONNECTIONS[server_id]
        self.locations = {}
        

    async def handle_IAMAT(self, client, location, client_time):
        print('Handling IAMAT')
        
        server_time = time.time();
        time_diff = server_time - client_time

        response = str('AT ' + self.name + ' +' + str(time_diff) + ' ' + str(client) + ' ' + str(location) + ' ' + str(client_time))

        self.locations[client] = response
        
        for server in self.connections:
            try:
                _, writer = await asyncio.open_connection(HOST_ADDR, SERVERS[server])
                writer.write(response.encode())
                await writer.drain()
                writer.close()
                await writer.wait_closed()
            except:
                pass
        
        print('IAMAT response: ' + response)
        return str(response  + '\n')
    
    async def handle_WHATSAT(self, client, radius, num_places):
        print('Handling WHATSAT')

        print(self.locations.get(client))
        if self.locations.get(client) is None:
            print('Client not found')
            return str('? ' + 'WHATSAT ' + client + ' ' + str(radius) + ' ' + str(num_places))
        
        latest_info = self.locations[client]
        print(latest_info)
        latest_location = latest_info.split()[4]
        temp = re.split('(\+|-)', latest_location)
        latitude = temp[1] + temp[2]
        longitude = temp[3] + temp[4]
        location = latitude + '%2C' + longitude
        
        radius *= 1000
        if radius < 0:
            print('Invalid radius')
            return str('? ' + 'WHATSAT ' + client + ' ' + str(radius) + ' ' + str(num_places))

        request = URL + 'location=' + location + '&radius=' + str(radius) + '&key=' + API_KEY
        async with aiohttp.ClientSession() as session:
            async with session.get(request) as response:
                api_resp = await response.json()
                if len(api_resp['results']) > num_places:
                    api_resp['results'] = api_resp['results'][:num_places]
                return str(latest_info + '\n' + json.dumps(api_resp, indent=4) + '\n\n') 

    async def handle_AT(self, response):
        print('Handling AT')
        if response is not None:
            components = response.split()
            if not components[3] in self.locations or self.locations.get(components[3])[4] != response[4]:
                self.locations[components[3]] = response
                for server in self.connections:
                    try:
                        _, writer = await asyncio.open_connection(HOST_ADDR, SERVERS[server])
                        writer.write(response.encode())
                        await writer.drain()
                        writer.close()
                        await writer.wait_closed() 
                    except:
                        pass            
            else:
                print("Duplicate message")
                return response
        else:
            return None


    async def start_server(self, reader, writer):
        print('Connected to client')
        try:
            data = await reader.read(100)
            if data is not None:
                message = data.decode()
                components = message.split()
                type = components[0]
                if type == 'IAMAT' and len(components) == 4:
                    result = await self.handle_IAMAT(components[1], components[2], float(components[3]))
                    if result is not None:
                        writer.write(result.encode())
                elif type == 'WHATSAT' and len(components) == 4:
                    result = await self.handle_WHATSAT(components[1], int(components[2]), int(components[3]))
                    if result is not None:
                        writer.write(result.encode())
                elif type == 'AT' and len(components) == 6:
                    result = await self.handle_AT(message)
                    if result is not None:
                        writer.write(result.encode())
                else:
                    writer.write(('?' + message).encode())
        except:
            print('Disconnected from client')
            pass

        await writer.drain()
        writer.close()
        await writer.wait_closed()
    
async def main():
    parser = argparse.ArgumentParser(description='Server for server herd application')
    parser.add_argument('server', type=str, help='Connect to this server')
    args = parser.parse_args()
    server = args.server
    if server in SERVERS:
        try:
            herd = Server(server)
            print('Starting server')
            asyncio_server = await asyncio.start_server(herd.start_server, HOST_ADDR, SERVERS[server])
            async with asyncio_server:
                await asyncio_server.serve_forever()
        except KeyboardInterrupt:
            print('Shutting down server')
            pass
    else:
        print('Invalid server')

if __name__ == '__main__':
    asyncio.run(main())
