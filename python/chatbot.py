'''
Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance with the License. A copy of the License is located at

    http://aws.amazon.com/apache2.0/

or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
'''

import random
import sys
import irc.bot
import requests

class TwitchBot(irc.bot.SingleServerIRCBot):
    def __init__(self, username, client_id, token, channel):
        self.client_id = client_id
        self.token = token
        self.channel = '#' + channel
        self.is_raffle = False
        self.kwrd = ""
        self.entrylist = set()

        # Create request session and set Twitch headers
        self.web = requests.Session()
        _headers = {'Client-ID': self.client_id, 'Accept': 'application/vnd.twitchtv.v5+json'}
        self.web.headers.update(_headers)
        
        # Get the channel id for v5 API calls
        url = 'https://api.twitch.tv/kraken/users?login=' + channel
        r = self.web.get(url).json()
        self.channel_id = r['users'][0]['_id']

        # Create IRC bot connection
        server = 'irc.chat.twitch.tv'
        port = 6667
        print('Connecting to ' + server + ' on port ' + str(port) + '...')
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port, token)], username, username)
        
    def on_welcome(self, c, e):
        print('Joining ' + self.channel + '...')

        # Request Twitch specific capabilities.
        c.cap('REQ', ':twitch.tv/membership')
        c.cap('REQ', ':twitch.tv/tags')
        c.cap('REQ', ':twitch.tv/commands')
        c.join(self.channel)

        if c.is_connected():
            print('Connected \nListening for commands...')
        else:
            print('Connection failed')

    def on_pubmsg(self, c, e):
        # If a chat message starts with an exclamation point, try to run it as a command
        if e.arguments[0][:1] == '!':
            cmd = e.arguments[0].split(' ')[0][1:]
            print('Received command: ' + cmd)
            self.do_command(e, cmd)

        # If the first word of a chat message matches a keyword, add user to raffle entry list
        elif e.arguments[0] == self.kwrd and self.is_raffle:
            if e.source.user not in self.entrylist:
                print(e.source.user + ' - has been added to entry list.')
                self.entrylist.add(e.source.user)

    def do_command(self, e, cmd):
        c = self.connection
        ch_url = 'https://api.twitch.tv/kraken/channels/' + self.channel_id
        source = e.source.user

        # Poll the API to get the current game.
        if cmd == "game":
            r = self.web.get(ch_url).json()
            if not isinstance(r['game'], str):
                c.privmsg(self.channel, source + ' No current game')
            else:
                c.privmsg(self.channel, source + ' Currently playing ' + r['game'])

        # Poll the API to get the current status of the stream.
        elif cmd == "title":
            r = self.web.get(ch_url).json()
            c.privmsg(self.channel, source + ' Channel title is currently ' + r['status'])

        # Create a link to the specified streamer's channel.
        elif cmd == "shoutout":
            target = e.arguments[0].split()[1]
            c.privmsg(self.channel, 'Please follow and support ' + target + ' at twitch.tv/' + target)

        # Start/End a raffle and set keyword.
        elif cmd == "raffle":
            if source == self.channel[1:]:
                self.is_raffle = not self.is_raffle
                if self.is_raffle and len(e.arguments[0].split()) > 1:                    
                    print('Raffle has begun.')
                    self.kwrd = e.arguments[0].split()[1]

                elif self.is_raffle and len(e.arguments[0].split()) == 1:
                    self.is_raffle = not self.is_raffle
                    print('No keyword given.')

                # End raffle, select winner and clear entry list
                else:
                    print('Raffle has ended.')
                    winner = random.sample(self.entrylist,1)[0]
                    print('Winner: ' + winner)
                    c.privmsg(self.channel, winner + ' is the winner!')
                    self.entrylist.clear()

        # The command was not recognized
        else:
            c.privmsg(self.channel, source + ' Did not understand command: ' + cmd)
            print('Did not understand command: ' + cmd)

def main():
    if len(sys.argv) != 5:
        print("Usage: twitchbot <username> <client id> <token> <channel>")
        sys.exit(1)

    username  = sys.argv[1]
    client_id = sys.argv[2]
    token     = sys.argv[3]
    channel   = sys.argv[4]

    bot = TwitchBot(username, client_id, token, channel)
    bot.start()

if __name__ == "__main__":
    main()
