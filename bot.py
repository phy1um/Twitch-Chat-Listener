
"""A simple bot for connecting to Twitch Chat channels and processing
    messages.
    By phylum, November 12th 2017
    https://github.com/phy1um/Twitch-Chat-Listener
    My site: http://dlsym.so
    My email: contact@dlsym.so
    My twitter: @phy1um
"""


import re
import socket
import time

class TwitchListen(object):

    """an active twitch IRC connection, which can listen in to messages in
    specified channels

    """

    def __init__(self, nick, pw, host="irc.twitch.tv", port=6667,
                 timeout=240):
        """
        Args:
            nick (string): your Twitch username
            pw (string): your Twitch chat authentication code
            host (string), port (string/int): where to connect this bot
            timeout (int): socket timeout in seconds

        """
        self._host = (host, port)
        self._sockettimeout = timeout
        self._nick = nick
        self._pw = pw
        self._encoding = "utf-8"
        self._listen = []
        self._lastping = -1
        self._joinq = []
        self._join = []
        self._irc_connect()
        self._relisten = re.compile(r"")
        self._pingcount = 0

    def _irc_connect(self):
        """
        Open a new socket connection to the Twitch IRC service
        """
        self._socket = socket.socket()
        self._socket.connect(self._host)
        # tell the server who we are
        self.command("PASS", self._pw)
        self.command("NICK", self._nick)
        # create a filestream that we can read messages from
        self._stream = self._socket.makefile(mode="r",
                                             encoding=self._encoding)
        self._socket.settimeout(self._sockettimeout)
        # time of last message we recieved (-1 indicates no messages)
        self._lastping = -1
        for c in self._join:
            self.join_channel(c)
        for c in self._joinq:
            self.join_channel(c, False)

    def command(self, cmd, data):
        """perform and IRC command for some given data, eg:
        JOIN #channel\r\n ---> command("JOIN", "#channel")

        Args:
            cmd (string): the IRC command to issue
            data (string): the data to send with this command
        """
        self._socket.send("{} {}\r\n".format(cmd, data).encode("utf-8"))

    def join_channel(self, channel, listen=True):
        """connect to the chat of a given channel

        Args:
            channel (string): the name of the channel, in IRC-form eg #foobar
            listen (boolean): do we listen for messages on this channel? false
             will make your bot sit in other channels but ignore the messages,
             if you want your monitoring obscured
        """
        # treat this as an exception because it's so easy to get wrong
        if channel[0] != "#":
            raise Exception(
                "Channel name {} does not start with #".format(channel))

        self.command("JOIN", channel)
        if listen is True:
            self._listen.append(channel)
            self._make_listen_regex()
            self._join = channel
        else:
            self._joinq = channel

    def _make_listen_regex(self):
        """create matching rules for the channels we are listening to
        """
        match = r""
        # build the channel names to filter for (not foolproof)
        for chan in self._listen:
            match += "PRIVMSG {}|".format(chan)
        match = match[:-1]
        self._relisten = re.compile(match)


    def process_stream(self, on_match, loop_end=None):
        """process messages in channels until some condition

        Args:
            onMatch (function): one argument, the full message we matched.
             called for each message in a channel we are watching
            loopEnd (function): one argument, the current time.time(). called
             each iteration of the while loop, the loop exits when this is True
        """
        # lock self?
        now = time.time()
        # process until some predicate (default forever)
        if loop_end == None:
            loop_end = lambda x: False
        while not loop_end(now):
            # try to catch socket timeouts
            try:
                # for each line in stream
                m = self._stream.readline()
                if m != "":
                    # update last message time
                    self._lastping = now
                    # reply to ping with pong to keep connection alive
                    if m == "PING tmi.twitch.tv\r\n":
                        self._pingcount += 1
                        self.command("PONG", "tmi.twitch.tv\r\n")
                    else:
                        # if we have a match then call our handler
                        match = self._relisten.search(m)
                        if match:
                            on_match(m)

                # if we haven't been pinged in a while restart, to be safe
                if self._lastping > 0 and time.time() > self._lastping + 180:
                    self._socket.close()
                    self._irc_connect()

                now = time.time()
            # also if our socket times out, that's a restart
            except socket.timeout:
                self._socket.close()
                self._irc_connect()


if __name__ == "__main__":
    #example case monitoring the chat of twitch.tv/BobRoss for keywords

    import cfg
    import ircutil

    # load settings from a config file (for simplicity)
    tl = TwitchListen(cfg.NICK, cfg.PASS)

    # we will be monitoring #BobRoss for keywords
    tl.join_channel("#bobross")
    keyword_pattern = re.compile("cabin|fence|devil|.*")

    # check if our messages contain a keyword ignoring case
    def test_message(m):
        m = m.lower()
        match = keyword_pattern.search(m)
        if match:
            parts = ircutil.splitPrivMsg(m)
            print("MATCH: {} in {} (by {})".format(parts.message, parts.channel, parts.name))

    # look for 10 seconds (predicate example)
    time_end = time.time() + 600
    print("Looping until time={}".format(time_end))
    # call onMatch for messages we are monitoring until loopEnd == True
    tl.process_stream(on_match=test_message, loop_end=lambda x: x > time_end)
