from snmp.ber import ParseError, decode_identifier
from snmp.pdu.v2 import Confirmed, Response, pduTypes
from snmp.security import SecurityLevel
from snmp.security.levels import noAuthNoPriv
from snmp.types import *
from snmp.utils import DummyLock, NumberGenerator, subbytes

class InvalidMessage(ValueError):
    pass

class UnknownSecurityModel(ValueError):
    pass

class MessageFlags(OctetString):
    MIN_SIZE = 1

    AUTH_FLAG       = (1 << 0)
    PRIV_FLAG       = (1 << 1)
    REPORTABLE_FLAG = (1 << 2)
    ALL_FLAGS       = AUTH_FLAG | PRIV_FLAG | REPORTABLE_FLAG

    def __init__(self, byte=0):
        self.byte = byte & self.ALL_FLAGS

    @classmethod
    def parse(cls, data=b''):
        return cls(byte=data[0])

    @property
    def data(self):
        return bytes((self.byte,))

    @property
    def authFlag(self):
        return bool(self.byte & self.AUTH_FLAG)

    @property
    def privFlag(self):
        return bool(self.byte & self.PRIV_FLAG)

    @property
    def reportableFlag(self):
        return bool(self.byte & self.REPORTABLE_FLAG)

    @authFlag.setter
    def authFlag(self, value):
        if value:
            self.byte |= self.AUTH_FLAG
        else:
            self.byte &= ~self.AUTH_FLAG

    @privFlag.setter
    def privFlag(self, value):
        if value:
            self.byte |= self.PRIV_FLAG
        else:
            self.byte &= ~self.PRIV_FLAG

    @reportableFlag.setter
    def reportableFlag(self, value):
        if value:
            self.byte |= self.REPORTABLE_FLAG
        else:
            self.byte &= ~self.REPORTABLE_FLAG

class HeaderData(Sequence):
    def __init__(self, msgID, maxSize, flags, securityModel):
        self.id = msgID
        self.maxSize = maxSize
        self.flags = flags
        self.securityModel = securityModel

    @property
    def objects(self):
        yield Integer(self.id)
        yield Integer(self.maxSize)
        yield self.flags
        yield Integer(self.securityModel)

    @classmethod
    def deserialize(cls, data):
        msgID,      data = Integer      .decode(data, leftovers=True)
        msgMaxSize, data = Integer      .decode(data, leftovers=True)
        msgFlags,   data = MessageFlags .decode(data, leftovers=True)
        msgSecurityModel = Integer      .decode(data)

        if msgID.value < 0:
            raise ParseError("msgID may not be less than 0")
        elif msgMaxSize.value < 484:
            raise ParseError("msgMaxSize may not be less than 484")
        elif msgSecurityModel.value < 1:
            raise ParseError("msgSecurityModel may not be less than 1")

        return cls(
            msgID.value,
            msgMaxSize.value,
            msgFlags,
            msgSecurityModel.value
        )

class ScopedPDU(Sequence):
    def __init__(self, pdu, contextEngineID, contextName=b''):
        self.contextEngineID = contextEngineID
        self.contextName = contextName
        self.pdu = pdu

    @property
    def objects(self):
        yield OctetString(self.contextEngineID)
        yield OctetString(self.contextName)
        yield self.pdu

    @classmethod
    def deserialize(cls, data, types={}):
        contextEngineID, data = OctetString.decode(data, leftovers=True)
        contextName,     data = OctetString.decode(data, leftovers=True)

        identifier = decode_identifier(subbytes(data))

        try:
            pduType = types[identifier]
        except KeyError as err:
            raise ParseError("Invalid PDU type: {}".format(identifier)) from err

        return cls(
            pduType.decode(data),
            contextEngineID=contextEngineID.data,
            contextName=contextName.data,
        )

class CacheEntry:
    def __init__(self, engineID, contextName, handle,
            securityName, securityModel, securityLevel):
        self.context = contextName
        self.engineID = engineID
        self.handle = handle
        self.securityName = securityName
        self.securityModel = securityModel
        self.securityLevel = securityLevel

class MessagePreparer:
    VERSION = 3

    def __init__(self, security, lockType=DummyLock):
        self.generator = NumberGenerator(31, signed=False)
        self.lock = lockType()
        self.security = security

        self.outstanding = {}

    def cache(self, entry):
        for i in range(10):
            with self.lock:
                msgID = next(self.generator)
                if msgID not in self.outstanding:
                    self.outstanding[msgID] = entry
                    return msgID

        raise Exception("Failed to allocate message ID")

    def retrieve(self, msgID):
        with self.lock:
            return self.outstanding[msgID]

    def uncache(self, msgID):
        with self.lock:
            try:
                del self.outstanding[msgID]
            except KeyError:
                pass

    def prepareDataElements(self, msg):
        msgGlobalData, msg = HeaderData.decode(msg, leftovers=True)

        if msgGlobalData.securityModel != self.security.MODEL:
            raise UnknownSecurityModel(msgGlobalData.securityModel)

        try:
            securityLevel = SecurityLevel(
                auth=msgGlobalData.flags.authFlag,
                priv=msgGlobalData.flags.privFlag)
        except ValueError as err:
            raise InvalidMessage("Invalid msgFlags: {}".format(err)) from err

        secureData = self.security.processIncoming(msg, securityLevel)
        secureData.scopedPDU = ScopedPDU.decode(secureData.data, types=pduTypes)

        if isinstance(secureData.scopedPDU.pdu, Response):
            try:
                entry = self.retrieve(msgGlobalData.id)
            except KeyError as err:
                errmsg = "Unknown msgID: {}".format(msgGlobalData.id)
                raise ValueError(errmsg) from err

            if (entry.engineID
            and entry.engineID != secureData.securityEngineID):
                raise ValueError("Security Engine ID does not match request")

            if entry.securityName != secureData.securityName:
                raise ValueError("Security Name does not match request")

            if (entry.securityLevel < secureData.securityLevel
            and not isinstance(secureData.scopedPDU.pdu, Internal)):
                raise ValueError("Security Level does not match request")

            if (entry.engineID
            and entry.engineID != secureData.scopedPDU.contextEngineID):
                raise ValueError("Context Engine ID does not match request")

            if entry.context != secureData.scopedPDU.contextName:
                raise ValueError("Context Name does not match request")
        else:
            raise ValueError("Received a non-response PDU type")

        # TODO: periodically uncache unanswered messages
        self.uncache(msgGlobalData.id)
        return secureData, entry.handle

    def prepareOutgoingMessage(self, pdu, handle, engineID, userName,
                securityLevel=noAuthNoPriv, contextName=b''):
        entry = CacheEntry(
            engineID,
            contextName,
            handle,
            userName,
            self.security.MODEL,
            securityLevel)

        msgID = self.cache(entry)
        flags = MessageFlags()
        flags.authFlag = securityLevel.auth
        flags.privFlag = securityLevel.priv
        flags.reportableFlag = isinstance(pdu, Confirmed)

        msgGlobalData = HeaderData(msgID, 1472, flags, self.security.MODEL)
        header = Integer(self.VERSION).encode() + msgGlobalData.encode()
        scopedPDU = ScopedPDU(pdu, engineID, contextName=contextName)

        return self.security.prepareOutgoing(
            header,
            scopedPDU.encode(),
            engineID,
            userName,
            securityLevel,
        )
