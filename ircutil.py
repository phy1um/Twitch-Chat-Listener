class IRCMsg(object):
    def __init__(self, name, chan, msg):
        self.name = name
        self.channel = chan
        self.message = msg

def splitPrivMsg(m):
    name = m[1: m.index("!")]
    chan = m.split(" ")[2]
    msg = m.split(":")[2]
    return IRCMsg(name, chan, msg)
