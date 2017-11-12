
import re
import socket
import time
import datetime
import time

class TwitchListen(object):

    """TwitchListener

    A simple bot for connecting to Twitch Chat channels and processing
    messages.
    By phylum, November 12th 2017
    https://github.com/phy1um/Twitch-Chat-Listener
    My site: http://dlsym.so
    My email: contact@dlsym.so
    My twitter: @phy1um
    """

    def __init__(self, nick, pw, host="irc.twitch.tv", port=6667, 
            timeout=240)
        """
        Args:
            nick (string): your Twitch username
            pw (string): your Twitch chat authentication code
            host (string), port (string/int): where to connect this bot
            timeout (int): socket timeout in seconds

        """
        self.host = (host, port)
        self.socketTimeout = timeout
        self.nick = nick
        self.pw = pw
        self.encoding = "utf-8"
        self.listen = []
        self.ircConnect()
        self.relisten = re.compile(r"")
        self.pingCount = 0

    def ircConnect(self):
        """
        Open a new socket connection to the Twitch IRC service
        """
        self.socket = socket.socket()
        self.socket.connect(self.host)
        # tell the server who we are
        self.command("PASS", self.pw)
        self.command("NICK", self.pw)
        # create a filestream that we can read messages from
        self.stream = self.socket.makefile(mode="r", 
                encoding=self.encoding)
        self.socket.settimeout(self.socketTimeout)
        # time of last message we recieved (-1 indicates no messages)
        self.lastPing = -1

    def command(self, cmd, data):
        """perform and IRC command for some given data, eg:
        JOIN #channel\r\n ---> command("JOIN", "#channel")

        Args:
            cmd (string): the IRC command to issue
            data (string): the data to send with this command
        """
        self.socket.send("{} {}\r\n".format(cmd, data).encode("utf-8"))
    
    def joinChannel(self, channel, listen=True):
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
        if listen == True:
            self.listen.append(channel)
            self.makeListenRegex()

    def makeListenRegex(self):
        """create matching rules for the channels we are listening to
        """
        match = r""
        # build the channel names to filter for (not foolproof)
        for x in self.listen:
            match += "PRIVMSG {}|".format(x)
        match = match[:-1]
        self.relisten = re.compile(match)


    def processStream(self, onMatch=lambda x: print(x), loopEnd=lambda x:False):
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
        while not loopEnd(now):
            # try to catch socket timeouts
            try:
                # for each line in stream
                m = self.stream.readline()
                if m != "":
                    # update last message time
                    self.lastPing = now
                    # reply to ping with pong to keep connection alive
                    if m == "PING tmi.twitch.tv\r\n":
                        self.pingCount += 1
                        self.command("PONG", "tmi.twitch.tv\r\n")
                    else:
                        # if we have a match then call our handler
                        match = self.relisten.search(m)
                        if match:
                            onMatch(m)

                # if we haven't been pinged in a while restart, to be safe
                if self.lastPing > 0 and time.time() > self.lastPing + 180:
                    self.socket.close()
                    ircConnect()

                now = time.time()
            # also if our socket times out, that's a restart
            except socket.timeout:
                self.socket.close()
                ircConnect()


if __name__ == "__main__":
    """example case monitoring the chat of twitch.tv/BobRoss for keywords
    """
    import cfg
    import ircutil

    # load settings from a config file (for simplicity)
    tl = TwitchListen(cfg.NICK, cfg.PASS)

    # we will be monitoring #BobRoss for keywords
    tl.joinChannel("#bobross")
    keywords = re.compile("cabin|fence|devil")

    # check if our messages contain a keyword ignoring case
    def testMessage(m):
        m = m.lower()
        match = keywords.search(m)
        if match:
            parts = ircutil.splitPrivMsg(m)
            print("MATCH: {} in {} (by {})".format(parts.message, parts.channel, parts.name))

    # look for 10 seconds (predicate example)
    end = time.time() + 10
    print("Looping until time={}".format(end))
    # call onMatch for messages we are monitoring until loopEnd == True
    tl.processStream(onMatch=testMessage, loopEnd=lambda x: x > end)
